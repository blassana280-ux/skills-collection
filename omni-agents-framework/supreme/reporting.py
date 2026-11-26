"""Reporting Engine SUPREME — rapports dérivés des données réelles uniquement."""
from __future__ import annotations

import json
import sqlite3

from .db import now


class ReportingEngine:
    def __init__(self, conn: sqlite3.Connection, registry, observability):
        self.conn = conn
        self.registry = registry
        self.obs = observability

    def mission_report(self, mission_id: str) -> dict:
        m = self.conn.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone()
        if m is None:
            raise KeyError(mission_id)
        tasks = [dict(r) for r in self.conn.execute("SELECT * FROM tasks WHERE mission_id=?", (mission_id,))]
        return {"mission": dict(m), "tasks": tasks,
                "trace": self.obs.mission_trace(mission_id)}

    def division_report(self, division: str) -> dict:
        members = self.registry.list(division=division, kind="specialist")
        counts = {s: 0 for s in ("registered", "validated", "operational", "monitored")}
        for m in members:
            counts[m["status"]] += 1
        manager = next((a for a in self.registry.list(division=division, kind="manager")), None)
        return {"division": division, "total": len(members), "status_counts": counts,
                "manager": manager["id"] if manager else None,
                "manager_status": manager["status"] if manager else None}

    def global_report(self) -> dict:
        return {"generated_at": now(), "system": self.obs.system_status(),
                "divisions": self.registry.divisions_summary(),
                "providers": self.obs.router.status()}

    def to_markdown(self, report: dict) -> str:
        lines = ["# Rapport OMNIBRAIN SUPREME", f"*Généré : {report['generated_at']}*", ""]
        sys = report["system"]
        lines.append("## Agents")
        for k, v in sys["agents"].items():
            lines.append(f"- {k}: {v}")
        lines.append("\n## KPIs (null = indisponible)")
        for k, v in sys["kpis"].items():
            if not k.startswith("_"):
                lines.append(f"- {k}: {v}")
        lines.append("\n## Divisions")
        for d in report["divisions"]:
            lines.append(f"- {d['division']}: {d['total']} agents, chef {d['manager']} ({d['manager_status']})")
        return "\n".join(lines)
