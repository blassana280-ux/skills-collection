"""SearXNG — moteur auto-hébergé, sans clé API ni abonnement."""
from __future__ import annotations

import httpx

from .base import BaseProvider, SearchQuery, make_source, response_error
from ..core.errors import ProviderUnavailable
from ..core.schemas import SourceRecord


class SearXNGProvider(BaseProvider):
    name = "searxng"
    label = "SearXNG"
    requires_key = False
    strengths = ("general", "news", "science", "technology", "web", "osint")

    def is_configured(self) -> bool:
        return self.settings.searxng_enabled and bool(self.settings.searxng_url)

    async def search(self, client: httpx.AsyncClient,
                     query: SearchQuery) -> list[SourceRecord]:
        if not self.is_configured():
            raise ProviderUnavailable("SearXNG désactivé ou URL absente")
        url = self.settings.searxng_url.rstrip("/") + "/search"
        params = {"q": query.effective_text(), "format": "json",
                  "language": query.language or "all", "safesearch": 0,
                  "categories": "general"}
        r = await client.get(url, params=params, headers=self.headers())
        if r.status_code >= 400:
            raise response_error(r, self.name)
        payload = r.json()
        out: list[SourceRecord] = []
        for item in (payload.get("results") or [])[: query.limit]:
            href = item.get("url") or ""
            if not href.startswith(("http://", "https://")):
                continue
            out.append(make_source(
                url=href, title=item.get("title") or "",
                snippet=item.get("content") or "", provider=self.name,
                score=float(item.get("score") or 0.0),
                published_at=item.get("publishedDate"),
                raw={"engine": item.get("engine"), "category": item.get("category")},
            ))
        return out

    async def healthcheck(self, client: httpx.AsyncClient) -> tuple[bool, str]:
        try:
            r = await client.get(self.settings.searxng_url.rstrip("/") + "/healthz")
            return r.status_code < 400, f"http {r.status_code}"
        except Exception as exc:
            return False, f"injoignable: {type(exc).__name__}"
