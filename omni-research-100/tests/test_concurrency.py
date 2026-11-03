"""Concurrence mesurée, limites réelles et aucune affirmation de simultanéité
supérieure à l'infrastructure.
"""
from __future__ import annotations

import asyncio

import pytest

from app.brain.scheduler import TaskScheduler
from app.core.schemas import Mode


@pytest.mark.asyncio
@pytest.mark.concurrency
async def test_measured_peak_never_exceeds_semaphore(runtime, corpus_docs):
    object.__setattr__(runtime.settings, "max_parallel_agents", 2)
    runtime.executor._semaphore = asyncio.Semaphore(2)
    plan = runtime.planner.plan("étude API 2025", Mode.FAST, ["fixture"], "general",
                                {"max_agents": 20})
    from app.core.schemas import PlanStep
    plan.steps = [PlanStep(agent_id=s.id, division=s.division_code,
                           objective=s.name, relevance=1.0, wave=0)
                  for s in list(runtime.registry.specs)[:20]]
    waves = TaskScheduler().build_waves(plan)
    assert len(waves) == 1 and len(waves[0].steps) == 20
    report = await runtime.executor.execute(
        "concurrency-test", waves, query="étude API 2025", plan=plan,
        mode=Mode.FAST, evidence=corpus_docs, data_origin="offline-fixture",
        is_cancelled=lambda: False)
    assert report.executed == 20, report.to_dict()
    assert report.failed == 0
    assert 1 <= report.peak_concurrency <= 2
    assert report.to_dict()["peak_concurrency_measured"] == report.peak_concurrency
    assert report.queued == 18


@pytest.mark.asyncio
@pytest.mark.concurrency
async def test_global_mission_concurrency_is_bounded(runtime):
    commander = runtime.commander
    assert runtime.settings.max_concurrent_missions == 2
    async with commander.slot("a"):
        async with commander.slot("b"):
            assert commander.active == {"a", "b"}
            async def third():
                async with commander.slot("c"):
                    return True
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(third(), timeout=0.25)
        async with commander.slot("c"):
            assert "c" in commander.active
    assert commander.active == set()
