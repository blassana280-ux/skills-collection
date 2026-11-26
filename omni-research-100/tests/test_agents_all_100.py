"""Exécution RÉELLE des 100 handlers sur un corpus de test hors ligne."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agents.base import AgentContext, ToolFacade
from app.agents.registry import AgentRegistry
from app.core.schemas import Mode

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "test-results" / "agent_results.json"


@pytest.mark.agents
def test_all_100_agents_execute_with_distinct_structured_outputs(corpus_docs):
    registry = AgentRegistry()
    assert len(registry.specs) == 100
    statuses: dict[str, str] = {}
    fingerprints: set[str] = set()
    failures: list[str] = []
    for spec in registry.specs:
        ctx = AgentContext(
            mission_id="agents-test", query="étude 2025 versions API et contradiction",
            mode=Mode.MAXIMUM, evidence=corpus_docs,
            tools=ToolFacade(list(spec.allowed_tools)), data_origin="offline-fixture",
        )
        try:
            output = registry.handlers[spec.id](ctx)
            ok = (output.status == "ok" and output.agent_id == spec.id
                  and output.division == spec.division_code
                  and isinstance(output.findings, list) and len(output.findings) >= 1
                  and isinstance(output.metrics, dict) and bool(output.summary)
                  and all(isinstance(f.score, float) and 0 <= f.score <= 1
                          for f in output.findings)
                  and all(f.agent_id == spec.id for f in output.findings)
                  and set(output.tools_used) <= set(spec.allowed_tools))
            if ok:
                statuses[spec.id] = "OPÉRATIONNELLE ET TESTÉE"
                fingerprints.add(output.fingerprint)
            else:
                failures.append(spec.id)
                statuses[spec.id] = "PARTIELLE"
        except Exception as exc:
            failures.append(f"{spec.id}:{type(exc).__name__}")
            statuses[spec.id] = "BLOQUÉE"
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(statuses, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    assert not failures, f"agents en échec : {failures[:10]}"
    assert len(statuses) == 100
    assert len(fingerprints) == 100, f"sorties distinctes : {len(fingerprints)}/100"


@pytest.mark.agents
def test_every_agent_has_a_real_config_and_schemas():
    registry = AgentRegistry()
    for spec in registry.specs:
        assert spec.handler_name.startswith(spec.division_code.lower())
        assert callable(registry.handler(spec.id))
        assert spec.input_schema["required"] == [
            "mission_id", "query", "mode", "evidence"]
        assert "findings" in spec.output_schema["properties"]
        assert spec.config["kernel"] == spec.template
        assert 0 <= spec.config["confidence_weight"] <= 1
        assert spec.config["retry_attempts"] >= 1
        assert spec.skills and spec.focus and spec.allowed_tools


@pytest.mark.agents
def test_runner_enforces_tool_allowlist(corpus_docs, runtime):
    import asyncio
    spec = runtime.registry.get("WEB-01")
    ctx = runtime.runner.build_context(
        spec, mission_id="tool-test", query="test", mode=Mode.FAST,
        evidence=corpus_docs, data_origin="offline-fixture",
    )
    assert ctx.tools.snapshot() == []
    with pytest.raises(Exception):
        ctx.tools.use("llm")  # non autorisé pour WEB-01
    out = asyncio.run(runtime.runner.run(spec, ctx))
    assert out.status == "ok"
    assert set(out.tools_used) <= set(spec.allowed_tools)


@pytest.mark.agents
def test_runner_rejects_malformed_input(corpus_docs, runtime):
    import asyncio
    spec = runtime.registry.get("FACT-01")
    ctx = runtime.runner.build_context(
        spec, mission_id="", query="", mode=Mode.FAST, evidence=corpus_docs,
    )
    out = asyncio.run(runtime.runner.run(spec, ctx))
    assert out.status == "failed"
    assert "validation" in out.error
