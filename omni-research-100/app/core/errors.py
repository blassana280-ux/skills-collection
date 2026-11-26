"""Erreurs typées : aucune panne n'est silencieusement transformée en succès."""
from __future__ import annotations


class OmniError(Exception):
    code = "internal_error"
    status_code = 500

    def __init__(self, message: str, **detail: object) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail

    def as_dict(self) -> dict[str, object]:
        return {"error": self.code, "message": self.message, "detail": self.detail}


class ValidationError(OmniError):
    code = "validation_error"
    status_code = 422


class AuthenticationError(OmniError):
    code = "authentication_error"
    status_code = 401


class AuthorizationError(OmniError):
    code = "authorization_error"
    status_code = 403


class NotFoundError(OmniError):
    code = "not_found"
    status_code = 404


class RateLimitError(OmniError):
    code = "rate_limited"
    status_code = 429


class ProviderUnavailable(OmniError):
    code = "provider_unavailable"
    status_code = 503


class QuotaExceeded(OmniError):
    code = "quota_exceeded"
    status_code = 429


class MissionCancelled(OmniError):
    code = "mission_cancelled"
    status_code = 409


class InsufficientEvidence(OmniError):
    code = "insufficient_evidence"
    status_code = 422


class CapacityError(OmniError):
    code = "capacity_exceeded"
    status_code = 429


class UnsafeURL(OmniError):
    code = "unsafe_url"
    status_code = 400
