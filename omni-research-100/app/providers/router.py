"""Routage intelligent, recherche parallèle, bascule, quotas, déduplication,
vérification des sources et conservation des preuves.

Règle absolue : si aucun fournisseur ne répond, `sources` est VIDE et les
erreurs sont explicites. Aucun résultat n'est fabriqué.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

from ..core.config import Settings
from ..core.db import Evidence, Source, Store
from ..core.errors import (ProviderUnavailable, QuotaExceeded, UnsafeURL)
from ..core.logging_conf import log_event
from ..core.schemas import SourceRecord
from ..core.security import check_url_syntax
from .base import (CircuitBreaker, QuotaManager, SearchQuery, content_hash,
                   make_source)
from .extractor import DirectExtraction
from .registry import ProviderRegistry

_CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("news", ("actualité", "news", "breaking", "aujourd'hui", "today", "dernier",
              "récent", "communiqué", "headline", "event")),
    ("science", ("étude", "study", "paper", "research", "pubmed", "arxiv", "doi",
                 "clinical", "scientifique", "peer review", "preprint")),
    ("technology", ("api", "github", "release", "version", "benchmark", "code",
                    "library", "framework", "documentation", "changelog", "sdk")),
    ("osint", ("repository", "commit", "maintainer", "domain", "whois", "package",
               "registry", "open source", "provenance")),
    ("social", ("tweet", "post", "hashtag", "reddit", "forum", "sentiment",
                "viral", "community", "social")),
    ("data", ("dataset", "csv", "statistique", "statistics", "timeseries",
              "série temporelle", "corrélation", "données", "data")),
    ("fact_check", ("vrai ou faux", "fact check", "verify", "vérifier", "rumeur",
                    "claim", "affirmation", "démenti")),
    ("deep", ("comparer", "analyse approfondie", "pourquoi", "impact", "revue",
              "state of the art", "synthèse", "contradiction")),
)

_PRIORITY: dict[str, tuple[str, ...]] = {
    "news": ("brave", "searxng", "tavily", "exa", "firecrawl"),
    "science": ("exa", "tavily", "searxng", "brave", "firecrawl"),
    "technology": ("exa", "firecrawl", "brave", "searxng", "tavily"),
    "osint": ("exa", "searxng", "brave", "tavily", "firecrawl"),
    "social": ("brave", "tavily", "searxng", "exa", "firecrawl"),
    "data": ("exa", "tavily", "searxng", "brave", "firecrawl"),
    "fact_check": ("brave", "tavily", "exa", "searxng", "firecrawl"),
    "deep": ("tavily", "exa", "searxng", "brave", "firecrawl"),
    "general": ("searxng", "brave", "tavily", "exa", "firecrawl"),
}


@dataclass
class SearchOutcome:
    sources: list[SourceRecord] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)
    providers_used: list[str] = field(default_factory=list)
    providers_attempted: list[str] = field(default_factory=list)
    providers_real: list[str] = field(default_factory=list)
    dedup_removed: int = 0
    category: str = "general"
    ranking: list[str] = field(default_factory=list)
    quota: dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    extracted: int = 0

    @property
    def has_real_sources(self) -> bool:
        return bool(self.sources)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sources": [s.to_dict() for s in self.sources],
            "errors": self.errors, "providers_used": self.providers_used,
            "providers_real": self.providers_real,
            "providers_attempted": self.providers_attempted,
            "dedup_removed": self.dedup_removed, "category": self.category,
            "ranking": self.ranking, "quota": self.quota,
            "elapsed_ms": round(self.elapsed_ms, 2), "extracted": self.extracted,
            "source_count": len(self.sources),
        }


class ProviderRouter:
    def __init__(self, settings: Settings, store: Store,
                 registry: ProviderRegistry | None = None,
                 quota: QuotaManager | None = None,
                 client_factory: Callable[[], httpx.AsyncClient] | None = None,
                 breaker: CircuitBreaker | None = None) -> None:
        self.settings = settings
        self.store = store
        self.registry = registry or ProviderRegistry(settings)
        self.quota = quota or QuotaManager(settings, store)
        self.breaker = breaker or CircuitBreaker(settings.provider_failure_cooldown_seconds)
        self.client_factory = client_factory
        self.direct = DirectExtraction(settings)
        self.disabled: set[str] = set(
            self.store.get_setting("disabled_providers", []) or []
        )

    # -- décision -----------------------------------------------------------
    @staticmethod
    def category_for(text: str) -> str:
        low = (text or "").lower()
        best, score = "general", 0
        for category, keywords in _CATEGORY_RULES:
            hits = sum(1 for kw in keywords if kw in low)
            if hits > score:
                best, score = category, hits
        return best

    def rank(self, category: str) -> list[str]:
        order = list(_PRIORITY.get(category, _PRIORITY["general"]))
        known = set(self.registry.names())
        order = [n for n in order if n in known]
        order += [n for n in self.registry.names() if n not in order]
        return [n for n in order if n not in self.disabled]

    def _make_client(self) -> httpx.AsyncClient:
        if self.client_factory is not None:
            return self.client_factory()
        return httpx.AsyncClient(timeout=self.settings.http_timeout_seconds,
                                 follow_redirects=True)

    # -- appel unitaire -----------------------------------------------------
    async def _call(self, provider_name: str, client: httpx.AsyncClient,
                    sq: SearchQuery, mission_id: str) -> list[SourceRecord]:
        provider = self.registry.get(provider_name)
        if provider is None:
            raise ProviderUnavailable(f"Fournisseur inconnu : {provider_name}")
        provider.state.configured = provider.is_configured()
        self.quota.check(provider_name, mission_id)
        started = time.perf_counter()
        try:
            results = await asyncio.wait_for(
                provider.search(client, sq), timeout=self.settings.http_timeout_seconds
            )
            latency = (time.perf_counter() - started) * 1000
            self.breaker.record_success(provider.state, latency, len(results))
            provider.state.configured = True
            self.store.record_usage(provider_name, "search", "ok", latency, len(results),
                                    mission_id)
            log_event("providers", "search_ok", mission_id=mission_id,
                      provider=provider_name, results=len(results),
                      latency_ms=round(latency, 1))
            return results
        except QuotaExceeded:
            raise
        except Exception as exc:
            latency = (time.perf_counter() - started) * 1000
            self.breaker.record_failure(provider.state, str(exc))
            self.store.record_usage(provider_name, "search", "error", latency, 0,
                                    mission_id, str(exc))
            self.store.record_error("provider", str(exc), mission_id, "warning")
            log_event("providers", "search_failed", level="WARNING",
                      mission_id=mission_id, provider=provider_name,
                      error_type=type(exc).__name__)
            raise

    # -- recherche parallèle + bascule -------------------------------------
    async def search(self, text: str, *, mission_id: str = "", limit: int = 10,
                     language: str = "fr", category: str | None = None,
                     freshness: str | None = None, site: str | None = None,
                     provider_names: list[str] | None = None,
                     max_providers: int | None = None,
                     verify_http: bool = False) -> SearchOutcome:
        started = time.perf_counter()
        cat = category or self.category_for(text)
        ranking = provider_names or self.rank(cat)
        sq = SearchQuery(text=text, limit=limit, language=language,
                         freshness=freshness, site=site, category=cat)
        outcome = SearchOutcome(category=cat, ranking=ranking)

        candidates: list[str] = []
        for name in ranking:
            provider = self.registry.get(name)
            if provider is None or name in self.disabled:
                continue
            provider.state.configured = provider.is_configured()
            if not self.breaker.allow(provider.state):
                outcome.errors.append({"provider": name,
                                       "error": f"indisponible ({provider.state.status()})"})
                continue
            try:
                self.quota.check(name, mission_id)
            except QuotaExceeded as exc:
                outcome.errors.append({"provider": name, "error": exc.message})
                continue
            candidates.append(name)
            if max_providers and len(candidates) >= max_providers:
                break

        gathered: list[SourceRecord] = []
        if candidates:
            client = self._make_client()
            try:
                calls = [self._call(name, client, sq, mission_id) for name in candidates]
                responses = await asyncio.gather(*calls, return_exceptions=True)
            finally:
                await client.aclose()
            outcome.providers_attempted = list(candidates)
            for name, response in zip(candidates, responses):
                if isinstance(response, BaseException):
                    outcome.errors.append({"provider": name,
                                           "error": f"{type(response).__name__}: {response}"[:300]})
                    continue
                if response:
                    outcome.providers_used.append(name)
                    gathered.extend(response)

        # Bascule automatique : providers restants, en série, si rien n'est revenu.
        if not gathered:
            for name in ranking:
                provider = self.registry.get(name)
                if name in candidates or provider is None or name in self.disabled:
                    continue
                provider.state.configured = provider.is_configured()
                if not self.breaker.allow(provider.state):
                    continue
                client = self._make_client()
                try:
                    extra = await self._call(name, client, sq, mission_id)
                except Exception as exc:
                    outcome.errors.append({"provider": name,
                                           "error": f"fallback: {exc}"[:300]})
                    extra = []
                finally:
                    await client.aclose()
                outcome.providers_attempted.append(name)
                if extra:
                    outcome.providers_used.append(name)
                    gathered.extend(extra)
                    break

        outcome.providers_real = [
            name for name in outcome.providers_used
            if not getattr(self.registry.get(name), "test_double", False)
        ]
        deduped, removed = self.dedupe(gathered)
        outcome.dedup_removed = removed
        outcome.sources = deduped[: max(1, limit)]
        outcome.quota = self.quota.snapshot(self.registry.names())
        if verify_http:
            await self.verify_sources(outcome.sources, mission_id)
        if mission_id:
            self.preserve_evidence(outcome.sources, mission_id)
        outcome.elapsed_ms = (time.perf_counter() - started) * 1000
        if not outcome.sources:
            log_event("providers", "no_sources", level="WARNING", mission_id=mission_id,
                      category=cat, attempted=outcome.providers_attempted,
                      errors=len(outcome.errors))
        return outcome

    # -- déduplication ------------------------------------------------------
    @staticmethod
    def dedupe(sources: list[SourceRecord]) -> tuple[list[SourceRecord], int]:
        by_key: dict[str, SourceRecord] = {}
        removed = 0
        for src in sources:
            key = src.canonical_url or src.url
            if key in by_key:
                removed += 1
                existing = by_key[key]
                extra = existing.raw.setdefault("also_found_by", [])
                if src.provider not in extra:
                    extra.append(src.provider)
                existing.score = max(existing.score, src.score)
                if len(src.snippet) > len(existing.snippet):
                    existing.snippet = src.snippet
                continue
            by_key[key] = src
        return list(by_key.values()), removed

    # -- vérification des sources ------------------------------------------
    async def verify_sources(self, sources: list[SourceRecord],
                             mission_id: str = "", max_checks: int = 8) -> int:
        """Vérification HTTP réelle (HEAD/GET) d'un nombre borné de sources.
        Une source non joignable reste `verified=False` : jamais de faux positif."""
        checked = 0
        client = self._make_client()
        try:
            for src in sources[:max_checks]:
                try:
                    check_url_syntax(src.url)
                    r = await asyncio.wait_for(client.head(src.url),
                                               timeout=min(5, self.settings.http_timeout_seconds))
                    src.http_status = r.status_code
                    src.verified = r.status_code < 400
                    checked += 1
                except (Exception, UnsafeURL) as exc:
                    src.http_status = None
                    src.verified = False
                    src.raw["verification_error"] = type(exc).__name__
        finally:
            await client.aclose()
        if mission_id:
            for src in sources[:max_checks]:
                if src.source_id:
                    self.store.update(Source, src.source_id, verified=src.verified,
                                      http_status=src.http_status)
        return checked

    # -- conservation des preuves ------------------------------------------
    def preserve_evidence(self, sources: list[SourceRecord], mission_id: str) -> int:
        count = 0
        for src in sources:
            sid = f"{mission_id}-{src.content_hash[:16]}"
            src.source_id = sid
            if self.store.get(Source, sid) is not None:
                continue
            self.store.add(Source(
                id=sid, mission_id=mission_id, url=src.url,
                canonical_url=src.canonical_url, domain=src.domain, title=src.title,
                snippet=src.snippet, provider=src.provider, score=src.score,
                published_at=src.published_at, content_hash=src.content_hash,
                verified=src.verified, http_status=src.http_status,
                untrusted=True, injection_flags=src.injection_flags,
                fetched_at=src.fetched_at, raw=src.raw,
            ))
            self.store.add(Evidence(
                id=f"ev-{sid}", mission_id=mission_id, source_id=sid,
                quote=src.snippet[:1000], content_hash=src.content_hash,
                untrusted=True, injection_flags=src.injection_flags,
                meta={"provider": src.provider, "domain": src.domain,
                      "url": src.url, "title": src.title},
            ))
            count += 1
        return count

    # -- extraction de pages -----------------------------------------------
    async def extract_pages(self, sources: list[SourceRecord], mission_id: str,
                            limit: int | None = None) -> int:
        """Extraction parallèle, bornée, avec garde SSRF et preuves conservées."""
        cap = limit if limit is not None else self.settings.max_extractions_per_mission
        targets = [s for s in sources if s.url][: max(0, cap)]
        if not targets:
            return 0
        firecrawl = self.registry.get("firecrawl")
        use_firecrawl = bool(firecrawl and firecrawl.is_configured()
                             and "firecrawl" not in self.disabled)
        client = self._make_client()

        async def one(src: SourceRecord) -> bool:
            try:
                page = await (firecrawl.extract(client, src.url) if use_firecrawl
                              else self.direct.extract(client, src.url))
            except Exception as exc:
                self.store.record_error("extractor", str(exc), mission_id, "warning")
                log_event("providers", "extract_failed", level="WARNING",
                          mission_id=mission_id, url=src.url, error=type(exc).__name__)
                return False
            src.text = page.text
            src.injection_flags = sorted(set(src.injection_flags + page.injection_flags))
            src.published_at = src.published_at or page.published_at
            src.raw["extracted_by"] = page.provider
            src.raw["extracted_bytes"] = len(page.text)
            src.content_hash = content_hash(src.canonical_url, src.title,
                                            src.snippet, page.text)
            if src.source_id:
                self.store.update(Source, src.source_id,
                                  content_hash=src.content_hash,
                                  injection_flags=src.injection_flags,
                                  published_at=src.published_at, raw=src.raw)
                self.store.add(Evidence(
                    id=f"ev-{src.source_id}-full", mission_id=mission_id,
                    source_id=src.source_id, quote=page.text[:1500],
                    content_hash=src.content_hash, untrusted=True,
                    injection_flags=page.injection_flags,
                    meta={"kind": "full_text", "extracted_by": page.provider,
                          "url": src.url, "title": page.title},
                ))
            return True

        try:
            results = await asyncio.gather(*[one(s) for s in targets],
                                           return_exceptions=True)
        finally:
            await client.aclose()
        return sum(1 for r in results if r is True)

    # -- exposition d'état --------------------------------------------------
    def status(self) -> dict[str, Any]:
        return {
            "providers": self.registry.describe(self.quota),
            "configured": self.registry.configured(),
            "disabled": sorted(self.disabled),
            "category_priority": {k: list(v) for k, v in _PRIORITY.items()},
            "dns_ssrf_check": self.settings.dns_ssrf_check,
        }

    def set_disabled(self, names: list[str]) -> None:
        allowed = set(self.registry.names())
        self.disabled = {n for n in names if n in allowed}
        self.store.set_setting("disabled_providers", sorted(self.disabled))
        for p in self.registry.all():
            p.state.enabled = p.name not in self.disabled
