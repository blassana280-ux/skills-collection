#!/usr/bin/env python3
"""Vérification LIVE des 5 connecteurs — sans jamais simuler de résultat.

À exécuter sur une machine disposant d'un accès réseau et, pour les services
payants ou à clé, des variables d'environnement correspondantes. Un connecteur
non configuré est signalé `not_configured` avec **0 source** ; une panne réseau
est signalée comme telle. Aucune donnée d'exemple n'est injectée.

    .venv/bin/python scripts/verify_providers_live.py "ma requête"

Rapport : test-results/providers_live.json
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.providers.base import SearchQuery  # noqa: E402
from app.providers.registry import ProviderRegistry  # noqa: E402

OUT = ROOT / "test-results" / "providers_live.json"


async def main() -> int:
    query_text = sys.argv[1] if len(sys.argv) > 1 else "open source intelligence"
    settings = Settings.from_env()
    registry = ProviderRegistry(settings, plugins=True)
    results: list[dict] = []
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds,
                                 follow_redirects=False) as client:
        for provider in registry.all():
            row: dict = {"provider": provider.name,
                         "configured": provider.is_configured(),
                         "enabled": provider.state.enabled,
                         "status_before": provider.state.status(),
                         "sources": 0, "verified_live": False}
            if not provider.is_configured() or not provider.state.enabled:
                row["status"] = row["status_before"]
                row["detail"] = "aucun appel effectué (configuration absente ou désactivé)"
                results.append(row)
                continue
            started = time.monotonic()
            try:
                sources = await provider.search(
                    client, SearchQuery(text=query_text, limit=3,
                                        language="fr", category="general"))
                row["sources"] = len(sources)
                # Un double de test ne peut JAMAIS valider un appel live.
                row["verified_live"] = bool(sources) and not bool(
                    getattr(provider, "test_double", False))
                row["status"] = "live_ok" if sources else "live_empty"
                row["sample_domains"] = sorted({s.domain for s in sources})[:3]
                row["latency_ms"] = round((time.monotonic() - started) * 1000, 1)
            except Exception as error:
                row["status"] = "error"
                row["error_type"] = type(error).__name__
                row["detail"] = str(error)[:300]
                row["latency_ms"] = round((time.monotonic() - started) * 1000, 1)
            results.append(row)
    report = {
        "query": query_text,
        "network_used": True,
        "simulated_results": False,
        "providers": results,
        "live_verified": [r["provider"] for r in results if r["verified_live"]],
        "conclusion": ("Aucun fournisseur n'a pu être vérifié en direct : "
                       "aucune clé/service joignable. Les connecteurs restent "
                       "préparés et documentés, sans résultat fictif."
                       if not any(r["verified_live"] for r in results) else
                       "Appels réels réussis pour les fournisseurs listés."),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"providers": [(r["provider"], r["status"], r["sources"])
                                    for r in results],
                      "live_verified": report["live_verified"]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
