"""Tavily Search API — recherche orientée agent, avec contenu extrait."""
from __future__ import annotations

import httpx

from .base import BaseProvider, SearchQuery, make_source, response_error
from ..core.errors import ProviderUnavailable
from ..core.schemas import SourceRecord


class TavilyProvider(BaseProvider):
    name = "tavily"
    label = "Tavily"
    requires_key = True
    strengths = ("general", "deep", "news", "science", "synthesis")

    async def search(self, client: httpx.AsyncClient,
                     query: SearchQuery) -> list[SourceRecord]:
        key = self.settings.tavily_api_key
        if not key:
            raise ProviderUnavailable("OMNI_TAVILY_API_KEY absente")
        body = {
            "api_key": key, "query": query.effective_text(),
            "search_depth": "advanced" if query.category in {"deep", "science"} else "basic",
            "max_results": min(max(1, query.limit), 20),
            "include_answer": False, "include_raw_content": False,
        }
        if query.freshness in {"day", "week", "month", "year"}:
            body["topic"] = "news"
            body["days"] = {"day": 1, "week": 7, "month": 30, "year": 365}[query.freshness]
        headers = {**self.headers(), "Authorization": f"Bearer {key}"}
        r = await client.post(self.settings.tavily_base_url.rstrip("/") + "/search",
                              json=body, headers=headers)
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
                published_at=item.get("published_date"),
                raw={"raw_content": bool(item.get("raw_content"))},
            ))
        return out
