"""Routage : parallélisme, bascule, quotas, déduplication, zéro fabrication."""
from __future__ import annotations

import pytest

from app.providers.base import SearchQuery
from tests.fixtures.provider_responses import FailingProvider


@pytest.mark.asyncio
@pytest.mark.providers
async def test_parallel_search_with_fixture(runtime):
    outcome = await runtime.router.search(
        "étude 2025 API", mission_id="m-parallel", limit=8,
        provider_names=["fixture"], max_providers=1)
    assert len(outcome.sources) == 8
    assert outcome.providers_used == ["fixture"]
    assert outcome.providers_real == []  # double de test : jamais « réel »
    assert outcome.has_real_sources
    assert outcome.category in {"science", "technology", "deep", "general"}
    assert "fixture" in outcome.quota
    assert runtime.store.count(__import__("app.core.db", fromlist=["Source"]).Source) >= 8


@pytest.mark.asyncio
@pytest.mark.failure
async def test_automatic_failover(runtime, settings):
    runtime.router.registry.register(FailingProvider(settings))
    outcome = await runtime.router.search(
        "test de bascule", mission_id="m-failover", limit=8,
        provider_names=["failing_fixture", "fixture"], max_providers=2)
    assert outcome.sources, "la bascule doit récupérer le fournisseur sain"
    assert "fixture" in outcome.providers_used
    assert any(e["provider"] == "failing_fixture" for e in outcome.errors)
    assert runtime.router.registry.get("failing_fixture").state.consecutive_failures >= 1


@pytest.mark.asyncio
@pytest.mark.failure
async def test_all_providers_down_produces_no_fake_sources(runtime, settings):
    runtime.router.registry.register(FailingProvider(settings))
    outcome = await runtime.router.search(
        "panne totale", mission_id="m-down", limit=8,
        provider_names=["failing_fixture"], max_providers=1)
    assert outcome.sources == []
    assert not outcome.has_real_sources
    assert outcome.errors
    assert outcome.providers_real == []


@pytest.mark.asyncio
@pytest.mark.providers
async def test_quota_exhaustion_is_explicit(runtime):
    runtime.router.quota.overrides = {"fixture": 1}
    runtime.store.record_usage("fixture", "search", "ok", 1.0, 2, "previous")
    outcome = await runtime.router.search(
        "quota", mission_id="m-quota", limit=8,
        provider_names=["fixture"], max_providers=1)
    assert outcome.sources == []
    assert any("quota" in e["error"].lower() for e in outcome.errors)


@pytest.mark.unit
def test_deduplication_and_category_routing(runtime):
    from tests.fixtures.provider_responses import FixtureProvider
    docs = FixtureProvider(runtime.settings)
    import asyncio
    from tests.fixtures.provider_responses import make_mock_client
    async def _get():
        async with make_mock_client() as client:
            return await docs.search(client, SearchQuery(text="x", limit=8))
    sources = asyncio.run(_get())
    deduped, removed = runtime.router.dedupe(sources + sources)
    assert len(deduped) == len(sources)
    assert removed == len(sources)
    assert runtime.router.category_for("actualité breaking news") == "news"
    assert runtime.router.category_for("arxiv doi peer review") == "science"
    assert runtime.router.category_for("vue d'ensemble") == "general"


@pytest.mark.asyncio
@pytest.mark.providers
async def test_source_http_verification_and_evidence_preservation(runtime):
    outcome = await runtime.router.search(
        "vérification", mission_id="m-verify", limit=8,
        provider_names=["fixture"], max_providers=1)
    checked = await runtime.router.verify_sources(outcome.sources, "m-verify",
                                                  max_checks=3)
    assert checked == 3
    assert all(s.verified for s in outcome.sources[:3])
    from app.core.db import Evidence
    assert runtime.store.count(Evidence) >= 8
