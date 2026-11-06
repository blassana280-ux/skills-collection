"""Réglages, santé, surveillance, journal d'audit, sauvegarde et rétention."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text

from ..core.db import AuditLog, ErrorLog, Metric, ProviderUsage
from ..core.errors import AuthorizationError, ValidationError
from ..core.schemas import PurgeIn, SettingsPatch
from .deps import Actor, audit, require, runtime_of

router = APIRouter(prefix="/api", tags=["system"])

_MUTABLE_FIELDS = {
    "max_parallel_agents", "max_concurrent_missions", "max_sources_per_mission",
    "rate_limit_per_minute", "retention_days",
}


@router.get("/health")
def health(rt=Depends(runtime_of)) -> dict[str, Any]:
    """Aucune authentification : sonde de vie minimale, sans secret."""
    try:
        with rt.store.session() as s:
            s.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        db_ok = False
        rt.store.record_error("health", str(exc), "", "warning")
    return {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
        "memory": rt.memory.describe(),
        "agents": rt.registry.validate()["agents"],
        "providers_configured": rt.router.registry.configured(),
        "active_missions": sorted(rt.commander.active),
        "default_secret_in_use": rt.settings.has_default_secret(),
        "time": time.time(),
    }


@router.get("/settings")
def get_settings_api(actor: Actor = Depends(require("settings:read")),
                     rt=Depends(runtime_of)) -> dict[str, Any]:
    return {
        "settings": rt.settings.public_dict(),
        "stored_overrides": {
            "disabled_providers": rt.store.get_setting("disabled_providers", []),
            "quota_overrides": rt.store.get_setting("quota_overrides", {}),
        },
        "modes": rt.status()["modes"],
    }


@router.patch("/settings")
def patch_settings(payload: SettingsPatch,
                   actor: Actor = Depends(require("settings:write")),
                   rt=Depends(runtime_of)) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    data = payload.model_dump(exclude_none=True)
    for key in _MUTABLE_FIELDS:
        if key in data:
            object.__setattr__(rt.settings, key, int(data[key]))
            changes[key] = int(data[key])
    if "retention_days" in changes:
        rt.memory.retention_days = changes["retention_days"]
    if "max_parallel_agents" in changes:
        rt.executor._semaphore = asyncio.Semaphore(changes["max_parallel_agents"])
    if "max_concurrent_missions" in changes:
        rt.commander._semaphore = asyncio.Semaphore(changes["max_concurrent_missions"])
    if "rate_limit_per_minute" in changes:
        rt.limiter.capacity = changes["rate_limit_per_minute"]
    if "disabled_providers" in data:
        rt.router.set_disabled(list(data["disabled_providers"]))
        changes["disabled_providers"] = sorted(rt.router.disabled)
    if "quota_overrides" in data:
        overrides = {str(k): int(v) for k, v in data["quota_overrides"].items()}
        rt.router.quota.overrides = overrides
        rt.store.set_setting("quota_overrides", overrides)
        changes["quota_overrides"] = overrides
    for key, value in changes.items():
        rt.store.set_setting(key, value)
    audit(rt, actor, "settings_patch", "settings", changes=changes)
    return {"applied": changes, "settings": rt.settings.public_dict()}


@router.get("/metrics")
def metrics(limit: int = 200,
            actor: Actor = Depends(require("metrics:read")),
            rt=Depends(runtime_of)) -> dict[str, Any]:
    rows = rt.store.filter(Metric, order_by=Metric.ts.desc(), limit=limit)
    usage = rt.store.filter(ProviderUsage, order_by=ProviderUsage.ts.desc(),
                            limit=limit)
    errors = rt.store.filter(ErrorLog, order_by=ErrorLog.ts.desc(), limit=limit)
    by_name: dict[str, list[float]] = {}
    for row in rows:
        by_name.setdefault(row.name, []).append(row.value)
    return {
        "metrics": [{"name": r.name, "value": r.value, "mission_id": r.mission_id,
                     "ts": r.ts, "detail": r.detail} for r in rows],
        "aggregates": {name: {"count": len(values),
                              "mean": round(sum(values) / len(values), 4),
                              "max": max(values)}
                       for name, values in by_name.items()},
        "provider_usage": [{"provider": u.provider, "status": u.status,
                            "latency_ms": u.latency_ms,
                            "result_count": u.result_count, "ts": u.ts}
                           for u in usage],
        "errors": [{"component": e.component, "message": e.message[:200],
                    "severity": e.severity, "ts": e.ts} for e in errors],
    }


@router.get("/audit")
def audit_log(limit: int = 200,
              actor: Actor = Depends(require("audit:read")),
              rt=Depends(runtime_of)) -> dict[str, Any]:
    rows = rt.store.filter(AuditLog, order_by=AuditLog.ts.desc(), limit=limit)
    return {"entries": [{"ts": r.ts, "actor": r.actor, "action": r.action,
                         "resource": r.resource, "detail": r.detail} for r in rows]}


@router.post("/backup")
def backup(actor: Actor = Depends(require("settings:write")),
           rt=Depends(runtime_of)) -> dict[str, Any]:
    destination = f"data/backups/omni-{int(time.time())}.db"
    try:
        path = rt.store.backup(destination)
    except NotImplementedError as exc:
        raise ValidationError(str(exc)) from exc
    audit(rt, actor, "backup", path)
    return {"backup": path, "bytes": Path(path).stat().st_size}


@router.post("/retention/purge")
def purge(payload: PurgeIn,
          actor: Actor = Depends(require("missions:purge")),
          rt=Depends(runtime_of)) -> dict[str, Any]:
    """SUPPRESSION DE DONNÉES — exige le mot `PURGE` et le rôle admin.

    Cette route n'est jamais appelée automatiquement par le système.
    """
    if actor.role != "admin":
        raise AuthorizationError("Réservé au rôle admin")
    if payload.confirm != "PURGE":
        raise ValidationError("Confirmation PURGE requise")
    deleted = rt.memory.purge_expired(payload.older_than_days, payload.confirm)
    audit(rt, actor, "retention_purge", "all", days=payload.older_than_days,
          deleted=deleted)
    return {"deleted": deleted, "older_than_days": payload.older_than_days}
