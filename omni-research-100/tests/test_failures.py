"""Pannes, bascule, annulation et absence de faux succès."""
from __future__ import annotations

import pytest

from app.core.db import Mission, ReportRow
from app.core.schemas import Mode
from app.runtime import build_runtime
from tests.fixtures.provider_responses import FailingProvider, make_mock_client


@pytest.mark.asyncio
@pytest.mark.failure
async def test_all_providers_down_leads_to_insufficient_evidence(settings):
    rt = build_runtime(settings, extra_providers=[FailingProvider(settings)],
                       client_factory=make_mock_client, provider_plugins=False)
    try:
        mid, task = await rt.pipeline.submit(
            "question sans réseau", Mode.FAST, "tester",
            {"data_origin": "offline-fixture", "skip_extraction": True})
        result = await task
        assert result["status"] == "insufficient_evidence", result
        assert result["sources"] == 0
        assert result["verdict"] == "NEEDS_WORK"
        report = rt.store.get(ReportRow, f"report-{mid}")
        assert report is not None
        assert "aucune source réelle" in report.markdown
        assert "NEEDS_WORK" in report.markdown
        assert rt.store.get(Mission, mid).status == "insufficient_evidence"
    finally:
        rt.close()


@pytest.mark.asyncio
@pytest.mark.failure
async def test_failing_agent_is_reported_not_hidden(runtime, corpus_docs):
    spec = runtime.registry.get("WEB-01")
    broken_id = spec.id
    original = runtime.registry.handlers[broken_id]

    def broken(_ctx):
        raise RuntimeError("panne de l'agent de test")

    runtime.registry.handlers[broken_id] = broken
    ctx = runtime.runner.build_context(
        spec, mission_id="agent-failure", query="test", mode=Mode.FAST,
        evidence=corpus_docs, data_origin="offline-fixture")
    output = await runtime.runner.run(spec, ctx)
    runtime.registry.handlers[broken_id] = original
    assert output.status == "failed"
    assert "RuntimeError" in output.error
    errors = runtime.store.filter(
        __import__("app.core.db", fromlist=["ErrorLog"]).ErrorLog,
        mission_id="agent-failure")
    assert errors


@pytest.mark.asyncio
@pytest.mark.failure
async def test_cancellation_stops_the_pipeline(runtime):
    mid = runtime.commander.create("mission annulée", Mode.DEEP, "tester",
                                   {"data_origin": "offline-fixture"})
    assert runtime.commander.cancel(mid) is True
    result = await runtime.pipeline.run(mid, "mission annulée", Mode.DEEP,
                                        {"data_origin": "offline-fixture"})
    assert result["status"] == "cancelled"
    assert runtime.store.get(Mission, mid).status == "cancelled"


@pytest.mark.asyncio
@pytest.mark.failure
async def test_pipeline_exception_is_logged_and_status_failed(runtime, offline_options):
    async def boom(*_args, **_kwargs):
        raise RuntimeError("panne du routeur")
    runtime.router.search = boom
    mid, task = await runtime.pipeline.submit("question", Mode.FAST, "tester",
                                              offline_options)
    result = await task
    assert result["status"] == "failed"
    assert "RuntimeError" in result["error"]
    mission = runtime.store.get(Mission, mid)
    assert mission.status == "failed" and mission.error
