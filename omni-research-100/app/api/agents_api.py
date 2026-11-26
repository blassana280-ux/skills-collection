"""Exposition du registre des 100 agents et de l'export OmniBrain."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.errors import NotFoundError
from .deps import require, runtime_of

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("")
def agents(division: str | None = None, limit: int = 100,
           actor=Depends(require("agents:read")), rt=Depends(runtime_of)):
    specs = rt.registry.specs
    if division:
        specs = tuple(s for s in specs if s.division_code.upper() == division.upper())
    return {
        "total": len(rt.registry.specs), "returned": min(limit, len(specs)),
        "divisions": list(rt.registry.by_division().keys()),
        "agents": [s.to_dict() for s in specs[: max(1, limit)]],
    }


@router.get("/divisions")
def divisions(actor=Depends(require("agents:read")),
              rt=Depends(runtime_of)):
    return rt.registry.by_division()


@router.get("/validation")
def validation(actor=Depends(require("agents:read")),
               rt=Depends(runtime_of)):
    return {"valid": True, **rt.registry.validate()}


@router.get("/export/omnibrain")
def export_omnibrain(actor=Depends(require("agents:read")),
                     rt=Depends(runtime_of)):
    return rt.registry.export_for_omnibrain()


@router.get("/{agent_id}")
def agent_detail(agent_id: str, actor=Depends(require("agents:read")),
                 rt=Depends(runtime_of)):
    try:
        spec = rt.registry.get(agent_id.upper())
    except Exception as exc:
        raise NotFoundError(f"Agent inconnu : {agent_id}") from exc
    return {"spec": spec.to_dict(),
            "handler": rt.registry.handler(spec.id).__name__,
            "handler_callable": callable(rt.registry.handler(spec.id))}
