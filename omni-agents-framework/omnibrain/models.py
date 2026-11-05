"""Dataclasses partagées par tout le framework."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Signal:
    """Un fait expliquant le score de classification (traçabilité)."""

    label: str
    weight: int
    evidence: str


@dataclass
class Classification:
    level: str  # "simple" | "moyenne" | "complexe"
    score: int
    signals: list[Signal] = field(default_factory=list)
    squad_size: int = 1
    domains: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data


@dataclass
class AgentDef:
    id: str
    name: str
    file: str
    domains: list[str]
    keywords: list[str]
    artifacts: list[str] = field(default_factory=list)
    emoji: str = "🤖"
    orchestrator: bool = False
    risk: bool = False
    description: str = ""
    body: str = ""
    squad: str = "core"

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if k != "body"}


@dataclass
class InterfaceContract:
    artifact: str
    producers: list[str]
    consumers: list[str]
    schema_ref: str


@dataclass
class RoutingDecision:
    agents: list[AgentDef]
    scores: dict[str, int]
    reasons: list[str] = field(default_factory=list)
    contracts: list[InterfaceContract] = field(default_factory=list)
    wave: int = 0  # une seule vague parallèle, conformément au manifeste


@dataclass
class Brief:
    agent_id: str
    agent_name: str
    emoji: str
    objective: str
    context_scope: str
    inputs: list[str]
    expected_outputs: list[str]
    gate_obligations: list[str]
    token_budget: str


@dataclass
class GateResult:
    gate: str
    status: str  # "PASS" | "NEEDS WORK"
    evidence: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


@dataclass
class OrchestrationPlan:
    task: str
    classification: Classification
    decision: RoutingDecision
    briefs: list[Brief]
    gates_checklist: list[str]
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "classification": self.classification.as_dict(),
            "squad": [a.as_dict() for a in self.decision.agents],
            "scores": self.decision.scores,
            "contracts": [asdict(c) for c in self.decision.contracts],
            "wave": self.decision.wave,
            "briefs": [asdict(b) for b in self.briefs],
            "gates_checklist": self.gates_checklist,
            "warnings": self.warnings,
        }
