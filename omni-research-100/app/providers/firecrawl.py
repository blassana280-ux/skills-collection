"""Firecrawl — recherche + extraction de pages (scrape Markdown)."""
from __future__ import annotations

import httpx

from .base import (BaseProvider, ExtractedPage, SearchQuery, make_source,
                   response_error)
from ..core.errors import ProviderUnavailable, UnsafeURL
from ..core.schemas import SourceRecord
from ..core.security import sanitize_untrusted_text, validate_public_url


class FirecrawlProvider(BaseProvider):
    name = "firecrawl"
    label = "Firecrawl"
    requires_key = True
    supports_extract = True
    strengths = ("general", "web", "technology", "deep")

    def _headers(self) -> dict[str, str]:
        key = self.settings.firecrawl_api_key
        if not key:
            raise ProviderUnavailable("OMNI_FIRECRAWL_API_KEY absente")
        return {**self.headers(), "Authorization": f"Bearer {key}"}

    async def search(self, client: httpx.AsyncClient,
                     query: SearchQuery) -> list[SourceRecord]:
        body = {"query": query.effective_text(),
                "limit": min(max(1, query.limit), 20),
                "scrapeOptions": {"formats": ["markdown"]}}
        r = await client.post(self.settings.firecrawl_base_url.rstrip("/") + "/search",
                              json=body, headers=self._headers())
        if r.status_code >= 400:
            raise response_error(r, self.name)
        payload = r.json()
        if payload.get("success") is False:
            raise ProviderUnavailable(f"Firecrawl: {payload.get('error', 'échec')}")
        data = payload.get("data") or []
        if isinstance(data, dict):
            data = data.get("web") or []
        out: list[SourceRecord] = []
        for item in data[: query.limit]:
            href = item.get("url") or ""
            if not href.startswith(("http://", "https://")):
                continue
            out.append(make_source(
                url=href, title=item.get("title") or "",
                snippet=(item.get("description") or item.get("markdown") or "")[:8000],
                provider=self.name, score=0.5,
                published_at=item.get("publishedTime"),
                raw={"source": "firecrawl-search"},
            ))
        return out

    async def extract(self, client: httpx.AsyncClient, url: str) -> ExtractedPage:
        validate_public_url(url)
        r = await client.post(self.settings.firecrawl_base_url.rstrip("/") + "/scrape",
                              json={"url": url, "formats": ["markdown"]},
                              headers=self._headers())
        if r.status_code >= 400:
            raise response_error(r, self.name)
        payload = r.json()
        data = payload.get("data") or {}
        metadata = data.get("metadata") or {}
        text, flags = sanitize_untrusted_text(data.get("markdown") or "", 200_000)
        return ExtractedPage(
            url=url, title=str(metadata.get("title") or ""), text=text,
            published_at=metadata.get("publishedTime"), status_code=r.status_code,
            provider=self.name, injection_flags=flags,
            raw={"statusCode": data.get("statusCode")},
        )
