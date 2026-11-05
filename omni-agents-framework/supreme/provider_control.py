"""Autorisation d'inférence, preuves de connexion et prix déclarés par l'opérateur.

Défaut fermé : aucune inférence externe sans autorisation humaine locale bornée
dans le temps, plafond USD et nombre d'appels. Les GET de découverte ne sont pas
des preuves de génération. Les tests HTTP locaux restent catégorie `local_test`
et ne peuvent jamais rendre un fournisseur connecté ou un agent opérationnel.
"""
from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from .budget import BudgetController
from .db import epoch, log_event, now, transaction

PRICE_MAX_AGE_DAYS = 30
CONNECTED_FRESH_SECONDS = 900
AUTH_CONFIRM = "AUTORISER INFERENCE"
PRICE_CONFIRM = "JE CONFIRME LES PRIX"


def _positive(value, name):
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} invalide") from exc
    if not math.isfinite(v) or v <= 0:
        raise ValueError(f"{name} doit être fini et strictement positif")
    return v


def is_external_endpoint(base_url: str) -> bool:
    p = urlparse(base_url)
    return p.scheme == "https" and p.hostname not in ("127.0.0.1", "::1", "localhost")


class ProviderControl:
    def __init__(self, conn, budget: BudgetController | None = None):
        self.conn = conn
        self.budget = budget or BudgetController(conn)

    def row(self, provider: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM provider_controls WHERE provider=?", (provider,)).fetchone()
        return dict(r) if r else None

    def authorize(self, provider: str, *, max_total_usd: float, max_calls: int,
                  hours: float, approved_by: str, confirm: str) -> dict:
        if confirm != AUTH_CONFIRM or not approved_by.strip():
            raise PermissionError("confirmation humaine explicite requise (CLI local uniquement)")
        cap = _positive(max_total_usd, "max_total_usd")
        hours = _positive(hours, "hours")
        if hours > 24:
            raise ValueError("une autorisation ne peut pas dépasser 24 heures")
        calls = int(max_calls)
        if calls < 1 or calls > 10000:
            raise ValueError("max_calls doit être entre 1 et 10000")
        approved_at = now()
        with transaction(self.conn, immediate=True):
            self.conn.execute(
                """INSERT INTO provider_controls(provider,inference_enabled,approved_by,approved_at,
                     expires_at,max_total_usd,max_calls,updated_at) VALUES(?,?,?,?,?,?,?,?)
                   ON CONFLICT(provider) DO UPDATE SET inference_enabled=1,approved_by=excluded.approved_by,
                     approved_at=excluded.approved_at,expires_at=excluded.expires_at,
                     max_total_usd=excluded.max_total_usd,max_calls=excluded.max_calls,updated_at=excluded.updated_at""",
                (provider, 1, approved_by.strip(), approved_at, epoch() + hours * 3600, cap, calls, now()))
            existing = self.conn.execute("SELECT limit_usd FROM quotas WHERE scope='provider' AND scope_id=?", (provider,)).fetchone()
            # Une autorisation ne relève jamais silencieusement un quota central existant.
            limit = min(cap, float(existing["limit_usd"])) if existing else cap
            self.conn.execute("INSERT OR REPLACE INTO quotas(scope,scope_id,limit_usd,period) VALUES('provider',?,?,'total')",
                              (provider, limit))
        log_event(self.conn, "info", "provider-control", f"inférence autorisée temporairement : {provider}",
                  data={"max_total_usd": cap, "max_calls": calls, "hours": hours, "approved_by": approved_by})
        return self.status(provider)

    def revoke(self, provider: str, *, confirm: str) -> dict:
        if confirm != "REVOQUER INFERENCE":
            raise PermissionError("confirmation humaine explicite requise")
        with transaction(self.conn, immediate=True):
            self.conn.execute("UPDATE provider_controls SET inference_enabled=0,expires_at=0,updated_at=? WHERE provider=?",
                              (now(), provider))
        return {"provider": provider, "inference_enabled": False}

    def set_price(self, provider: str, model: str, *, input_usd_per_million: float,
                  output_usd_per_million: float, source_url: str, confirm: str) -> dict:
        if confirm != PRICE_CONFIRM:
            raise PermissionError("confirmation humaine des prix requise")
        src = urlparse(source_url)
        if src.scheme != "https" or not src.hostname:
            raise ValueError("source de prix HTTPS requise")
        pin = _positive(input_usd_per_million, "prix entrée")
        pout = _positive(output_usd_per_million, "prix sortie")
        row = self.row(provider) or {"pricing_json": "{}"}
        prices = json.loads(row.get("pricing_json") or "{}")
        prices[model] = {"input_usd_per_million": pin, "output_usd_per_million": pout,
                         "source_url": source_url, "checked_at": now(),
                         "attestation": "operator_declared_not_invoice"}
        with transaction(self.conn, immediate=True):
            self.conn.execute(
                """INSERT INTO provider_controls(provider,pricing_json,updated_at) VALUES(?,?,?)
                   ON CONFLICT(provider) DO UPDATE SET pricing_json=excluded.pricing_json,updated_at=excluded.updated_at""",
                (provider, json.dumps(prices, ensure_ascii=False), now()))
        return {"provider": provider, "model": model, "pricing_attested": True,
                "inference_enabled": bool(row.get("inference_enabled", 0))}

    def price(self, provider: str, model: str) -> dict | None:
        row = self.row(provider)
        if not row:
            return None
        entry = json.loads(row.get("pricing_json") or "{}").get(model)
        if not entry:
            return None
        try:
            checked = datetime.fromisoformat(entry["checked_at"])
            age = (datetime.now(timezone.utc) - checked).total_seconds()
        except (KeyError, TypeError, ValueError):
            return None
        if age < 0 or age > PRICE_MAX_AGE_DAYS * 86400:
            return None
        return entry

    def window_usage(self, provider: str) -> dict:
        row = self.row(provider)
        if not row or not row.get("approved_at"):
            return {"cost_usd": 0.0, "exposure_usd": 0.0, "calls": 0}
        since = row["approved_at"]
        calls = self.conn.execute("SELECT COUNT(*) c FROM budget_reservations WHERE provider=? AND created_at>=?",
                                  (provider, since)).fetchone()["c"]
        settled = self.conn.execute("SELECT COALESCE(SUM(actual_cost_usd),0) s FROM budget_reservations WHERE provider=? AND created_at>=? AND status='settled'",
                                    (provider, since)).fetchone()["s"]
        held = self.conn.execute("SELECT COALESCE(SUM(amount_usd),0) s FROM budget_reservations WHERE provider=? AND created_at>=? AND status IN ('reserved','interrupted')",
                                 (provider, since)).fetchone()["s"]
        return {"cost_usd": float(settled), "exposure_usd": float(settled) + float(held), "calls": int(calls)}

    def preflight(self, provider: str, amount: float = 0.0) -> dict:
        """À appeler dans la transaction IMMEDIATE de réservation pour éviter les races."""
        row = self.row(provider)
        if not row or not row["inference_enabled"]:
            return {"allowed": False, "reason": "inférence externe non autorisée (CLI humain requis)"}
        if float(row["expires_at"]) <= epoch():
            return {"allowed": False, "reason": "autorisation d'inférence expirée"}
        usage = self.window_usage(provider)
        if usage["calls"] >= int(row["max_calls"]):
            return {"allowed": False, "reason": "nombre maximal d'appels autorisés atteint"}
        if usage["exposure_usd"] + amount > float(row["max_total_usd"]) + 1e-12:
            return {"allowed": False, "reason": "plafond USD de l'autorisation atteint"}
        return {"allowed": True, "reason": "autorisation humaine valide"}

    def status(self, provider: str) -> dict:
        row = self.row(provider)
        usage = self.window_usage(provider)
        prices = json.loads(row.get("pricing_json") or "{}") if row else {}
        return {"provider": provider, "inference_enabled": bool(row and row["inference_enabled"] and row["expires_at"] > epoch()),
                "approved_by": row.get("approved_by") if row else None,
                "approved_at": row.get("approved_at") if row else None,
                "expires_at": row.get("expires_at") if row else 0,
                "max_total_usd": row.get("max_total_usd", 0) if row else 0,
                "max_calls": row.get("max_calls", 0) if row else 0,
                "window_usage": usage, "priced_models": sorted(prices),
                "default": "closed", "authorization_surface": "local_cli_only"}

    def record_verification(self, provider: str, result: dict) -> str:
        vid = f"pv-{uuid.uuid4().hex[:16]}"
        ok = bool(result.get("ok"))
        category = result.get("category", "local_test")
        models = result.get("models", []) if ok else []
        with transaction(self.conn, immediate=True):
            self.conn.execute(
                """INSERT INTO provider_verifications(id,provider,ok,category,http_status,endpoint_host,
                     request_id,latency_ms,models_json,error,checked_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (vid, provider, int(ok), category, int(result.get("http_status", 0)),
                 result.get("endpoint_host", ""), result.get("request_id"), float(result.get("latency_ms", 0)),
                 json.dumps(models, ensure_ascii=False), str(result.get("error", ""))[:300], now()))
            if ok and category == "external_api":
                for m in models:
                    self.conn.execute(
                        """INSERT INTO provider_models(provider,model,capabilities_json,context,tools,
                             discovered_at,endpoint_host,request_id,category) VALUES(?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(provider,model) DO UPDATE SET capabilities_json=excluded.capabilities_json,
                             context=excluded.context,tools=excluded.tools,discovered_at=excluded.discovered_at,
                             endpoint_host=excluded.endpoint_host,request_id=excluded.request_id,category=excluded.category""",
                        (provider, m["id"], json.dumps(m.get("capabilities", [])), int(m.get("context", 0)),
                         int(bool(m.get("tools", False))), now(), result.get("endpoint_host", ""),
                         result.get("request_id"), category))
        return vid

    def discovered_models(self, provider: str) -> list[dict]:
        return [{"id": r["model"], "capabilities": json.loads(r["capabilities_json"]),
                 "context": r["context"], "tools": bool(r["tools"]), "discovered_at": r["discovered_at"]}
                for r in self.conn.execute("SELECT * FROM provider_models WHERE provider=? AND category='external_api' ORDER BY model", (provider,))]

    def summary(self) -> dict:
        rows = self.conn.execute(
            """SELECT v.* FROM provider_verifications v JOIN (
                 SELECT provider, MAX(checked_at) AS checked_at FROM provider_verifications
                 WHERE ok=1 AND category='external_api' GROUP BY provider
               ) latest ON latest.provider=v.provider AND latest.checked_at=v.checked_at
               WHERE v.ok=1 AND v.category='external_api'""").fetchall()
        verified = [dict(r) for r in rows]
        fresh = []
        for r in verified:
            try:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(r["checked_at"])).total_seconds()
                if 0 <= age <= CONNECTED_FRESH_SECONDS:
                    fresh.append(r["provider"])
            except ValueError:
                pass
        return {"verified_providers": sorted({r["provider"] for r in verified}),
                "connected_recently": sorted(set(fresh)),
                "verified_count": len({r["provider"] for r in verified}),
                "connected_recently_count": len(set(fresh)),
                "freshness_seconds": CONNECTED_FRESH_SECONDS,
                "note": "Une vérification ancienne reste une preuve historique, pas une disponibilité actuelle garantie."}
