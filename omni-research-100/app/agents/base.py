"""Contrat d'exécution d'un agent : entrée structurée, outils autorisés,
sortie structurée, horodatage et preuves référencées.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from ..core.errors import AuthorizationError
from ..core.schemas import (AgentOutput, Finding, MissionPlan, Mode, SourceRecord,
                            Claim)
from ..core.security import check_url_syntax

TOOL_CATALOG: dict[str, str] = {
    "stats": "Noyaux d'analyse déterministes sur les preuves",
    "memory": "Lecture de la mémoire de recherche (cache, historique)",
    "verify": "Vérification syntaxique/SSRF des sources",
    "search": "Recherche Internet via le routeur de fournisseurs",
    "extract": "Extraction de pages via le routeur",
    "llm": "Fournisseur de modèles configuré (données web non fiables)",
    "graph": "Graphe de citations et co-occurrences",
}


class ToolFacade:
    """Seule voie d'accès aux outils : applique la liste blanche du profil."""

    def __init__(self, allowed: list[str], *, mission_id: str = "",
                 store: Any = None, memory: Any = None) -> None:
        self.allowed = list(allowed)
        self.mission_id = mission_id
        self.store = store
        self.memory = memory
        self.used: list[str] = []

    def use(self, name: str) -> None:
        if name not in TOOL_CATALOG:
            raise AuthorizationError(f"Outil inconnu : {name}")
        if name not in self.allowed:
            raise AuthorizationError(f"Outil non autorisé pour ce profil : {name}")
        if name not in self.used:
            self.used.append(name)

    def memory_lookup(self, query: str) -> dict[str, Any]:
        self.use("memory")
        if self.store is None:
            return {"reusable": False, "reason": "mémoire indisponible"}
        from ..core.db import Mission
        rows = self.store.filter(Mission, limit=50)
        similar = [r for r in rows if query.lower()[:20] in (r.query or "").lower()]
        return {"reusable": bool(similar), "past_missions": [r.id for r in similar[:5]]}

    def verify_url(self, url: str) -> bool:
        self.use("verify")
        try:
            check_url_syntax(url)
            return True
        except Exception:
            return False

    def snapshot(self) -> list[str]:
        return list(self.used)


@dataclass
class AgentContext:
    mission_id: str
    query: str
    mode: Mode
    evidence: list[SourceRecord] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    plan: MissionPlan | None = None
    config: dict[str, Any] = field(default_factory=dict)
    tools: ToolFacade = field(default_factory=lambda: ToolFacade(["stats"]))
    data_origin: str = "live"
    wave: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentSpec:
    id: str
    division_code: str
    division_name: str
    name: str
    mission: str
    skills: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    config: dict[str, Any]
    template: str
    focus: tuple[str, ...]
    pattern: str
    threshold: float
    weight: float
    label: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    handler_name: str
    priority: int = 5

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "division_code": self.division_code,
            "division_name": self.division_name, "name": self.name,
            "mission": self.mission, "skills": list(self.skills),
            "allowed_tools": list(self.allowed_tools), "config": self.config,
            "template": self.template, "focus": list(self.focus),
            "pattern": self.pattern, "threshold": self.threshold,
            "weight": self.weight, "label": self.label,
            "input_schema": self.input_schema, "output_schema": self.output_schema,
            "handler": self.handler_name, "priority": self.priority,
        }


@dataclass(frozen=True)
class AgentHandler:
    spec_id: str
    fn: Callable[[AgentContext], AgentOutput]


INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["mission_id", "query", "mode", "evidence"],
    "properties": {
        "mission_id": {"type": "string"},
        "query": {"type": "string", "maxLength": 600},
        "mode": {"enum": ["fast", "deep", "maximum"]},
        "evidence": {"type": "array", "items": {"$ref": "#/definitions/SourceRecord"}},
        "claims": {"type": "array"},
        "config": {"type": "object"},
    },
    "definitions": {
        "SourceRecord": {
            "type": "object",
            "required": ["url", "title", "snippet", "provider", "domain"],
            "properties": {
                "url": {"type": "string", "format": "uri"},
                "title": {"type": "string"}, "snippet": {"type": "string"},
                "provider": {"type": "string"}, "domain": {"type": "string"},
                "content_hash": {"type": "string"}, "verified": {"type": "boolean"},
                "published_at": {"type": ["string", "null"]},
            },
        }
    },
}

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["agent_id", "division", "status", "findings", "metrics", "summary"],
    "properties": {
        "agent_id": {"type": "string"}, "division": {"type": "string"},
        "status": {"enum": ["ok", "failed", "skipped"]},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["statement", "score", "evidence_ids"],
                "properties": {
                    "statement": {"type": "string"},
                    "score": {"type": "number", "minimum": 0, "maximum": 1},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                    "metadata": {"type": "object"},
                },
            },
        },
        "metrics": {"type": "object"}, "summary": {"type": "string"},
        "duration_ms": {"type": "number"}, "tools_used": {"type": "array"},
    },
}


def build_output(ctx: AgentContext, spec: AgentSpec, findings: list[Finding],
                 metrics: dict[str, Any], summary: str) -> AgentOutput:
    """Valide la sortie et ajoute les métadonnées d'exécution."""
    clean_findings = []
    for f in findings[:30]:
        score = max(0.0, min(1.0, float(f.score)))
        clean_findings.append(Finding(
            statement=str(f.statement)[:600], score=score,
            evidence_ids=list(f.evidence_ids)[:10],
            metadata={k: v for k, v in f.metadata.items() if isinstance(k, str)},
            agent_id=spec.id,
        ))
    metrics = dict(metrics)
    metrics["agent_id"] = spec.id
    metrics["division"] = spec.division_code
    metrics["focus"] = list(spec.focus)
    metrics["threshold"] = spec.threshold
    metrics["weight"] = spec.weight
    metrics["evidence_documents"] = len(ctx.evidence)
    metrics["data_origin"] = ctx.data_origin
    return AgentOutput(
        agent_id=spec.id, division=spec.division_code, status="ok",
        findings=clean_findings, metrics=metrics, summary=summary[:800],
        tools_used=ctx.tools.snapshot(), wave=ctx.wave,
        executed_at=time.time(),
    )
