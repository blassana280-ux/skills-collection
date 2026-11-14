"""Observability Engine SUPREME — logs structurés, métriques, KPIs réels.

Les KPIs non mesurables sont retournés à null avec la mention « indisponible ».
Aucun score fabriqué. Les événements sont corrélés aux missions.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .config import LOG_PATH, ensure_dirs
from .db import now


class ObservabilityEngine:
    def __init__(self, conn: sqlite3.Connection, registry, budget, router):
        self.conn = conn
        self.registry = registry
        self.budget = budget
        self.router = router

    def _rate(self, name: str) -> float | None:
        row = self.conn.execute("SELECT AVG(value) v, COUNT(*) c FROM metrics WHERE name=?", (name,)).fetchone()
        return round(row["v"], 4) if row["c"] else None

    def _avg(self, name: str) -> float | None:
        row = self.conn.execute("SELECT AVG(value) v, COUNT(*) c FROM metrics WHERE name=?", (name,)).fetchone()
        return round(row["v"], 3) if row["c"] else None

    def kpis(self) -> dict:
        """Les 15 indicateurs demandés ; null = indisponible (pas encore mesurable)."""
        statuses = self.registry.status_counts()
        total_agents = sum(statuses.values())
        dup = self._duplicate_rate()
        return {
            "agent_success_rate": self._rate("task_success"),
            "task_completion_rate": self._task_completion_rate(),
            "mission_success_rate": self._rate("mission_success"),
            "average_mission_duration_ms": self._avg("mission_duration_ms"),
            "average_task_latency_ms": self._avg("task_duration_ms"),
            "model_availability": self._model_availability(),
            "model_routing_accuracy": None,  # nécessite des évaluations de routage réelles
            "memory_retrieval_quality": None,  # nécessite un jeu de requêtes annotées
            "duplicate_agent_rate": dup,
            "agent_evaluation_score": self._agent_eval_score(),
            "regression_rate": None,  # nécessite un historique de versions comparées
            "failure_recovery_time_ms": None,  # nécessite des incidents de reprise mesurés
            "cost_per_mission_usd": self._cost_per_mission(),
            "resource_utilization": None,  # nécessite des métriques système réelles
            "human_approval_rate": self._approval_rate(),
            "_note": "null = indisponible, aucune valeur fabriquée",
        }

    def _task_completion_rate(self) -> float | None:
        row = self.conn.execute("SELECT COUNT(*) c, SUM(CASE WHEN state='done' THEN 1 ELSE 0 END) d FROM tasks").fetchone()
        return round(row["d"] / row["c"], 4) if row["c"] else None

    def _duplicate_rate(self) -> float:
        from collections import Counter
        names = [a["profile"]["name"] for a in self.registry.list()]
        if not names:
            return 0.0
        c = Counter(names)
        dups = sum(v - 1 for v in c.values() if v > 1)
        return round(dups / len(names), 6)

    def _model_availability(self) -> dict:
        st = self.router.status()
        return {"available": st["available_count"], "total": len(st["providers"]),
                "providers": {p["name"]: p["status"] for p in st["providers"]}}

    def _agent_eval_score(self) -> float | None:
        row = self.conn.execute("SELECT AVG(passed) v, COUNT(*) c FROM eval_runs WHERE deferred=0").fetchone()
        return round(row["v"], 4) if row["c"] else None

    def _cost_per_mission(self) -> float | None:
        row = self.conn.execute("SELECT AVG(cost) v FROM (SELECT SUM(cost_usd) cost FROM budget_ledger WHERE scope='mission' GROUP BY mission_id)").fetchone()
        return round(row["v"], 6) if row["v"] is not None else None

    def _approval_rate(self) -> float | None:
        row = self.conn.execute("SELECT COUNT(*) c, SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) a FROM approvals").fetchone()
        return round(row["a"] / row["c"], 4) if row["c"] else None

    def system_status(self) -> dict:
        statuses = self.registry.status_counts()
        missions = {r["state"]: r["c"] for r in self.conn.execute("SELECT state, COUNT(*) c FROM missions GROUP BY state")}
        tasks = {r["state"]: r["c"] for r in self.conn.execute("SELECT state, COUNT(*) c FROM tasks GROUP BY state")}
        return {"agents": statuses, "missions": missions, "tasks": tasks,
                "memory": self._memory_stats(), "budget_totals": self.budget.totals(),
                "kpis": self.kpis()}

    def _memory_stats(self) -> dict:
        total = self.conn.execute("SELECT COUNT(*) c FROM memory_items WHERE deleted=0").fetchone()["c"]
        return {"total_items": total}

    def export_jsonl(self, limit: int = 1000) -> str:
        ensure_dirs()
        rows = self.conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        lines = [json.dumps(dict(r), ensure_ascii=False) for r in rows]
        LOG_PATH.write_text("\n".join(lines), encoding="utf-8")
        return str(LOG_PATH)

    def mission_trace(self, mission_id: str) -> dict:
        events = [dict(r) for r in self.conn.execute("SELECT * FROM events WHERE mission_id=? ORDER BY id", (mission_id,))]
        metrics = [dict(r) for r in self.conn.execute("SELECT * FROM metrics WHERE mission_id=? ORDER BY id", (mission_id,))]
        tasks = [dict(r) for r in self.conn.execute("SELECT * FROM tasks WHERE mission_id=? ORDER BY id", (mission_id,))]
        return {"mission_id": mission_id, "events": events, "metrics": metrics, "tasks": tasks}
