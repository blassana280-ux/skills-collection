"""Registre : 100 profils, 10 divisions, contrat OmniBrain vérifié."""
from __future__ import annotations

import pytest

from app.agents.registry import (DANGEROUS_ACTIONS, OMNIBRAIN_DANGEROUS_ACTIONS,
                                 OMNIBRAIN_GATES, AgentRegistry)
from app.core.schemas import Mode


@pytest.mark.unit
def test_registry_structure():
    registry = AgentRegistry()
    info = registry.validate()
    assert info["agents"] == 100
    assert info["handlers"] == 100
    assert len(info["divisions"]) == 10
    assert set(info["divisions"].values()) == {10}
    assert len({s.id for s in registry.specs}) == 100
    assert len({s.template for s in registry.specs}) >= 25


@pytest.mark.unit
def test_divisions_and_names():
    registry = AgentRegistry()
    by_div = registry.by_division()
    assert set(by_div) == {"WEB", "DEEP", "NEWS", "SCI", "TECH", "OSINT",
                           "SOC", "FACT", "DATA", "SYN"}
    for code, agents in by_div.items():
        assert len(agents) == 10
        assert all(a["id"].startswith(code + "-") for a in agents)
        assert all(a["mission"] and a["skills"] and a["allowed_tools"] for a in agents)


@pytest.mark.unit
def test_relevance_selection_is_deterministic():
    registry = AgentRegistry()
    q = "Quelles sont les dernières versions de l'API GitHub et le CVE ?"
    a = registry.select(q, Mode.FAST, limit=8)
    b = registry.select(q, Mode.FAST, limit=8)
    assert [x[0].id for x in a] == [x[0].id for x in b]
    assert any(x[0].division_code == "TECH" for x in a)
    news = registry.select("actualité breaking news aujourd'hui", Mode.DEEP, limit=8)
    assert any(x[0].division_code == "NEWS" for x in news)


@pytest.mark.unit
def test_maximum_mobilises_all_100_profiles():
    registry = AgentRegistry()
    ranked = registry.select("synthèse étude données API social news osint fact web",
                             Mode.MAXIMUM, limit=100)
    assert len(ranked) == 100
    assert len({s.division_code for s, _ in ranked}) == 10


@pytest.mark.omnibrain
def test_omnibrain_export_matches_real_contract():
    registry = AgentRegistry()
    export = registry.export_for_omnibrain()
    assert export["version"] == 1
    assert len(export["agents"]) == 100
    expected = {"id", "title", "specialties", "skills", "provenance",
                "boundaries", "brief_template"}
    for agent in export["agents"]:
        assert set(agent) == expected
        assert agent["id"].startswith("or100-")
        assert agent["specialties"] and agent["skills"]
        assert any("deny merge_pr" in b for b in agent["boundaries"])
        assert "no simulated search results" in agent["boundaries"]
    assert set(OMNIBRAIN_GATES) == {"completeness", "evidence", "execution",
                                    "arbitration", "secrets", "trace"}
    alignment = registry.dangerous_action_alignment()
    assert alignment["aligned"] is True
    assert set(OMNIBRAIN_DANGEROUS_ACTIONS) <= set(DANGEROUS_ACTIONS)
    assert "purge_evidence" in DANGEROUS_ACTIONS
