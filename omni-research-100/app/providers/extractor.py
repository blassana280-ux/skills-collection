"""Extraction de pages : parsing HTML réel (stdlib), sans exécution de code.

Tout script, style, iframe, formulaire ou balise active est ignoré. Le texte est
neutralisé contre les injections de prompts et conservé comme DONNÉE NON FIABLE.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

import httpx

from .base import ExtractedPage
from ..core.config import Settings
from ..core.errors import ProviderUnavailable, UnsafeURL
from ..core.security import sanitize_untrusted_text, validate_public_url

_SKIP = {"script", "style", "noscript", "iframe", "object", "embed", "svg",
         "nav", "footer", "header", "aside", "form", "template", "canvas"}


class HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.meta: dict[str, str] = {}
        self.chunks: list[str] = []
        self.links: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _SKIP:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        attributes = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            key = (attributes.get("name") or attributes.get("property") or "").lower()
            if key:
                self.meta[key] = attributes.get("content", "")
        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])
        if tag in {"p", "br", "li", "h1", "h2", "h3", "h4", "div", "section"}:
            self.chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _SKIP and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self.title_parts.append(data)
        text = data.strip()
        if text:
            self.chunks.append(text + " ")

    @property
    def text(self) -> str:
        joined = "".join(self.chunks)
        return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]{2,}", " ", joined)).strip()

    @property
    def title(self) -> str:
        return " ".join(self.title_parts).strip()[:500]

    def published_at(self) -> str | None:
        for key in ("article:published_time", "date", "datepublished", "dc.date",
                    "og:published_time", "publishdate", "timestamp"):
            if self.meta.get(key):
                return self.meta[key][:80]
        return None


def parse_html(html: str, url: str, status_code: int = 200,
               provider: str = "direct") -> ExtractedPage:
    parser = HTMLTextExtractor()
    parser.feed(html)
    parser.close()
    cleaned, flags = sanitize_untrusted_text(parser.text, 200_000)
    return ExtractedPage(
        url=url, title=parser.title, text=cleaned,
        published_at=parser.published_at(), status_code=status_code,
        provider=provider, injection_flags=flags,
        raw={"links": len(parser.links), "meta_keys": sorted(parser.meta)[:30]},
    )


class DirectExtraction:
    """Extraction HTTP directe (repli quand Firecrawl n'est pas configuré)."""
    name = "direct"
    label = "Extraction HTTP directe"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def extract(self, client: httpx.AsyncClient, url: str) -> ExtractedPage:
        try:
            validate_public_url(url, require_dns=self.settings.dns_ssrf_check)
        except UnsafeURL as exc:
            raise ProviderUnavailable(f"URL refusée : {exc.message}") from exc
        r = await client.get(url, follow_redirects=True,
                             headers={"User-Agent": "OmniResearch100/1.0",
                                      "Accept": "text/html,application/xhtml+xml"})
        if r.status_code >= 400:
            raise ProviderUnavailable(f"Extraction HTTP {r.status_code} pour {url}")
        ctype = r.headers.get("content-type", "")
        if "html" not in ctype and "text" not in ctype:
            raise ProviderUnavailable(f"Type de contenu non extractible : {ctype}")
        payload = r.content[: self.settings.max_content_bytes]
        page = parse_html(payload.decode(r.encoding or "utf-8", errors="replace"),
                          str(r.url), r.status_code, self.name)
        page.raw["content_type"] = ctype
        page.raw["bytes"] = len(payload)
        return page
