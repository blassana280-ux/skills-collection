"""OmniBrain Core / Agent Orchestrator SUPREME — exécute les missions en DAG.

États explicites, idempotence, reprises, annulation, backpressure, bus, mémoire,
budget, télémétrie. Aucun échec d'agent n'arrête globalement le cerveau.

Concurrence : chaque thread worker utilise sa PROPRE connexion SQLite (WAL).
Les missions revendiquées par des processus séparés sont protégées par bail
propriétaire + heartbeat + jeton de fencing ; les écritures d'un ancien
propriétaire sont refusées et les résultats sont dédupliqués par tâche.
"""
from __future__ import annotations

import contextvars
import json
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextvars import copy_context
from pathlib import Path

from .budget import BudgetController
from .bus import Bus
from .db import get_conn, log_event, now, transaction
from .leases import (LeaseLostError, MissionLease, assert_mission, claim_mission,
                     new_worker_id, recover_abandoned, register_worker, release_mission,
                     renew_mission)
from .memory import MemoryEngine
from .planner import MissionPlanner
from .policy import PolicyEngine
from .registry import Registry
from .router import ModelRouter
from .runtime import WorkerPool
from .security import check_tool_permission
from .tools import run_tool

TERMINAL = {"done", "failed", "cancelled", "blocked"}
MISSION_TERMINAL = {"completed", "partial", "failed", "cancelled"}
_lease_ctx: contextvars.ContextVar[MissionLease | None] = contextvars.ContextVar("supreme_mission_lease", default=None)


class OmniBrainCore:
    def __init__(self, conn: sqlite3.Connection | None = None, max_workers: int = 4,
                 worker_id: str | None = None, lease_seconds: float = 30.0):
        self.conn = conn or get_conn()
        row = self.conn.execute("PRAGMA database_list").fetchone()
        self.db_path = Path(row[2]) if row and row[2] else None
        self.worker_id = worker_id or new_worker_id("core")
        self.lease_seconds = lease_seconds
        self.registry = Registry(self.conn)
        self.bus = Bus(self.conn, self.registry)
        self.memory = MemoryEngine(self.conn, self.registry)
        self.budget = BudgetController(self.conn)
        self.policy = PolicyEngine(self.conn)
        self.router = ModelRouter(self.conn, budget=self.budget)
        self.planner = MissionPlanner(self.registry, self.router)
        self.pool = WorkerPool()
        self.max_workers = max_workers
        self._local = threading.local()
        self._main_ident = threading.get_ident()
        self._main_comp = {"conn": self.conn, "registry": self.registry, "bus": self.bus,
                           "memory": self.memory, "budget": self.budget, "policy": self.policy,
                           "router": self.router, "planner": self.planner}

    def _c(self):
        if threading.get_ident() == self._main_ident:
            return self._main_comp
        comp = getattr(self._local, "comp", None)
        if comp is None:
            conn = get_conn(self.db_path) if self.db_path else self.conn
            registry = Registry(conn)
            budget = BudgetController(conn)
            comp = {"conn": conn, "registry": registry, "bus": Bus(conn, registry),
                    "memory": MemoryEngine(conn, registry), "budget": budget,
                    "policy": PolicyEngine(conn), "router": ModelRouter(conn, budget=budget),
                    "planner": MissionPlanner(registry)}
            self._local.comp = comp
        return comp

    def _guard(self, conn: sqlite3.Connection) -> None:
        lease = _lease_ctx.get()
        if lease is not None:
            assert_mission(conn, lease)

    # ------------------------------------------------------------- missions
    def submit(self, spec: dict) -> dict:
        c = self._c()
        conn = c["conn"]
        plan = c["planner"].plan(spec)
        mid = plan["mission_id"]
        with transaction(conn, immediate=True):
            conn.execute(
                """INSERT INTO missions(id,objective,state,priority,plan_json,created_at,updated_at,budget_usd,privacy)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (mid, plan["objective"], "planned", plan["priority"], json.dumps(plan, ensure_ascii=False),
                 now(), now(), plan["budget_usd"], plan["privacy"]))
            for t in plan["tasks"]:
                idem = f"{mid}:{t['id']}"
                conn.execute(
                    """INSERT INTO tasks(id,mission_id,agent_id,tool,input_json,state,depends_on,timeout_s,
                       idempotency_key,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (t["id"], mid, t["agent_id"], t["tool"], json.dumps(t["input"], ensure_ascii=False),
                     "pending", json.dumps(t["depends_on"]), 120, idem, now(), now()))
        c["budget"].set_quota("mission", mid, plan["budget_usd"])
        log_event(conn, "info", "orchestrator", f"mission soumise : {mid}", mid,
                  {"tasks": len(plan["tasks"]), "classification": plan["classification"]["level"]})
        return {"mission_id": mid, "plan": plan}

    def _task(self, task_id: str, conn: sqlite3.Connection | None = None) -> dict:
        c = conn or self.conn
        row = c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        d = dict(row)
        d["input"] = json.loads(d["input_json"])
        d["depends_on"] = json.loads(d["depends_on"])
        return d

    def _set_task(self, task_id: str, state: str, result: dict | None = None,
                  error: str | None = None, conn: sqlite3.Connection | None = None) -> None:
        c = conn or self.conn
        lease = _lease_ctx.get()
        with transaction(c, immediate=True):
            self._guard(c)
            if lease is not None:
                cur = c.execute("UPDATE tasks SET state=?, result_json=?, error=?, updated_at=? "
                                "WHERE id=? AND execution_token=?",
                                (state, json.dumps(result, ensure_ascii=False) if result is not None else None,
                                 error, now(), task_id, lease.token))
                if cur.rowcount != 1:
                    raise LeaseLostError(f"tâche {task_id} non détenue par le bail courant")
            else:
                c.execute("UPDATE tasks SET state=?, result_json=?, error=?, updated_at=? WHERE id=?",
                          (state, json.dumps(result, ensure_ascii=False) if result is not None else None,
                           error, now(), task_id))

    def _is_cancelled(self, mission_id: str, conn: sqlite3.Connection) -> bool:
        if self.pool.is_cancelled(mission_id):
            return True
        row = conn.execute("SELECT cancel_requested, state FROM missions WHERE id=?", (mission_id,)).fetchone()
        return bool(row and (row["cancel_requested"] or row["state"] == "cancelled"))

    def _execute_task(self, task_id: str) -> dict:
        comp = self._c()
        conn = comp["conn"]
        lease = _lease_ctx.get()
        t = self._task(task_id, conn)
        mid = t["mission_id"]
        if self._is_cancelled(mid, conn):
            self._set_task(task_id, "cancelled", conn=conn)
            return {"task_id": task_id, "state": "cancelled"}
        if t["state"] == "done":
            return {"task_id": task_id, "state": "done", "idempotent": True}
        if lease is not None:
            with transaction(conn, immediate=True):
                assert_mission(conn, lease)
                cur = conn.execute(
                    "UPDATE tasks SET state='assigned', execution_token=?, owner_worker_id=?, updated_at=? "
                    "WHERE id=? AND state IN ('pending','assigned')",
                    (lease.token, lease.worker_id, now(), task_id))
                if cur.rowcount != 1:
                    return {"task_id": task_id, "state": "skipped"}
        profile = comp["registry"].profile(t["agent_id"])
        comp["bus"].send("omnibrain-core", "omnibrain-core", t["agent_id"], mid, "task_assigned",
                         {"task_id": task_id, "tool": t["tool"]})
        tool = t["tool"]
        if not tool:
            self._set_task(task_id, "running", conn=conn)
            limits = profile["execution_limits"]
            mrow = conn.execute("SELECT objective, privacy FROM missions WHERE id=?", (mid,)).fetchone()
            objective = mrow["objective"] if mrow else ""
            privacy = (mrow["privacy"] if mrow else "standard") or "standard"
            system = profile.get("system_instructions", "")
            user_content = json.dumps({
                "objectif_mission": objective,
                "specialite_agent": profile.get("specialization", ""),
                "tache": t["input"],
                "consigne": "Produis une réponse structurée et vérifiable. Signale toute incertitude.",
            }, ensure_ascii=False)
            messages = [{"role": "system", "content": system}, {"role": "user", "content": user_content}]
            res = comp["router"].complete(
                {"capabilities": ["general"], "max_cost_usd": limits.get("max_cost", 0.05), "privacy": privacy},
                messages, max_tokens=min(limits.get("max_tokens", 2048), 2048),
                mission_id=mid, agent_id=t["agent_id"], task_id=task_id,
                call_key=t["idempotency_key"], extra_scopes=[("division", profile["division"])])
            self._guard(conn)
            if not res["ok"]:
                self._set_task(task_id, "blocked", error=res["error"], conn=conn)
                comp["bus"].send("omnibrain-core", t["agent_id"], "omnibrain-core", mid, "task_blocked",
                                 {"task_id": task_id, "reason": res["error"]})
                return {"task_id": task_id, "state": "blocked", "reason": res["error"]}
            out = {"text": res["text"], "model": f"{res['provider']}/{res['model']}",
                   "usage": res["usage"], "cost_usd": res["cost_usd"]}
            self._record_success(mid, task_id, t["agent_id"], f"llm:{res['model']}", out, res["latency_ms"], comp)
            return {"task_id": task_id, "state": "done", "model": out["model"], "cost_usd": res["cost_usd"]}
        if not check_tool_permission(profile, tool):
            self._set_task(task_id, "blocked", error=f"outil {tool} non autorisé pour {t['agent_id']}", conn=conn)
            return {"task_id": task_id, "state": "blocked"}
        self._set_task(task_id, "running", conn=conn)
        attempts = 0
        max_retries = profile["execution_limits"]["max_retries"]
        last_error = ""
        while attempts <= max_retries:
            attempts += 1
            self._guard(conn)
            with transaction(conn, immediate=True):
                self._guard(conn)
                conn.execute("UPDATE tasks SET attempts=? WHERE id=? AND execution_token=?",
                             (attempts, task_id, lease.token if lease else None))
            res = self.pool.submit(run_tool, tool, t["input"], timeout=t["timeout_s"], mission_id=mid)
            self._guard(conn)
            if res["ok"]:
                self._set_task(task_id, "validating", conn=conn)
                out = res["result"]
                if isinstance(out, dict):
                    self._record_success(mid, task_id, t["agent_id"], tool, out, res["duration_ms"], comp)
                    return {"task_id": task_id, "state": "done", "duration_ms": res["duration_ms"]}
                last_error = "sortie non structurée"
            else:
                last_error = res["error"]
            time.sleep(min(0.05 * attempts, 0.2))
        self._set_task(task_id, "failed", error=last_error, conn=conn)
        self._record_failure(mid, task_id, t["agent_id"], last_error, comp)
        return {"task_id": task_id, "state": "failed", "error": last_error}

    def _record_success(self, mid, task_id, agent_id, tool, out, duration_ms, comp) -> None:
        conn = comp["conn"]
        lease = _lease_ctx.get()
        result_json = json.dumps(out, ensure_ascii=False)
        with transaction(conn, immediate=True):
            self._guard(conn)
            cur = conn.execute(
                """INSERT OR IGNORE INTO task_executions(task_id,mission_id,idempotency_key,fencing_token,
                     worker_id,result_json,completed_at) VALUES(?,?,?,?,?,?,?)""",
                (task_id, mid, f"{mid}:{task_id}", lease.fencing_token if lease else 0,
                 lease.worker_id if lease else "inline", result_json, now()))
            if cur.rowcount != 1:
                return  # résultat déjà commité : idempotence stricte
            if lease is not None:
                cur = conn.execute("UPDATE tasks SET state='done', result_json=?, error=NULL, updated_at=? "
                                   "WHERE id=? AND execution_token=?", (result_json, now(), task_id, lease.token))
                if cur.rowcount != 1:
                    raise LeaseLostError(f"tâche {task_id} non détenue")
            else:
                conn.execute("UPDATE tasks SET state='done', result_json=?, error=NULL, updated_at=? WHERE id=?",
                             (result_json, now(), task_id))
            conn.execute("INSERT INTO metrics(mission_id,task_id,agent_id,name,value,at) VALUES(?,?,?,?,?,?)",
                         (mid, task_id, agent_id, "task_duration_ms", duration_ms, now()))
            conn.execute("INSERT INTO metrics(mission_id,task_id,agent_id,name,value,at) VALUES(?,?,?,?,?,?)",
                         (mid, task_id, agent_id, "task_success", 1, now()))
            comp["budget"].record("mission", mid, 0.0, mission_id=mid, provider="local-tool", model=tool,
                                  extra_scopes=[("agent", agent_id)])
            comp["bus"].send("omnibrain-core", "omnibrain-core", agent_id, mid, "task_done",
                             {"task_id": task_id, "tool": tool}, confidence=0.9)
            try:
                comp["memory"].add("omnibrain-core", "collective", "collective", "episodic",
                                   f"Mission {mid} tâche {task_id} ({tool}) : {result_json[:400]}",
                                   source=f"orchestrator:{mid}:{task_id}", confidence=0.9,
                                   metadata={"mission_id": mid, "agent_id": agent_id, "tool": tool,
                                             "subject_key": f"{mid}:{task_id}"})
            except Exception as e:
                log_event(conn, "warning", "orchestrator", f"mémoire non écrite : {e}", mid)

    def _record_failure(self, mid, task_id, agent_id, error, comp) -> None:
        conn = comp["conn"]
        with transaction(conn, immediate=True):
            self._guard(conn)
            conn.execute("INSERT INTO metrics(mission_id,task_id,agent_id,name,value,at) VALUES(?,?,?,?,?,?)",
                         (mid, task_id, agent_id, "task_success", 0, now()))
            comp["bus"].send("omnibrain-core", "omnibrain-core", agent_id, mid, "task_failed",
                             {"task_id": task_id, "error": error})
            try:
                comp["memory"].add("omnibrain-core", "collective", "collective", "error",
                                   f"Échec mission {mid} tâche {task_id} : {error}",
                                   source=f"orchestrator:{mid}:{task_id}", confidence=0.8,
                                   metadata={"mission_id": mid, "agent_id": agent_id})
            except Exception:
                pass

    def _active_lease(self, conn: sqlite3.Connection, mission_id: str) -> MissionLease | None:
        row = conn.execute(
            """SELECT owner_worker_id, lease_token, fencing_token, lease_expires_at FROM missions
               WHERE id=? AND state='running' AND owner_worker_id=? AND lease_expires_at > ?""",
            (mission_id, self.worker_id, time.time())).fetchone()
        if row is None:
            return None
        return MissionLease(mission_id, row["owner_worker_id"], row["lease_token"],
                            row["fencing_token"], row["lease_expires_at"])

    def run(self, mission_id: str, lease: MissionLease | None = None,
            stop_event: threading.Event | None = None) -> dict:
        c = self._c()
        conn = c["conn"]
        existing = conn.execute("SELECT state, result_json FROM missions WHERE id=?", (mission_id,)).fetchone()
        if existing is None:
            raise KeyError(f"mission inconnue : {mission_id}")
        if existing["state"] in MISSION_TERMINAL:
            if existing["result_json"]:
                return json.loads(existing["result_json"]) | {"idempotent": True}
            if existing["state"] == "cancelled":
                return {"mission_id": mission_id, "state": "cancelled", "tasks": {}, "cost_usd": 0.0}
        if lease is None:
            lease = self._active_lease(conn, mission_id) or claim_mission(
                conn, mission_id, self.worker_id, self.lease_seconds)
        if lease is None:
            raise LeaseLostError(f"mission {mission_id} déjà détenue par un autre worker ou non planifiée")
        register_worker(conn, lease.worker_id)
        ctx_token = _lease_ctx.set(lease)
        lost = threading.Event()
        hb_stop = threading.Event()
        hb_interval = max(0.05, min(self.lease_seconds / 3.0, 5.0))

        def heartbeat():
            hb_conn = get_conn(self.db_path) if self.db_path else self.conn
            while not hb_stop.wait(hb_interval):
                try:
                    if not renew_mission(hb_conn, lease, self.lease_seconds):
                        lost.set()
                        return
                except Exception:
                    lost.set()
                    return

        hb = threading.Thread(target=heartbeat, name=f"lease-{mission_id}", daemon=True)
        hb.start()
        start = time.monotonic()
        interrupted = False
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                while True:
                    if (stop_event is not None and stop_event.is_set()) or lost.is_set():
                        interrupted = True
                        break
                    self._guard(conn)
                    tasks = [self._task(r["id"], conn) for r in conn.execute(
                        "SELECT id FROM tasks WHERE mission_id=?", (mission_id,))]
                    if self._is_cancelled(mission_id, conn):
                        for t in tasks:
                            if t["state"] not in TERMINAL:
                                self._set_task(t["id"], "cancelled", conn=conn)
                        break
                    done_ids = {t["id"] for t in tasks if t["state"] == "done"}
                    terminal_ids = {t["id"] for t in tasks if t["state"] in TERMINAL}
                    ready = [t for t in tasks if t["state"] == "pending"
                             and all(d in done_ids for d in t["depends_on"])]
                    for t in tasks:
                        if t["state"] == "pending" and any(d in terminal_ids and d not in done_ids for d in t["depends_on"]):
                            self._set_task(t["id"], "blocked", error="dépendance non satisfaite", conn=conn)
                    if not ready:
                        if all(t["state"] in TERMINAL for t in tasks):
                            break
                        if not any(t["state"] in ("assigned", "running", "validating") for t in tasks):
                            break
                        time.sleep(0.01)
                        continue
                    futures = {}
                    for t in ready:
                        ctx = copy_context()
                        futures[ex.submit(ctx.run, self._execute_task, t["id"])] = t["id"]
                    for fut in as_completed(futures):
                        try:
                            fut.result()
                        except LeaseLostError:
                            lost.set()
                            interrupted = True
            if interrupted or lost.is_set() or (stop_event is not None and stop_event.is_set()):
                release_mission(conn, lease, requeue=True)
                return {"mission_id": mission_id, "state": "interrupted", "reason": "arrêt propre ou bail perdu"}
            tasks = [self._task(r["id"], conn) for r in conn.execute("SELECT id FROM tasks WHERE mission_id=?", (mission_id,))]
            states = [t["state"] for t in tasks]
            if self._is_cancelled(mission_id, conn):
                state = "cancelled"
            elif all(s == "done" for s in states):
                state = "completed"
            elif any(s == "done" for s in states):
                state = "partial"
            elif all(s in ("failed", "blocked") for s in states):
                state = "failed"
            else:
                state = "partial"
            duration_ms = (time.monotonic() - start) * 1000
            result = {"mission_id": mission_id, "state": state, "duration_ms": duration_ms,
                      "tasks": {s: states.count(s) for s in set(states)},
                      "cost_usd": c["budget"].mission_cost(mission_id)}
            try:
                self._guard(conn)
                mrow = conn.execute("SELECT objective, plan_json FROM missions WHERE id=?", (mission_id,)).fetchone()
                plan = json.loads(mrow["plan_json"]) if mrow and mrow["plan_json"] else {}
                if plan.get("classification", {}).get("level") == "complexe":
                    from .council import Council
                    evidence = [{"task_id": t["id"], "agent_id": t["agent_id"], "tool": t["tool"],
                                 "output": json.loads(t["result_json"]) if t["result_json"] else None}
                                for t in tasks if t["state"] == "done"]
                    council_res = Council(c["router"]).deliberate(
                        mrow["objective"] if mrow else mission_id, evidence=evidence,
                        mission_id=mission_id, budget_usd=plan.get("budget_usd"))
                    self._guard(conn)
                    result["council"] = council_res
                    log_event(conn, "info", "council", f"arbitrage mission {mission_id} : {council_res['status']}",
                              mission_id, {"status": council_res["status"]})
                    if council_res.get("decision"):
                        try:
                            c["memory"].add("omnibrain-core", "central", "omnibrain-core", "decision",
                                            f"Conseil mission {mission_id} : {json.dumps(council_res['decision'], ensure_ascii=False)[:400]}",
                                            source=f"council:{mission_id}", confidence=0.8,
                                            metadata={"mission_id": mission_id, "subject_key": f"council:{mission_id}"})
                        except Exception:
                            pass
            except LeaseLostError:
                raise
            except Exception as e:
                log_event(conn, "warning", "council", f"arbitrage non produit : {e}", mission_id)
            with transaction(conn, immediate=True):
                assert_mission(conn, lease)
                cur = conn.execute(
                    """UPDATE missions SET state=?, result_json=?, lease_expires_at=0, heartbeat_at=?, updated_at=?
                       WHERE id=? AND owner_worker_id=? AND lease_token=? AND fencing_token=? AND state='running'""",
                    (state, json.dumps(result, ensure_ascii=False), time.time(), now(),
                     mission_id, lease.worker_id, lease.token, lease.fencing_token))
                if cur.rowcount != 1:
                    raise LeaseLostError(f"mission {mission_id} non détenue à la complétion")
                conn.execute("INSERT INTO metrics(mission_id,name,value,at) VALUES(?,?,?,?)",
                             (mission_id, "mission_duration_ms", duration_ms, now()))
                conn.execute("INSERT INTO metrics(mission_id,name,value,at) VALUES(?,?,?,?)",
                             (mission_id, "mission_success", 1 if state == "completed" else 0, now()))
            log_event(conn, "info", "orchestrator", f"mission {mission_id} -> {state}", mission_id, result)
            return result
        except LeaseLostError:
            release_mission(conn, lease, requeue=True)
            raise
        except Exception:
            release_mission(conn, lease, requeue=True)
            raise
        finally:
            hb_stop.set()
            hb.join(timeout=2.0)
            _lease_ctx.reset(ctx_token)

    def cancel(self, mission_id: str) -> dict:
        conn = self._c()["conn"]
        self.pool.cancel_mission(mission_id)
        with transaction(conn, immediate=True):
            conn.execute("UPDATE tasks SET state='cancelled', updated_at=? WHERE mission_id=? AND state NOT IN ('done','failed','blocked','cancelled')",
                         (now(), mission_id))
            conn.execute("UPDATE missions SET state='cancelled', cancel_requested=1, lease_expires_at=0, updated_at=? WHERE id=?",
                         (now(), mission_id))
        return {"mission_id": mission_id, "state": "cancelled"}

    def recover(self) -> dict:
        """Reprise sûre : jamais de réinitialisation des missions encore sous bail vivant."""
        return recover_abandoned(self._c()["conn"])

    def status(self, mission_id: str) -> dict:
        conn = self._c()["conn"]
        m = conn.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone()
        if m is None:
            raise KeyError(f"mission inconnue : {mission_id}")
        d = dict(m)
        d["plan"] = json.loads(d.pop("plan_json"))
        d["result"] = json.loads(d["result_json"]) if d["result_json"] else None
        d["tasks"] = [self._task(r["id"], conn) for r in conn.execute("SELECT id FROM tasks WHERE mission_id=? ORDER BY id", (mission_id,))]
        return d

    def list_missions(self, limit: int = 50) -> list[dict]:
        rows = self._c()["conn"].execute(
            "SELECT id,objective,state,priority,created_at,updated_at,owner_worker_id,lease_expires_at,fencing_token,run_attempts FROM missions ORDER BY created_at DESC LIMIT ?",
            (limit,)).fetchall()
        return [dict(r) for r in rows]
