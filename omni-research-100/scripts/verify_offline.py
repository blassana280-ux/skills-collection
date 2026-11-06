#!/usr/bin/env python3
"""Vérification de bout en bout HORS LIGNE, reproductible.

Utilise un double de test HTTP explicitement déclaré (`test_double=True`).
Aucun résultat de recherche réel n'est simulé : le verdict attendu est donc
NEEDS_WORK, ce qui prouve que la gate `real_provider` fonctionne.
"""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import Settings  # noqa: E402
from app.core.db import ReportRow  # noqa: E402
from app.core.schemas import Mode  # noqa: E402
from app.runtime import build_runtime  # noqa: E402
from tests.fixtures.provider_responses import (FixtureProvider,  # noqa: E402
                                               make_mock_client)


async def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        settings = replace(
            Settings.from_env(),
            env="offline", database_url=f"sqlite:///{tmp}/verify.db",
            omnibrain_queue_dir=f"{tmp}/queue", searxng_enabled=False,
            dns_ssrf_check=False, llm_provider="extractive",
            max_parallel_agents=4, http_timeout_seconds=5,
            auth_secret="local-verification-secret-32-bytes-minimum",
            admin_password="verify-admin", user_password="verify-user",
            omnibrain_api_key="verify-key", redis_url="", qdrant_url="",
            tavily_api_key="", brave_api_key="", exa_api_key="",
            firecrawl_api_key="",
        )
        runtime = build_runtime(
            settings, extra_providers=[FixtureProvider(settings)],
            client_factory=make_mock_client, provider_plugins=False,
        )
        try:
            mid, task = await runtime.pipeline.submit(
                "Vérification hors ligne : versions de l'API et études 2025",
                Mode.FAST, "verify", {"data_origin": "offline-fixture",
                                      "skip_extraction": True})
            result = await task
            report = runtime.store.get(ReportRow, f"report-{mid}")
            summary = {
                "mission_id": mid, **result,
                "report_available": report is not None,
                "gates": (report.payload or {}).get("gates", {}) if report else {},
                "agents": runtime.registry.validate()["agents"],
                "providers": runtime.router.registry.names(),
                "memory": runtime.memory.describe(),
                "data_source": "offline test double (aucun résultat réel simulé)",
            }
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            assert result["status"] == "completed"
            assert result["verdict"] == "NEEDS_WORK"
            assert summary["gates"]["real_provider"] is False
            assert summary["agents"] == 100
            out = ROOT / "test-results" / "offline_verification.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                           encoding="utf-8")
            return 0
        finally:
            runtime.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
