"""Brave Search API — index indépendant, adapté à l'actualité et au web général."""
from __future__ import annotations

import httpx

from .base import BaseProvider, SearchQuery, make_source, response_error
from ..core.errors import ProviderUnavailable
from ..core.schemas import SourceRecord


class BraveProvider(BaseProvider):
    name = "brave"
    label = "Brave Search"
    requires_key = True
    strengths = ("general", "news", "web", "fact_check")

    async def search(self, client: httpx.AsyncClient,
                     query: SearchQuery) -> list[SourceRecord]:
        key = self.settings.brave_api_key
        if not key:
            raise ProviderUnavailable("OMNI_BRAVE_API_KEY absente")
        params = {"q": query.effective_text(), "count": min(max(1, query.limit), 20),
                  "search_lang": query.language or "fr", "safesearch": "moderate"}
        if query.freshness:
            params["freshness"] = {"day": "pd", "week": "pw",
                                   "month": "pm", "year": "py"}.get(query.freshness, "")
        headers = {**self.headers(), "X-Subscription-Token": key,
                   "Accept-Encoding": "gzip"}
        r = await client.get(self.settings.brave_base_url.rstrip("/") + "/res/v1/web/search",
                             params=params, headers=headers)
        if r.status_code >= 400:
            raise response_error(r, self.name)
        payload = r.json()
        web = payload.get("web") or {}
        out: list[SourceRecord] = []
        for item in (web.get("results") or [])[: query.limit]:
            href = item.get("url") or ""
            if not href.startswith(("http://", "https://")):
                continue
            out.append(make_source(
                url=href, title=item.get("title") or "",
                snippet=item.get("description") or "", provider=self.name,
                score=0.5, published_at=item.get("page_age"),
                raw={"age": item.get("age"), "family_friendly": item.get("family_friendly")},
            ))
        return out
