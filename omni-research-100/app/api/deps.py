"""Dépendances d'authentification, permissions, limitation de débit et accès
au runtime. Aucune route n'est accessible sans acteur identifié.
"""
from __future__ import annotations

from typing import Any, Callable

from fastapi import Depends, Request

from ..core.errors import AuthenticationError, AuthorizationError, OmniError
from ..core.security import (constant_time_equals, decode_token,
                             has_permission, redact)
from ..core.logging_conf import log_event


class Actor:
    def __init__(self, subject: str, role: str, via: str = "jwt") -> None:
        self.subject = subject
        self.role = role
        self.via = via

    def as_dict(self) -> dict[str, str]:
        return {"subject": self.subject, "role": self.role, "via": self.via}


def runtime_of(request: Request) -> Any:
    return request.app.state.runtime


def get_actor(request: Request, rt: Any = Depends(runtime_of)) -> Actor:
    api_key = request.headers.get("X-OmniBrain-Key")
    if api_key:
        if constant_time_equals(api_key, rt.settings.omnibrain_api_key):
            return Actor("omnibrain", "omnibrain", "api_key")
        log_event("auth", "invalid_api_key", level="WARNING")
        raise AuthenticationError("Clé API OmniBrain invalide")
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise AuthenticationError("Jeton Bearer requis")
    payload = decode_token(header[7:].strip(), rt.settings.auth_secret)
    return Actor(str(payload["sub"]), str(payload["role"]), "jwt")


def require(permission: str) -> Callable[..., Actor]:
    def dependency(actor: Actor = Depends(get_actor)) -> Actor:
        if not has_permission(actor.role, permission):
            raise AuthorizationError(f"Permission refusée : {permission}")
        return actor
    return dependency


def rate_limit(request: Request, actor: Actor = Depends(get_actor),
               rt: Any = Depends(runtime_of)) -> None:
    key = f"{actor.subject}:{request.url.path}"
    rt.limiter.check(key)


def audit(rt: Any, actor: Actor, action: str, resource: str = "",
          **detail: Any) -> None:
    rt.store.audit(actor.subject, action, resource,
                   **{k: redact(str(v)) if isinstance(v, str) else v
                      for k, v in detail.items()})


def error_payload(exc: OmniError) -> dict[str, Any]:
    return exc.as_dict()
