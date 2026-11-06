"""Les 100 agents doivent rester structurés même sans aucune source.

Reproduction du défaut observé dans le preview sans clé de fournisseur :
`length_stats([])` omettait `total_words`, ce qui faisait lever KeyError à
DEEP-03 et dégradait la mission au lieu de produire une sortie honnête.
"""
from __future__ import annotations

import pytest

from app.agents import kernels
from app.agents.base import AgentContext, ToolFacade
from app.agents.registry import AgentRegistry
from app.core.schemas import Mode


@pytest.mark.agents
def test_length_stats_empty_evidence_has_the_full_schema():
    stats = kernels.length_stats([])
    assert stats == {"documents": 0, "mean_words": 0.0, "max_words": 0,
                     "min_words": 0, "total_words": 0}


@pytest.mark.agents
def test_all_100_handlers_return_a_structured_output_with_zero_sources():
    registry = AgentRegistry()
    failures: list[str] = []
    for spec in registry.specs:
        ctx = AgentContext(
            mission_id="empty-evidence-test", query="aucune source disponible",
            mode=Mode.MAXIMUM, evidence=[],
            tools=ToolFacade(list(spec.allowed_tools)),
            data_origin="offline-fixture",
        )
        try:
            output = registry.handlers[spec.id](ctx)
            assert output.status == "ok"
            assert output.agent_id == spec.id
            assert isinstance(output.findings, list) and output.findings
            assert isinstance(output.metrics, dict)
            assert isinstance(output.summary, str) and output.summary.strip()
        except Exception as exc:  # un agent ne doit jamais lever en mission
            failures.append(f"{spec.id}:{type(exc).__name__}:{exc}")
    assert not failures, f"agents en échec sans preuve : {failures[:10]}"
