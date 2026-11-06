"""Cerveau de recherche : planner, scheduler, vérification, consensus,
arbitrage, synthèse, gates et rapport.
"""
from __future__ import annotations

import asyncio

import pytest

from app.brain.claim_verifier import ClaimVerifier
from app.brain.conflict_resolver import ConflictResolver
from app.brain.consensus import ConsensusEngine
from app.brain.evidence_collector import EvidenceCollector
from app.brain.modes import MODE_CONFIG, effective_agent_count, mode_summary
from app.brain.planner import MissionPlanner
from app.brain.report_generator import ReportGenerator
from app.brain.scheduler import TaskScheduler
from app.brain.synthesizer import ResearchSynthesizer
from app.core.db import ClaimRow, ContradictionRow, ReportRow
from app.core.schemas import Mode, PlanStep


@pytest.mark.unit
def test_mode_configuration_is_honest_about_resources(runtime):
    assert effective_agent_count(Mode.FAST, runtime.settings) == 3
    assert effective_agent_count(Mode.DEEP, runtime.settings) == 16
    assert effective_agent_count(Mode.MAXIMUM, runtime.settings) == 100
    for mode in Mode:
        summary = mode_summary(mode, runtime.settings)
        assert summary["max_simultaneous_agents"] <= runtime.settings.max_parallel_agents
        assert summary["queued_not_simultaneous"] == max(
            0, summary["agents_planned"] - summary["max_simultaneous_agents"])
        assert summary["report_sections"]


@pytest.mark.unit
def test_planner_and_scheduler(runtime):
    planner = MissionPlanner(runtime.registry, runtime.settings)
    scheduler = TaskScheduler()
    for mode, expected in ((Mode.FAST, 3), (Mode.DEEP, 16), (Mode.MAXIMUM, 100)):
        plan = planner.plan("étude API 2025 contradiction dataset news", mode,
                            ["fixture"], "general")
        assert len(plan.steps) == expected
        assert len({s.agent_id for s in plan.steps}) == expected
        assert plan.max_parallel <= runtime.settings.max_parallel_agents
        waves = scheduler.build_waves(plan)
        assert 1 <= len(waves) <= len(MODE_CONFIG[mode].waves)
        assert sum(len(w.steps) for w in waves) == expected
        assert all(s.wave == w.index for w in waves for s in w.steps)
        assert all(isinstance(s.depends_on, list) for w in waves for s in w.steps)
        if mode == Mode.MAXIMUM:
            assert any(s.depends_on for w in waves for s in w.steps)


@pytest.mark.unit
def test_planner_honours_division_hint(runtime):
    planner = MissionPlanner(runtime.registry, runtime.settings)
    plan = planner.plan("question quelconque", Mode.DEEP, ["fixture"], "general",
                        {"divisions": ["FACT"]})
    assert plan.steps
    assert all(s.division == "FACT" for s in plan.steps)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_claim_verifier_consensus_conflicts_synthesis(runtime, corpus_docs):
    from app.agents.base import AgentContext, ToolFacade
    outputs = []
    for agent_id in ("WEB-01", "FACT-01", "SCI-01", "SYN-02", "DATA-01"):
        spec = runtime.registry.get(agent_id)
        ctx = AgentContext(mission_id="brain-test", query="étude 2025 API",
                           mode=Mode.DEEP, evidence=corpus_docs,
                           tools=ToolFacade(list(spec.allowed_tools)))
        outputs.append(await runtime.runner.run(spec, ctx))
    assert all(o.status == "ok" for o in outputs)

    verification = ClaimVerifier(runtime.store).verify(outputs, corpus_docs,
                                                       "brain-test", passes=3)
    assert verification.claims
    assert verification.passes == 3
    assert runtime.store.count(ClaimRow) >= len(verification.claims[:250])
    assert {"verified", "contested", "uncertain", "unsupported"} >= \
        {c.status for c in verification.claims}

    consensus = ConsensusEngine().evaluate(verification.claims, outputs, corpus_docs)
    assert 0 <= consensus.score <= 1
    assert consensus.independence["domains"] >= 1

    conflicts = ConflictResolver(runtime.store).resolve(
        verification.claims, outputs, corpus_docs, "brain-test", deep=True)
    assert conflicts.rule.startswith("evidence_count >")
    for c in conflicts.contradictions:
        assert c.resolution in {"resolved", "unresolved"}
        assert c.rationale
    assert runtime.store.count(ContradictionRow) == len(conflicts.contradictions)

    collector = EvidenceCollector(runtime.store)
    from app.providers.router import SearchOutcome
    outcome = SearchOutcome(sources=corpus_docs, providers_used=["fixture"])
    bundle = collector.collect(outcome, "brain-test")
    assert len(bundle.citations) == len(corpus_docs)
    assert all(c["untrusted"] == "yes" for c in bundle.citations)

    synthesis = await ResearchSynthesizer(runtime.model_router).synthesize(
        "étude 2025 API ?", Mode.DEEP, verification.claims,
        conflicts.contradictions, bundle.citations, bundle.citation_by_id)
    assert synthesis.answer
    assert synthesis.citation_check["valid"] is True
    assert synthesis.used_llm is False  # fournisseur extractif par défaut
    assert any("extractive" in x for x in synthesis.limitations)


@pytest.mark.unit
def test_report_generator_gates_demand_a_real_provider(runtime, corpus_docs):
    from app.brain.evidence_collector import EvidenceCollector
    from app.brain.executor import ExecutionReport
    from app.brain.claim_verifier import VerificationReport
    from app.brain.consensus import ConsensusReport
    from app.brain.conflict_resolver import ConflictReport
    from app.brain.synthesizer import SynthesisResult
    from app.providers.router import SearchOutcome
    from app.core.db import Mission, Task
    from app.core.schemas import MissionStatus, Verdict

    mid = "report-gate-test"
    runtime.commander.create("question", Mode.FAST, "tester")
    # Remplace l'identifiant pour garder un test déterministe.
    plan = MissionPlanner(runtime.registry, runtime.settings).plan(
        "question", Mode.FAST, ["fixture"], "general")
    runtime.store.add(Mission(id=mid, query="question", mode="fast",
                              status=MissionStatus.COMPLETED.value,
                              created_at=0.0, data_origin="offline-fixture"))
    for step in plan.steps:
        runtime.store.add(Task(id=f"{mid}-{step.agent_id}", mission_id=mid,
                               agent_id=step.agent_id, division=step.division,
                               wave=0, status="ok",
                               output={"agent_id": step.agent_id,
                                       "findings": [{"statement": "x",
                                                     "score": 0.5,
                                                     "evidence_ids": ["src-0"]}]}))
        runtime.store.add_event(mid, "agent_dispatched", "analyzing",
                                agent=step.agent_id)
        runtime.store.add_event(mid, "agent_result", "analyzing",
                                agent=step.agent_id)
    outcome = SearchOutcome(sources=corpus_docs, providers_used=["fixture"],
                            providers_real=[])
    bundle = EvidenceCollector(runtime.store).collect(outcome, mid)
    execution = ExecutionReport(executed=len(plan.steps), failed=0,
                                peak_concurrency=1, wall_s=0.5)
    report = ReportGenerator(runtime.store, runtime.settings).generate(
        mission_id=mid, query="question", mode=Mode.FAST, plan=plan,
        outcome=outcome, bundle=bundle, execution=execution,
        verification=VerificationReport(), consensus=ConsensusReport(),
        conflicts=ConflictReport(), synthesis=SynthesisResult(answer="Réponse"),
        provider_status=runtime.router.status(), data_origin="offline-fixture",
        mode_summary=mode_summary(Mode.FAST, runtime.settings))
    assert report.verdict == Verdict.NEEDS_WORK
    assert report.gates["real_provider"] is False
    assert "Table des preuves" in report.markdown
    assert "Gates de validation" in report.markdown
    assert runtime.store.get(ReportRow, f"report-{mid}") is not None
