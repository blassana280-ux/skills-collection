"""Contrôle des fournisseurs : état réel, quotas, activation et test réel.

Aucune réponse de recherche n'est simulée : sans fournisseur configuré,
`/test` renvoie `not_configured` et zéro source.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..core.errors import NotFoundError, ValidationError
from ..core.schemas import ProviderTestIn
from .deps import Actor, audit, require, runtime_of

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("")
def providers(actor=Depends(require("providers:read")),
              rt=Depends(runtime_of)):
    return rt.router.status()


@router.get("/quota")
def quotas(actor=Depends(require("providers:read")),
           rt=Depends(runtime_of)):
    return {"quotas": rt.router.quota.snapshot(rt.router.registry.names()),
            "usage_today": {n: rt.store.usage_today(n)
                            for n in rt.router.registry.names()}}


@router.post("/{name}/test")
async def test_provider(name: str, payload: ProviderTestIn,
                        actor: Actor = Depends(require("providers:test")),
                        rt=Depends(runtime_of)):
    provider = rt.router.registry.get(name)
    if provider is None:
        raise NotFoundError(f"Fournisseur inconnu : {name}")
    if not provider.is_configured():
        audit(rt, actor, "provider_test", name, configured=False)
        return {"provider": name, "configured": False,
                "status": "not_configured", "sources": [], "real_results": False,
                "message": "Clé/URL absente : configurez le connecteur puis réessayez."}
    outcome = await rt.router.search(
        payload.query, mission_id="", limit=3, provider_names=[name],
        max_providers=1, verify_http=False,
    )
    real = bool(outcome.sources) and name in outcome.providers_real
    provider.state.configured = True
    if real:
        provider.state.verified_live = True  # preuve d'un appel réel réussi
    audit(rt, actor, "provider_test", name, sources=len(outcome.sources),
          real=real)
    return {
        "provider": name, "configured": True, "status": provider.state.status(),
        "sources": [s.to_dict() for s in outcome.sources],
        "errors": outcome.errors, "elapsed_ms": round(outcome.elapsed_ms, 2),
        "real_results": real,
        "quota": outcome.quota.get(name, {}),
    }


@router.patch("/{name}")
def toggle_provider(name: str, enabled: bool = Query(...),
                    actor: Actor = Depends(require("providers:configure")),
                    rt=Depends(runtime_of)):
    if rt.router.registry.get(name) is None:
        raise NotFoundError(f"Fournisseur inconnu : {name}")
    current = set(rt.router.disabled)
    if enabled:
        current.discard(name)
    else:
        current.add(name)
    rt.router.set_disabled(sorted(current))
    audit(rt, actor, "provider_toggle", name, enabled=enabled)
    return {"provider": name, "enabled": enabled,
            "disabled": sorted(rt.router.disabled)}
