"""OmniBrain Core / Agent Orchestrator SUPREME — exécute les missions en DAG.

États explicites, idempotence, reprises, annulation, backpressure, bus, mémoire,
budget, télémétrie. Aucun échec d'agent n'arrête globalement le cerveau.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

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
from .tools import TOOLS, run_tool

TERMINAL = {"done", "failed", "cancelled", "blocked"}


class OmniBrainCore:
    def __init__(self, conn: sqlite3.Connection | None = None, max_workers: int = 4):
        self.conn = conn or get_conn()
        self.registry = Registry(self.conn)
        self.bus = Bus(self.conn, self.registry)
        self.memory = MemoryEngine(self.conn, self.registry)
        self.budget = BudgetController(self.conn)
        self.policy = PolicyEngine(self.conn)
        self.router = ModelRouter(self.conn, budget=self.budget)
        self.planner = MissionPlanner(self.registry, self.router)
        self.pool = WorkerPool()
        self.max_workers = max_workers

    # ------------------------------------------------------------- missions
    def submit(self, spec: dict) -> dict:
        plan = self.planner.plan(spec)
        mid = plan["mission_id"]
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO missions(id,objective,state,priority,plan_json,created_at,updated_at,budget_usd,privacy) VALUES(?,?,?,?,?,?,?,?,?)",
                (mid, plan["objective"], "planned", plan["priority"], json.dumps(plan, ensure_ascii=False),
                 now(), now(), plan["budget_usd"], plan["privacy"]))
            for t in plan["tasks"]:
                idem = f"{mid}:{t['id']}"
                self.conn.execute(
                    """INSERT INTO tasks(id,mission_id,agent_id,tool,input_json,state,depends_on,timeout_s,
                       idempotency_key,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (t["id"], mid, t["agent_id"], t["tool"], json.dumps(t["input"], ensure_ascii=False),
                     "pending", json.dumps(t["depends_on"]), 120, idem, now(), now()))
        self.budget.set_quota("mission", mid, plan["budget_usd"])
        log_event(self.conn, "info", "orchestrator", f"mission soumise : {mid}", mid,
                  {"tasks": len(plan["tasks"]), "classification": plan["classification"]["level"]})
        return {"mission_id": mid, "plan": plan}

    def _task(self, task_id: str) -> dict:
        row = self.conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        d = dict(row)
        d["input"] = json.loads(d["input_json"])
        d["depends_on"] = json.loads(d["depends_on"])
        return d

    def _set_task(self, task_id: str, state: str, result: dict | None = None, error: str | None = None) -> None:
        with transaction(self.conn):
            self.conn.execute("UPDATE tasks SET state=?, result_json=?, error=?, updated_at=? WHERE id=?",
                              (state, json.dumps(result, ensure_ascii=False) if result is not None else None,
                               error, now(), task_id))

    def _execute_task(self, task_id: str) -> dict:
        t = self._task(task_id)
        mid = t["mission_id"]
        if self.pool.is_cancelled(mid):
            self._set_task(task_id, "cancelled")
            return {"task_id": task_id, "state": "cancelled"}
        # Idempotence : déjà terminé -> ne pas rejouer.
        if t["state"] == "done":
            return {"task_id": task_id, "state": "done", "idempotent": True}
        profile = self.registry.profile(t["agent_id"])
        self._set_task(task_id, "assigned")
        self.bus.send("omnibrain-core", "omnibrain-core", t["agent_id"], mid, "task_assigned",
                      {"task_id": task_id, "tool": t["tool"]})
        tool = t["tool"]
        if not tool:
            # Mission nécessitant un LLM : vérifier disponibilité réelle.
            route = self.router.route({"capabilities": ["general"], "max_cost_usd": 0.05})
            if not route["available"]:
                self._set_task(task_id, "blocked", error=route["reason"])
                self.bus.send("omnibrain-core", t["agent_id"], "omnibrain-core", mid, "task_blocked",
                              {"task_id": task_id, "reason": route["reason"]})
                return {"task_id": task_id, "state": "blocked", "reason": route["reason"]}
            # Un fournisseur disponible ne suffit pas à exécuter sans appel réel : marqué bloqué honnêtement.
            self._set_task(task_id, "blocked", error="appel LLM réel non implémenté dans cette version ; fournisseur disponible mais exécution à câbler")
            return {"task_id": task_id, "state": "blocked"}
        if not check_tool_permission(profile, tool):
            self._set_task(task_id, "blocked", error=f"outil {tool} non autorisé pour {t['agent_id']}")
            return {"task_id": task_id, "state": "blocked"}
        self._set_task(task_id, "running")
        attempts = 0
        max_retries = profile["execution_limits"]["max_retries"]
        last_error = ""
        while attempts <= max_retries:
            attempts += 1
            with transaction(self.conn):
                self.conn.execute("UPDATE tasks SET attempts=? WHERE id=?", (attempts, task_id))
            res = self.pool.submit(run_tool, tool, t["input"], timeout=t["timeout_s"], mission_id=mid)
            if res["ok"]:
                self._set_task(task_id, "validating")
                out = res["result"]
                # Validation : sortie structurée attendue.
                if isinstance(out, dict):
                    self._set_task(task_id, "done", result=out)
                    self._record_success(mid, task_id, t["agent_id"], tool, out, res["duration_ms"])
                    return {"task_id": task_id, "state": "done", "duration_ms": res["duration_ms"]}
                last_error = "sortie non structurée"
            else:
                last_error = res["error"]
            time.sleep(min(0.05 * attempts, 0.2))  # backoff borné
        self._set_task(task_id, "failed", error=last_error)
        self._record_failure(mid, task_id, t["agent_id"], last_error)
        return {"task_id": task_id, "state": "failed", "error": last_error}

    def _record_success(self, mid: str, task_id: str, agent_id: str, tool: str, out: dict, duration_ms: float) -> None:
        with transaction(self.conn):
            self.conn.execute("INSERT INTO metrics(mission_id,task_id,agent_id,name,value,at) VALUES(?,?,?,?,?,?)",
                              (mid, task_id, agent_id, "task_duration_ms", duration_ms, now()))
            self.conn.execute("INSERT INTO metrics(mission_id,task_id,agent_id,name,value,at) VALUES(?,?,?,?,?,?)",
                              (mid, task_id, agent_id, "task_success", 1, now()))
        self.budget.record("mission", mid, 0.0, mission_id=mid, provider="local-tool", model=tool,
                           extra_scopes=[("agent", agent_id)])
        self.bus.send("omnibrain-core", "omnibrain-core", agent_id, mid, "task_done",
                      {"task_id": task_id, "tool": tool}, confidence=0.9)
        # Mémoire collective : résultat validé avec provenance.
        try:
            self.memory.add("omnibrain-core", "collective", "collective", "episodic",
                            f"Mission {mid} tâche {task_id} ({tool}) : {json.dumps(out, ensure_ascii=False)[:400]}",
                            source=f"orchestrator:{mid}:{task_id}", confidence=0.9,
                            metadata={"mission_id": mid, "agent_id": agent_id, "tool": tool, "subject_key": f"{mid}:{task_id}"})
        except Exception as e:
            log_event(self.conn, "warning", "orchestrator", f"mémoire non écrite : {e}", mid)

    def _record_failure(self, mid: str, task_id: str, agent_id: str, error: str) -> None:
        with transaction(self.conn):
            self.conn.execute("INSERT INTO metrics(mission_id,task_id,agent_id,name,value,at) VALUES(?,?,?,?,?,?)",
                              (mid, task_id, agent_id, "task_success", 0, now()))
        self.bus.send("omnibrain-core", "omnibrain-core", agent_id, mid, "task_failed",
                      {"task_id": task_id, "error": error})
        try:
            self.memory.add("omnibrain-core", "collective", "collective", "error",
                            f"Échec mission {mid} tâche {task_id} : {error}",
                            source=f"orchestrator:{mid}:{task_id}", confidence=0.8,
                            metadata={"mission_id": mid, "agent_id": agent_id})
        except Exception:
            pass

    def run(self, mission_id: str) -> dict:
        with transaction(self.conn):
            self.conn.execute("UPDATE missions SET state='running', updated_at=? WHERE id=?", (now(), mission_id))
        start = time.monotonic()
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            while True:
                tasks = [self._task(r["id"]) for r in self.conn.execute(
                    "SELECT id FROM tasks WHERE mission_id=?", (mission_id,))]
                if self.pool.is_cancelled(mission_id):
                    for t in tasks:
                        if t["state"] not in TERMINAL:
                            self._set_task(t["id"], "cancelled")
                    break
                done_ids = {t["id"] for t in tasks if t["state"] == "done"}
                terminal_ids = {t["id"] for t in tasks if t["state"] in TERMINAL}
                ready = [t for t in tasks if t["state"] == "pending"
                         and all(d in done_ids for d in t["depends_on"])]
                # Tâches dont une dépendance a échoué/est bloquée -> bloquées.
                for t in tasks:
                    if t["state"] == "pending" and any(d in terminal_ids and d not in done_ids for d in t["depends_on"]):
                        self._set_task(t["id"], "blocked", error="dépendance non satisfaite")
                if not ready:
                    if all(t["state"] in TERMINAL for t in tasks):
                        break
                    # aucune tâche prête mais des non-terminées -> attendre (ne devrait pas arriver en DAG valide)
                    if not any(t["state"] in ("assigned", "running", "validating") for t in tasks):
                        break
                    time.sleep(0.01)
                    continue
                futures = {ex.submit(self._execute_task, t["id"]): t["id"] for t in ready}
                for fut in as_completed(futures):
                    fut.result()
        # État final de la mission
        tasks = [self._task(r["id"]) for r in self.conn.execute("SELECT id FROM tasks WHERE mission_id=?", (mission_id,))]
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
                  "cost_usd": self.budget.mission_cost(mission_id)}
        with transaction(self.conn):
            self.conn.execute("UPDATE missions SET state=?, result_json=?, updated_at=? WHERE id=?",
                              (state, json.dumps(result, ensure_ascii=False), now(), mission_id))
            self.conn.execute("INSERT INTO metrics(mission_id,name,value,at) VALUES(?,?,?,?)",
                              (mission_id, "mission_duration_ms", duration_ms, now()))
            self.conn.execute("INSERT INTO metrics(mission_id,name,value,at) VALUES(?,?,?,?)",
                              (mission_id, "mission_success", 1 if state == "completed" else 0, now()))
        log_event(self.conn, "info", "orchestrator", f"mission {mission_id} -> {state}", mission_id, result)
        return result

    def cancel(self, mission_id: str) -> dict:
        self.pool.cancel_mission(mission_id)
        with transaction(self.conn):
            self.conn.execute("UPDATE tasks SET state='cancelled', updated_at=? WHERE mission_id=? AND state NOT IN ('done','failed','blocked','cancelled')",
                              (now(), mission_id))
            self.conn.execute("UPDATE missions SET state='cancelled', updated_at=? WHERE id=?", (now(), mission_id))
        return {"mission_id": mission_id, "state": "cancelled"}

    def recover(self) -> dict:
        """Reprise après panne : les tâches running/assigned/validating sont remises en attente."""
        with transaction(self.conn):
            cur = self.conn.execute("UPDATE tasks SET state='pending', updated_at=? WHERE state IN ('assigned','running','validating')", (now(),))
            n = cur.rowcount
            self.conn.execute("UPDATE missions SET state='planned', updated_at=? WHERE state='running'", (now(),))
        log_event(self.conn, "info", "orchestrator", f"reprise : {n} tâches abandonnées remises en attente")
        return {"recovered_tasks": n}

    def status(self, mission_id: str) -> dict:
        m = self.conn.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone()
        if m is None:
            raise KeyError(f"mission inconnue : {mission_id}")
        d = dict(m)
        d["plan"] = json.loads(d.pop("plan_json"))
        d["result"] = json.loads(d["result_json"]) if d["result_json"] else None
        d["tasks"] = [self._task(r["id"]) for r in self.conn.execute("SELECT id FROM tasks WHERE mission_id=? ORDER BY id", (mission_id,))]
        return d

    def list_missions(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute("SELECT id,objective,state,priority,created_at,updated_at FROM missions ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
