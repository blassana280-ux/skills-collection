"""Exa — recherche neuronale / sémantique (papiers, documentation, code)."""
from __future__ import annotations

import httpx

from .base import BaseProvider, SearchQuery, make_source, response_error
from ..core.errors import ProviderUnavailable
from ..core.schemas import SourceRecord


class ExaProvider(BaseProvider):
    name = "exa"
    label = "Exa"
    requires_key = True
    strengths = ("science", "technology", "deep", "osint", "data")

    async def search(self, client: httpx.AsyncClient,
                     query: SearchQuery) -> list[SourceRecord]:
        key = self.settings.exa_api_key
        if not key:
            raise ProviderUnavailable("OMNI_EXA_API_KEY absente")
        body = {
            "query": query.effective_text(),
            "numResults": min(max(1, query.limit), 20),
            "type": "auto",
            "contents": {"text": {"maxCharacters": 2000}},
        }
        headers = {**self.headers(), "x-api-key": key}
        r = await client.post(self.settings.exa_base_url.rstrip("/") + "/search",
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
                snippet=(item.get("text") or "")[:8000], provider=self.name,
                score=float(item.get("score") or 0.0),
                published_at=item.get("publishedDate"),
                raw={"author": item.get("author"), "id": item.get("id")},
            ))
        return out
