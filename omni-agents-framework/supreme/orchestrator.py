"""OmniBrain Core / Agent Orchestrator SUPREME — exécute les missions en DAG.

États explicites, idempotence, reprises, annulation, backpressure, bus, mémoire,
budget, télémétrie. Aucun échec d'agent n'arrête globalement le cerveau.

Concurrence : chaque thread worker utilise sa PROPRE connexion SQLite (WAL) ;
les écritures sont sérialisées par le verrou global de db.transaction. Cela
évite tout usage concurrent d'une même connexion entre threads.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .budget import BudgetController
from .bus import Bus
from .db import get_conn, log_event, now, transaction
from .memory import MemoryEngine
from .planner import MissionPlanner
from .policy import PolicyEngine
from .registry import Registry
from .router import ModelRouter
from .runtime import WorkerPool
from .security import check_tool_permission
from .tools import run_tool

TERMINAL = {"done", "failed", "cancelled", "blocked"}


class OmniBrainCore:
    def __init__(self, conn: sqlite3.Connection | None = None, max_workers: int = 4):
        self.conn = conn or get_conn()
        # Chemin du fichier SQLite pour ouvrir des connexions par thread.
        row = self.conn.execute("PRAGMA database_list").fetchone()
        self.db_path = Path(row[2]) if row and row[2] else None
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
        """Composants + connexion propres au thread courant (thread-safety API/DAG).

        Le thread principal réutilise les composants initiaux ; tout autre thread
        (worker DAG, requête API) obtient sa propre connexion SQLite (WAL). Les
        écritures restent sérialisées par le verrou global de db.transaction.
        """
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

    # ------------------------------------------------------------- missions
    def submit(self, spec: dict) -> dict:
        c = self._c()
        conn = c["conn"]
        plan = c["planner"].plan(spec)
        mid = plan["mission_id"]
        with transaction(conn):
            conn.execute(
                "INSERT INTO missions(id,objective,state,priority,plan_json,created_at,updated_at,budget_usd,privacy) VALUES(?,?,?,?,?,?,?,?,?)",
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
        with transaction(c):
            c.execute("UPDATE tasks SET state=?, result_json=?, error=?, updated_at=? WHERE id=?",
                      (state, json.dumps(result, ensure_ascii=False) if result is not None else None,
                       error, now(), task_id))

    def _execute_task(self, task_id: str) -> dict:
        comp = self._c()
        conn = comp["conn"]
        t = self._task(task_id, conn)
        mid = t["mission_id"]
        if self.pool.is_cancelled(mid):
            self._set_task(task_id, "cancelled", conn=conn)
            return {"task_id": task_id, "state": "cancelled"}
        if t["state"] == "done":
            return {"task_id": task_id, "state": "done", "idempotent": True}
        profile = comp["registry"].profile(t["agent_id"])
        self._set_task(task_id, "assigned", conn=conn)
        comp["bus"].send("omnibrain-core", "omnibrain-core", t["agent_id"], mid, "task_assigned",
                         {"task_id": task_id, "tool": t["tool"]})
        tool = t["tool"]
        if not tool:
            # Tâche LLM : appel RÉEL via le routeur (clé en env, jamais journalisée).
            # Sans fournisseur configuré/disponible -> blocage honnête (aucune simulation).
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
                mission_id=mid, agent_id=t["agent_id"])
            if not res["ok"]:
                self._set_task(task_id, "blocked", error=res["error"], conn=conn)
                comp["bus"].send("omnibrain-core", t["agent_id"], "omnibrain-core", mid, "task_blocked",
                                 {"task_id": task_id, "reason": res["error"]})
                return {"task_id": task_id, "state": "blocked", "reason": res["error"]}
            out = {"text": res["text"], "model": f"{res['provider']}/{res['model']}",
                   "usage": res["usage"], "cost_usd": res["cost_usd"]}
            self._set_task(task_id, "done", result=out, conn=conn)
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
            with transaction(conn):
                conn.execute("UPDATE tasks SET attempts=? WHERE id=?", (attempts, task_id))
            res = self.pool.submit(run_tool, tool, t["input"], timeout=t["timeout_s"], mission_id=mid)
            if res["ok"]:
                self._set_task(task_id, "validating", conn=conn)
                out = res["result"]
                if isinstance(out, dict):
                    self._set_task(task_id, "done", result=out, conn=conn)
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
        with transaction(conn):
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
                               f"Mission {mid} tâche {task_id} ({tool}) : {json.dumps(out, ensure_ascii=False)[:400]}",
                               source=f"orchestrator:{mid}:{task_id}", confidence=0.9,
                               metadata={"mission_id": mid, "agent_id": agent_id, "tool": tool, "subject_key": f"{mid}:{task_id}"})
        except Exception as e:
            log_event(conn, "warning", "orchestrator", f"mémoire non écrite : {e}", mid)

    def _record_failure(self, mid, task_id, agent_id, error, comp) -> None:
        conn = comp["conn"]
        with transaction(conn):
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

    def run(self, mission_id: str) -> dict:
        c = self._c()
        conn = c["conn"]
        with transaction(conn):
            conn.execute("UPDATE missions SET state='running', updated_at=? WHERE id=?", (now(), mission_id))
        start = time.monotonic()
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            while True:
                tasks = [self._task(r["id"], conn) for r in conn.execute(
                    "SELECT id FROM tasks WHERE mission_id=?", (mission_id,))]
                if self.pool.is_cancelled(mission_id):
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
                futures = {ex.submit(self._execute_task, t["id"]): t["id"] for t in ready}
                for fut in as_completed(futures):
                    fut.result()
        tasks = [self._task(r["id"], conn) for r in conn.execute("SELECT id FROM tasks WHERE mission_id=?", (mission_id,))]
        states = [t["state"] for t in tasks]
        if self.pool.is_cancelled(mission_id):
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
        # Arbitrage : les missions complexes passent au conseil multi-modèles.
        # Sans fournisseur -> statut "unavailable" honnête (jamais de décision fabriquée).
        try:
            mrow = conn.execute("SELECT objective, plan_json FROM missions WHERE id=?", (mission_id,)).fetchone()
            plan = json.loads(mrow["plan_json"]) if mrow and mrow["plan_json"] else {}
            if plan.get("classification", {}).get("level") == "complexe":
                from .council import Council
                evidence = [{"task_id": t["id"], "agent_id": t["agent_id"], "tool": t["tool"],
                             "output": json.loads(t["result_json"]) if t["result_json"] else None}
                            for t in tasks if t["state"] == "done"]
                council_res = Council(c["router"]).deliberate(mrow["objective"] if mrow else mission_id,
                                                              evidence=evidence)
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
        except Exception as e:
            log_event(conn, "warning", "council", f"arbitrage non produit : {e}", mission_id)
        with transaction(conn):
            conn.execute("UPDATE missions SET state=?, result_json=?, updated_at=? WHERE id=?",
                         (state, json.dumps(result, ensure_ascii=False), now(), mission_id))
            conn.execute("INSERT INTO metrics(mission_id,name,value,at) VALUES(?,?,?,?)",
                         (mission_id, "mission_duration_ms", duration_ms, now()))
            conn.execute("INSERT INTO metrics(mission_id,name,value,at) VALUES(?,?,?,?)",
                         (mission_id, "mission_success", 1 if state == "completed" else 0, now()))
        log_event(conn, "info", "orchestrator", f"mission {mission_id} -> {state}", mission_id, result)
        return result

    def cancel(self, mission_id: str) -> dict:
        conn = self._c()["conn"]
        self.pool.cancel_mission(mission_id)
        with transaction(conn):
            conn.execute("UPDATE tasks SET state='cancelled', updated_at=? WHERE mission_id=? AND state NOT IN ('done','failed','blocked','cancelled')",
                         (now(), mission_id))
            conn.execute("UPDATE missions SET state='cancelled', updated_at=? WHERE id=?", (now(), mission_id))
        return {"mission_id": mission_id, "state": "cancelled"}

    def recover(self) -> dict:
        conn = self._c()["conn"]
        with transaction(conn):
            cur = conn.execute("UPDATE tasks SET state='pending', updated_at=? WHERE state IN ('assigned','running','validating')", (now(),))
            n = cur.rowcount
            conn.execute("UPDATE missions SET state='planned', updated_at=? WHERE state='running'", (now(),))
        log_event(conn, "info", "orchestrator", f"reprise : {n} tâches abandonnées remises en attente")
        return {"recovered_tasks": n}

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
        rows = self._c()["conn"].execute("SELECT id,objective,state,priority,created_at,updated_at FROM missions ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
