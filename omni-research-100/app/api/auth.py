"""Authentification : comptes locaux hashés, JWT signés, matrice de permissions."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core.db import UserRow
from ..core.errors import AuthenticationError
from ..core.schemas import LoginIn, TokenOut
from ..core.security import create_token, permission_matrix, verify_password
from .deps import Actor, audit, get_actor, rate_limit, require, runtime_of

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, rt=Depends(runtime_of)) -> TokenOut:
    rt.limiter.check(f"login:{payload.username}")
    user: UserRow | None = rt.store.get(UserRow, payload.username)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AuthenticationError("Identifiants invalides")
    token = create_token(user.username, user.role, rt.settings.auth_secret,
                         rt.settings.token_ttl_minutes)
    rt.store.audit(user.username, "login", "auth")
    return TokenOut(access_token=token, role=user.role,
                    expires_in=rt.settings.token_ttl_minutes * 60)


@router.get("/me")
def me(actor: Actor = Depends(get_actor)) -> dict[str, str]:
    return actor.as_dict()


@router.get("/permissions")
def permissions(actor: Actor = Depends(require("settings:read"))) -> dict[str, object]:
    return {"roles": permission_matrix(), "current": actor.as_dict()}
