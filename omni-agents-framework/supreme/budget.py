"""Cost Controller SUPREME — quotas, réservations atomiques, comptabilisation.

Chaque appel payant doit réserver une borne supérieure de coût AVANT l'appel,
puis être soldé sur l'usage réel (ou libéré/interrupté). Les quotas centraux
(mission, agent, division, fournisseur, global) sont vérifiés dans la même
transaction SQLite IMMEDIATE que la réservation : deux processus ne peuvent pas
dépenser deux fois le même solde. Les outils locaux restent à 0 USD.
"""
from __future__ import annotations

import math
import sqlite3
import uuid

from .db import log_event, now, transaction

ALERT_THRESHOLD = 0.9
SCOPES = ("provider", "agent", "division", "mission", "global")


def _amount(value: float) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as e:
        raise ValueError("montant invalide") from e
    if not math.isfinite(x) or x < 0:
        raise ValueError("montant négatif ou non fini interdit")
    return x


class BudgetController:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def set_quota(self, scope: str, scope_id: str, limit_usd: float, period: str = "total") -> None:
        if scope not in SCOPES:
            raise ValueError("scope invalide")
        limit = _amount(limit_usd)
        with transaction(self.conn, immediate=True):
            self.conn.execute(
                "INSERT OR REPLACE INTO quotas(scope,scope_id,limit_usd,period) VALUES(?,?,?,?)",
                (scope, scope_id, limit, period))

    def committed(self, scope: str, scope_id: str) -> float:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(cost_usd),0) s FROM budget_ledger WHERE scope=? AND scope_id=?",
            (scope, scope_id)).fetchone()
        return float(row["s"])

    # Compatibilité historique : `spent` = dépenses soldées. L'exposition inclut les réservations.
    def spent(self, scope: str, scope_id: str) -> float:
        return self.committed(scope, scope_id)

    def reserved(self, scope: str, scope_id: str) -> float:
        row = self.conn.execute(
            """SELECT COALESCE(SUM(s.amount_usd),0) s FROM budget_reservation_scopes s
               JOIN budget_reservations r ON r.id=s.reservation_id
               WHERE s.scope=? AND s.scope_id=? AND r.status IN ('reserved','interrupted')""",
            (scope, scope_id)).fetchone()
        return float(row["s"])

    def exposure(self, scope: str, scope_id: str) -> float:
        return self.committed(scope, scope_id) + self.reserved(scope, scope_id)

    def remaining(self, scope: str, scope_id: str) -> float | None:
        q = self.conn.execute("SELECT limit_usd FROM quotas WHERE scope=? AND scope_id=?", (scope, scope_id)).fetchone()
        if q is None:
            return None
        return float(q["limit_usd"]) - self.exposure(scope, scope_id)

    def check(self, entries: list[tuple[str, str]], amount: float) -> dict:
        amount = _amount(amount)
        for scope, scope_id in dict.fromkeys(entries):
            rem = self.remaining(scope, scope_id)
            if rem is not None and amount > rem + 1e-12:
                return {"allowed": False, "reason": f"quota dépassé : {scope}/{scope_id}", "remaining": rem}
        return {"allowed": True, "reason": "dans les quotas"}

    def reserve(self, entries: list[tuple[str, str]], amount: float, mission_id: str | None = None,
                task_id: str | None = None, provider: str | None = None, model: str | None = None,
                tokens_in_est: int = 0, tokens_out_est: int = 0, call_key: str | None = None) -> dict:
        """Réserve atomiquement une borne supérieure sur tous les scopes pertinents."""
        amount = _amount(amount)
        scopes = list(dict.fromkeys((sc, sid) for sc, sid in entries if sc in SCOPES and sid))
        if not scopes:
            raise ValueError("au moins un scope budgétaire est requis")
        rid = f"res-{uuid.uuid4().hex[:16]}"
        with transaction(self.conn, immediate=True):
            if call_key:
                existing = self.conn.execute("SELECT id, status FROM budget_reservations WHERE call_key=?", (call_key,)).fetchone()
                if existing:
                    return {"reserved": False, "reason": "call_key déjà utilisé", "reservation_id": existing["id"],
                            "status": existing["status"]}
            verdict = self.check(scopes, amount)
            if not verdict["allowed"]:
                log_event(self.conn, "warning", "budget", f"réservation refusée : {verdict['reason']}", mission_id)
                return {"reserved": False, **verdict}
            self.conn.execute(
                """INSERT INTO budget_reservations(id,call_key,mission_id,task_id,provider,model,status,
                     amount_usd,tokens_in_est,tokens_out_est,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,'reserved',?,?,?,?,?)""",
                (rid, call_key, mission_id, task_id, provider, model, amount,
                 int(tokens_in_est), int(tokens_out_est), now(), now()))
            for sc, sid in scopes:
                self.conn.execute(
                    "INSERT INTO budget_reservation_scopes(reservation_id,scope,scope_id,amount_usd) VALUES(?,?,?,?)",
                    (rid, sc, sid, amount))
        return {"reserved": True, "reservation_id": rid, "amount_usd": amount}

    def settle(self, reservation_id: str, actual_cost_usd: float, tokens_in: int = 0, tokens_out: int = 0,
               provider: str | None = None, model: str | None = None) -> dict:
        """Solde une réservation sur l'usage réel ; le coût réel ne dépasse pas la borne réservée."""
        actual = _amount(actual_cost_usd)
        with transaction(self.conn, immediate=True):
            r = self.conn.execute("SELECT * FROM budget_reservations WHERE id=?", (reservation_id,)).fetchone()
            if r is None:
                raise KeyError(f"réservation inconnue : {reservation_id}")
            if r["status"] != "reserved":
                return {"recorded": False, "reason": f"réservation non soluble : {r['status']}", "reservation_id": reservation_id}
            if actual > float(r["amount_usd"]) + 1e-12:
                raise ValueError("coût réel supérieur à la réservation : borne de tokens/prix à corriger")
            scopes = [(x["scope"], x["scope_id"]) for x in self.conn.execute(
                "SELECT scope, scope_id FROM budget_reservation_scopes WHERE reservation_id=?", (reservation_id,))]
            # Remplacer la réservation par le coût réel ne peut pas augmenter l'exposition.
            self.conn.execute(
                """UPDATE budget_reservations SET status='settled', actual_cost_usd=?, tokens_in_actual=?,
                     tokens_out_actual=?, provider=COALESCE(?,provider), model=COALESCE(?,model), updated_at=?
                   WHERE id=?""",
                (actual, int(tokens_in), int(tokens_out), provider, model, now(), reservation_id))
            for sc, sid in scopes:
                self.conn.execute(
                    """INSERT INTO budget_ledger(scope,scope_id,mission_id,provider,model,tokens_in,tokens_out,
                         cost_usd,at,reservation_id,call_key) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (sc, sid, r["mission_id"], provider or r["provider"], model or r["model"],
                     int(tokens_in), int(tokens_out), actual, now(), reservation_id, r["call_key"]))
        alerts = self._alerts(scopes, r["mission_id"])
        return {"recorded": True, "cost_usd": actual, "reservation_id": reservation_id, "alerts": alerts}

    def release(self, reservation_id: str, reason: str = "", interrupted: bool = False) -> dict:
        """Libère une réservation non facturée ; `interrupted` conserve l'exposition par prudence."""
        status = "interrupted" if interrupted else "released"
        with transaction(self.conn, immediate=True):
            cur = self.conn.execute(
                "UPDATE budget_reservations SET status=?, error=?, updated_at=? WHERE id=? AND status='reserved'",
                (status, reason[:500], now(), reservation_id))
            if cur.rowcount != 1:
                return {"released": False, "reservation_id": reservation_id}
        return {"released": True, "status": status, "reservation_id": reservation_id}

    def _alerts(self, scopes: list[tuple[str, str]], mission_id: str | None) -> list[str]:
        alerts = []
        for sc, sid in scopes:
            q = self.conn.execute("SELECT limit_usd FROM quotas WHERE scope=? AND scope_id=?", (sc, sid)).fetchone()
            if q and q["limit_usd"] > 0 and self.exposure(sc, sid) >= ALERT_THRESHOLD * q["limit_usd"]:
                alerts.append(f"quota {sc}/{sid} >= 90%")
        if alerts:
            log_event(self.conn, "warning", "budget", "; ".join(alerts), mission_id)
        return alerts

    def record(self, scope: str, scope_id: str, cost_usd: float, mission_id: str | None = None,
               provider: str | None = None, model: str | None = None,
               tokens_in: int = 0, tokens_out: int = 0, extra_scopes: list | None = None) -> dict:
        """Enregistre une dépense réelle via réservation + solde atomiques (0 pour les outils locaux)."""
        entries = [(scope, scope_id)] + list(extra_scopes or [])
        res = self.reserve(entries, cost_usd, mission_id=mission_id, provider=provider, model=model,
                           tokens_in_est=tokens_in, tokens_out_est=tokens_out)
        if not res.get("reserved"):
            return {"recorded": False, **res}
        try:
            return self.settle(res["reservation_id"], cost_usd, tokens_in=tokens_in, tokens_out=tokens_out,
                               provider=provider, model=model)
        except Exception as e:
            self.release(res["reservation_id"], reason=str(e), interrupted=True)
            return {"recorded": False, "reason": str(e)}

    def mission_cost(self, mission_id: str) -> float:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(cost_usd),0) s FROM budget_ledger WHERE mission_id=? AND scope='mission'",
            (mission_id,)).fetchone()
        return float(row["s"])

    def totals(self) -> dict:
        rows = self.conn.execute("SELECT scope, scope_id, SUM(cost_usd) s FROM budget_ledger GROUP BY scope, scope_id").fetchall()
        return {f"{r['scope']}/{r['scope_id']}": round(r["s"], 6) for r in rows}

    def exposure_totals(self) -> dict:
        keys = {tuple(k.split("/", 1)) for k in self.totals()}
        keys.update((r["scope"], r["scope_id"]) for r in self.conn.execute(
            "SELECT DISTINCT scope, scope_id FROM budget_reservation_scopes").fetchall())
        return {f"{sc}/{sid}": round(self.exposure(sc, sid), 6) for sc, sid in sorted(keys)}

    def ledger(self, limit: int = 100) -> list[dict]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM budget_ledger ORDER BY id DESC LIMIT ?", (limit,))]

    def reservations(self, limit: int = 100) -> list[dict]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM budget_reservations ORDER BY created_at DESC, id DESC LIMIT ?", (limit,))]
