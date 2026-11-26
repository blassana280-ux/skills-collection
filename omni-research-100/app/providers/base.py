"""Contrat commun des connecteurs Internet.

Aucun connecteur ne fabrique de résultat : soit il appelle réellement le service
et parse la réponse, soit il lève une erreur explicite (« non configuré », quota,
panne, timeout). Les tests utilisent httpx.MockTransport, jamais le code de prod.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from ..core.config import Settings
from ..core.errors import ProviderUnavailable, QuotaExceeded, UnsafeURL
from ..core.schemas import SourceRecord
from ..core.security import check_url_syntax, sanitize_untrusted_text

_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "mc_cid", "mc_eid", "ref", "ref_src", "spm", "igshid",
}


@dataclass(frozen=True)
class SearchQuery:
    text: str
    limit: int = 10
    language: str = "fr"
    freshness: str | None = None  # day | week | month | year
    site: str | None = None
    category: str = "general"

    def effective_text(self) -> str:
        return f"{self.text} site:{self.site}" if self.site else self.text


@dataclass
class ExtractedPage:
    url: str
    title: str = ""
    text: str = ""
    published_at: str | None = None
    status_code: int = 200
    provider: str = "direct"
    injection_flags: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderState:
    name: str
    configured: bool
    enabled: bool = True
    consecutive_failures: int = 0
    open_until: float = 0.0
    last_error: str = ""
    last_latency_ms: float = 0.0
    total_calls: int = 0
    total_results: int = 0

    @property
    def circuit_open(self) -> bool:
        return time.time() < self.open_until

    def status(self) -> str:
        if not self.configured:
            return "not_configured"
        if not self.enabled:
            return "disabled"
        if self.circuit_open:
            return "cooldown"
        if self.consecutive_failures:
            return "degraded"
        return "configured"


def canonicalize_url(url: str) -> str:
    try:
        parts = urlsplit(url.strip())
        host = (parts.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        path = parts.path.rstrip("/") or "/"
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                 if k.lower() not in _TRACKING_PARAMS]
        return urlunsplit((parts.scheme.lower(), host, path, urlencode(query), ""))
    except ValueError:
        return url.strip()


def domain_of(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def content_hash(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(p or "" for p in parts).encode("utf-8")).hexdigest()


def make_source(*, url: str, title: str, snippet: str, provider: str,
                score: float = 0.0, published_at: str | None = None,
                raw: dict[str, Any] | None = None, verify_url: bool = True) -> SourceRecord:
    cleaned_title, flags_t = sanitize_untrusted_text(title, 2000)
    cleaned_snippet, flags_s = sanitize_untrusted_text(snippet, 8000)
    if verify_url:
        check_url_syntax(url)
    flags = sorted(set(flags_t + flags_s))
    canonical = canonicalize_url(url)
    return SourceRecord(
        url=url, title=cleaned_title.strip(), snippet=cleaned_snippet.strip(),
        provider=provider, score=float(score or 0.0), published_at=published_at,
        canonical_url=canonical, domain=domain_of(canonical),
        content_hash=content_hash(canonical, cleaned_title, cleaned_snippet),
        untrusted=True, injection_flags=flags, raw=raw or {},
    )


class BaseProvider:
    name = "base"
    label = "Base"
    requires_key = False
    supports_extract = False
    strengths: tuple[str, ...] = ("general",)

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.state = ProviderState(name=self.name, configured=self.is_configured())

    def is_configured(self) -> bool:
        return bool(self.settings.provider_keys().get(self.name))

    def quota(self) -> int:
        return self.settings.quota_for(self.name)

    def headers(self) -> dict[str, str]:
        return {"User-Agent": "OmniResearch100/1.0 (+research; contact: local)",
                "Accept": "application/json"}

    async def search(self, client: httpx.AsyncClient, query: SearchQuery) -> list[SourceRecord]:
        raise NotImplementedError  # pragma: no cover

    async def extract(self, client: httpx.AsyncClient, url: str) -> ExtractedPage:
        raise ProviderUnavailable(f"{self.label} ne prend pas en charge l'extraction")

    async def healthcheck(self, client: httpx.AsyncClient) -> tuple[bool, str]:
        """Vérification réelle et non destructive (aucune recherche facturée)."""
        return self.state.configured, self.state.status()


class QuotaManager:
    """Quotas journaliers persistés (table provider_usage) + surcharges à chaud."""

    def __init__(self, settings: Settings, store: Any) -> None:
        self.settings = settings
        self.store = store
        self.overrides: dict[str, int] = {}

    def limit_for(self, provider: str) -> int:
        return int(self.overrides.get(provider, self.settings.quota_for(provider)))

    def check(self, provider: str, mission_id: str = "") -> int:
        limit = self.limit_for(provider)
        used = self.store.usage_today(provider)
        if limit > 0 and used >= limit:
            self.store.record_usage(provider, "search", "quota_exceeded", 0, 0,
                                    mission_id, f"quota {used}/{limit}")
            raise QuotaExceeded(f"Quota journalier atteint pour {provider} ({used}/{limit})")
        return max(0, limit - used) if limit > 0 else -1

    def snapshot(self, names: list[str]) -> dict[str, dict[str, int]]:
        return {name: {"limit": self.limit_for(name),
                       "used": self.store.usage_today(name),
                       "remaining": (max(0, self.limit_for(name) - self.store.usage_today(name))
                                     if self.limit_for(name) > 0 else -1)}
                for name in names}


class CircuitBreaker:
    def __init__(self, cooldown_seconds: int = 30, threshold: int = 3) -> None:
        self.cooldown = cooldown_seconds
        self.threshold = threshold

    def allow(self, state: ProviderState) -> bool:
        return state.configured and state.enabled and not state.circuit_open

    def record_success(self, state: ProviderState, latency_ms: float, results: int) -> None:
        state.consecutive_failures = 0
        state.open_until = 0.0
        state.last_error = ""
        state.last_latency_ms = latency_ms
        state.total_calls += 1
        state.total_results += results

    def record_failure(self, state: ProviderState, error: str) -> None:
        state.consecutive_failures += 1
        state.last_error = error[:500]
        state.total_calls += 1
        if state.consecutive_failures >= self.threshold:
            state.open_until = time.time() + self.cooldown


def response_error(response: httpx.Response, provider: str) -> ProviderUnavailable:
    body = response.text[:300].replace("\n", " ")
    return ProviderUnavailable(
        f"{provider} HTTP {response.status_code}: {body}",
        provider=provider, status_code=response.status_code,
    )
