"""Les trois modes exécutés de bout en bout avec le pipeline complet."""
from __future__ import annotations

import pytest

from app.core.db import Mission, ReportRow, Source, Task
from app.core.schemas import Mode


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.parametrize("mode,expected_agents", [
    (Mode.FAST, 3), (Mode.DEEP, 16), (Mode.MAXIMUM, 100),
])
async def test_full_pipeline_for_each_mode(runtime, offline_options, mode,
                                          expected_agents):
    mission_id, task = await runtime.pipeline.submit(
        "Quelles sont les versions de l'API, les études 2025 et les contradictions ?",
        mode, "tester", offline_options)
    result = await task
    assert result["mission_id"] == mission_id
    assert result["status"] == "completed", result
    # Double de test hors ligne : le verdict READY reste impossible.
    assert result["verdict"] == "NEEDS_WORK", result["gates"]
    assert result["sources"] == 8
    assert result["agents"] == expected_agents
    assert result["providers"] == ["fixture"]

    mission = runtime.store.get(Mission, mission_id)
    assert mission.status == "completed"
    assert mission.progress == 1.0
    assert mission.data_origin == "offline-fixture"
    assert len((mission.plan or {}).get("steps", [])) == expected_agents

    tasks = runtime.store.filter(Task, mission_id=mission_id)
    assert len(tasks) == expected_agents
    assert all(t.status == "ok" for t in tasks)
    assert runtime.store.count(Source) >= 8

    report = runtime.store.get(ReportRow, f"report-{mission_id}")
    assert report is not None
    assert report.verdict == "NEEDS_WORK"
    assert "Méthode" in report.markdown
    assert "Table des preuves" in report.markdown
    assert "[S1]" in report.markdown
    payload = report.payload or {}
    assert payload["coverage"]["agents_planned"] == expected_agents
    assert payload["coverage"]["agents_executed"] == expected_agents
    assert payload["coverage"]["peak_concurrency_measured"] <= \
        runtime.settings.max_parallel_agents
    assert payload["gates"]["real_provider"] is False
    assert payload["citations"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_maximum_uses_all_ten_divisions_in_bounded_waves(runtime, offline_options):
    mission_id, task = await runtime.pipeline.submit(
        "synthèse complète données actualité science technologie osint social "
        "vérification web recherche", Mode.MAXIMUM, "tester", offline_options)
    result = await task
    assert result["agents"] == 100
    events = runtime.store.events_after(mission_id, 0, limit=10000)
    wave_starts = [e for e in events if e["kind"] == "wave_started"]
    assert len(wave_starts) == 4
    for event in wave_starts:
        assert event["payload"]["max_parallel"] == runtime.settings.max_parallel_agents
    report = runtime.store.get(ReportRow, f"report-{mission_id}")
    assert len(report.payload["coverage"]["divisions"]) == 10


@pytest.mark.asyncio
@pytest.mark.integration
async def test_reusable_research_cache(runtime, offline_options):
    query = "Versions de l'API et étude 2025 ?"
    mid1, t1 = await runtime.pipeline.submit(query, Mode.FAST, "tester", offline_options)
    await t1
    found = await runtime.memory.find_reusable(query, "fast")
    assert found is not None and found["match"] == "exact"
    assert found["hits"] >= 1
