"""Cost Controller SUPREME — quotas par fournisseur/agent/division/mission,
alertes, coupure automatique, estimation et historique des dépenses.

Démarrage gratuit : les outils déterministes locaux coûtent 0 USD. Les coûts
LLM ne sont enregistrés que sur appels réels à des fournisseurs configurés.
"""
from __future__ import annotations

import sqlite3

from .db import log_event, now, transaction

ALERT_THRESHOLD = 0.9  # alerte à 90% du quota


class BudgetController:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def set_quota(self, scope: str, scope_id: str, limit_usd: float, period: str = "total") -> None:
        if scope not in ("provider", "agent", "division", "mission", "global"):
            raise ValueError("scope invalide")
        if limit_usd < 0:
            raise ValueError("quota négatif interdit")
        with transaction(self.conn):
            self.conn.execute(
                "INSERT OR REPLACE INTO quotas(scope,scope_id,limit_usd,period) VALUES(?,?,?,?)",
                (scope, scope_id, limit_usd, period))

    def spent(self, scope: str, scope_id: str) -> float:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(cost_usd),0) s FROM budget_ledger WHERE scope=? AND scope_id=?",
            (scope, scope_id)).fetchone()
        return float(row["s"])

    def remaining(self, scope: str, scope_id: str) -> float | None:
        q = self.conn.execute("SELECT limit_usd FROM quotas WHERE scope=? AND scope_id=?", (scope, scope_id)).fetchone()
        if q is None:
            return None
        return q["limit_usd"] - self.spent(scope, scope_id)

    def check(self, entries: list[tuple[str, str]], amount: float) -> dict:
        """Vérifie qu'une dépense respecte tous les quotas pertinents."""
        for scope, scope_id in entries:
            rem = self.remaining(scope, scope_id)
            if rem is not None and amount > rem + 1e-9:
                return {"allowed": False, "reason": f"quota dépassé : {scope}/{scope_id}", "remaining": rem}
        return {"allowed": True, "reason": "dans les quotas"}

    def record(self, scope: str, scope_id: str, cost_usd: float, mission_id: str | None = None,
               provider: str | None = None, model: str | None = None,
               tokens_in: int = 0, tokens_out: int = 0, extra_scopes: list | None = None) -> dict:
        """Enregistre une dépense réelle (0 pour les outils locaux)."""
        entries = [(scope, scope_id)] + list(extra_scopes or [])
        verdict = self.check(entries, cost_usd)
        if not verdict["allowed"]:
            log_event(self.conn, "warning", "budget", f"dépense refusée : {verdict['reason']}", mission_id)
            return {"recorded": False, **verdict}
        with transaction(self.conn):
            for sc, sid in entries:
                self.conn.execute(
                    """INSERT INTO budget_ledger(scope,scope_id,mission_id,provider,model,tokens_in,tokens_out,cost_usd,at)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (sc, sid, mission_id, provider, model, tokens_in, tokens_out, cost_usd, now()))
        # Alertes
        alerts = []
        for sc, sid in entries:
            q = self.conn.execute("SELECT limit_usd FROM quotas WHERE scope=? AND scope_id=?", (sc, sid)).fetchone()
            if q and q["limit_usd"] > 0 and self.spent(sc, sid) >= ALERT_THRESHOLD * q["limit_usd"]:
                alerts.append(f"quota {sc}/{sid} >= 90%")
        if alerts:
            log_event(self.conn, "warning", "budget", "; ".join(alerts), mission_id)
        return {"recorded": True, "cost_usd": cost_usd, "alerts": alerts}

    def mission_cost(self, mission_id: str) -> float:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(cost_usd),0) s FROM budget_ledger WHERE mission_id=? AND scope='mission'",
            (mission_id,)).fetchone()
        return float(row["s"])

    def totals(self) -> dict:
        rows = self.conn.execute("SELECT scope, scope_id, SUM(cost_usd) s FROM budget_ledger GROUP BY scope, scope_id").fetchall()
        return {f"{r['scope']}/{r['scope_id']}": round(r["s"], 6) for r in rows}

    def ledger(self, limit: int = 100) -> list[dict]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM budget_ledger ORDER BY id DESC LIMIT ?", (limit,))]
