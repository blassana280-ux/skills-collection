"""Evidence Collector : normalisation, déduplication, vérification et
conservation des preuves avec empreintes et citations stables.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core.db import Evidence, Source, Store
from ..core.logging_conf import log_event
from ..core.schemas import SourceRecord
from ..core.security import check_url_syntax
from ..providers.router import SearchOutcome


@dataclass
class EvidenceBundle:
    docs: list[SourceRecord] = field(default_factory=list)
    citations: list[dict[str, str]] = field(default_factory=list)
    citation_by_id: dict[str, str] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)
    rejected: list[dict[str, str]] = field(default_factory=list)

    def citation_for(self, source_id: str) -> str:
        return self.citation_by_id.get(source_id, "")


class EvidenceCollector:
    def __init__(self, store: Store) -> None:
        self.store = store

    def collect(self, outcome: SearchOutcome, mission_id: str) -> EvidenceBundle:
        bundle = EvidenceBundle()
        domains: set[str] = set()
        providers: set[str] = set()
        flags = 0
        for source in outcome.sources:
            try:
                check_url_syntax(source.url)
            except Exception as exc:
                bundle.rejected.append({"url": source.url[:200],
                                        "reason": f"{type(exc).__name__}"})
                continue
            if not source.source_id:
                source.source_id = f"{mission_id}-{source.content_hash[:16]}"
            index = f"S{len(bundle.citations) + 1}"
            bundle.citation_by_id[source.id] = index
            bundle.citations.append({
                "index": index, "id": source.id, "url": source.url,
                "title": source.title[:200], "domain": source.domain,
                "provider": source.provider,
                "content_hash": source.content_hash,
                "verified": "yes" if source.verified else "no",
                "untrusted": "yes",
            })
            bundle.docs.append(source)
            domains.add(source.domain)
            providers.add(source.provider)
            flags += len(source.injection_flags)
            if self.store.get(Source, source.source_id) is None:
                self.store.add(Source(
                    id=source.source_id, mission_id=mission_id, url=source.url,
                    canonical_url=source.canonical_url, domain=source.domain,
                    title=source.title, snippet=source.snippet,
                    provider=source.provider, score=source.score,
                    published_at=source.published_at,
                    content_hash=source.content_hash, verified=source.verified,
                    http_status=source.http_status, untrusted=True,
                    injection_flags=source.injection_flags,
                    fetched_at=source.fetched_at, raw=source.raw,
                ))
        bundle.stats = {
            "sources": len(bundle.docs), "rejected": len(bundle.rejected),
            "domains": len(domains), "providers": len(providers),
            "verified": sum(1 for d in bundle.docs if d.verified),
            "https": sum(1 for d in bundle.docs if d.url.startswith("https://")),
            "injection_flags": flags,
            "dedup_removed": outcome.dedup_removed,
            "providers_used": outcome.providers_used,
            "providers_real": outcome.providers_real,
            "search_errors": outcome.errors,
            "evidence_rows": self.store.count(Evidence),
        }
        log_event("evidence", "collected", mission_id=mission_id,
                  sources=len(bundle.docs), domains=len(domains),
                  injections=flags, rejected=len(bundle.rejected))
        return bundle
