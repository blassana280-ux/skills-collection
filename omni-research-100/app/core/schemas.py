"""Schémas structurés : entrées/sorties des agents, de l'API et des rapports."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def new_id(prefix: str = "id") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


class Mode(str, Enum):
    FAST = "fast"
    DEEP = "deep"
    MAXIMUM = "maximum"


class MissionStatus(str, Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    SEARCHING = "searching"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    VERIFYING = "verifying"
    SYNTHESIZING = "synthesizing"
    REPORTING = "reporting"
    COMPLETED = "completed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Verdict(str, Enum):
    # Aligné sur OmniBrain : READY exige les 6 gates et un provider réel.
    READY = "READY"
    NEEDS_WORK = "NEEDS_WORK"


# --------------------------------------------------------------------------- #
# Structures internes (dataclasses sérialisables)
# --------------------------------------------------------------------------- #
@dataclass
class SourceRecord:
    url: str
    title: str = ""
    snippet: str = ""
    provider: str = ""
    score: float = 0.0
    published_at: str | None = None
    canonical_url: str = ""
    domain: str = ""
    content_hash: str = ""
    verified: bool = False
    http_status: int | None = None
    text: str = ""
    untrusted: bool = True
    injection_flags: list[str] = field(default_factory=list)
    fetched_at: float = field(default_factory=time.time)
    raw: dict[str, Any] = field(default_factory=dict)
    source_id: str = ""

    @property
    def id(self) -> str:
        return self.source_id or self.content_hash[:16] or new_id("src")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["id"] = self.id
        d.pop("raw", None)
        d.pop("text", None)
        return d

    def evidence_text(self) -> str:
        return "\n".join(x for x in (self.title, self.snippet, self.text) if x)


@dataclass
class Finding:
    statement: str
    score: float = 0.0
    evidence_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    agent_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Claim:
    text: str
    claim_id: str = field(default_factory=lambda: new_id("claim"))
    support_ids: list[str] = field(default_factory=list)
    contradict_ids: list[str] = field(default_factory=list)
    status: Literal["verified", "contested", "uncertain", "unsupported"] = "uncertain"
    confidence: float = 0.0
    independent_domains: int = 0
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Contradiction:
    claim_id: str
    statement_a: str
    statement_b: str
    contradiction_id: str = field(default_factory=lambda: new_id("contra"))
    resolution: Literal["resolved", "unresolved"] = "unresolved"
    winner: str = ""
    rationale: str = ""
    evidence_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentOutput:
    agent_id: str
    division: str
    status: Literal["ok", "failed", "skipped"] = "ok"
    findings: list[Finding] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    duration_ms: float = 0.0
    tools_used: list[str] = field(default_factory=list)
    wave: int = 0
    error: str = ""
    executed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["findings"] = [f.to_dict() for f in self.findings]
        return d

    @property
    def fingerprint(self) -> str:
        import hashlib, json
        payload = json.dumps(
            {"m": self.metrics, "s": self.summary,
             "f": [f.statement for f in self.findings[:5]]},
            sort_keys=True, ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class PlanStep:
    agent_id: str
    division: str
    objective: str
    relevance: float
    wave: int = 0
    depends_on: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MissionPlan:
    query: str
    mode: Mode
    steps: list[PlanStep]
    providers: list[str]
    reasoning: str
    max_parallel: int
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["mode"] = self.mode.value
        d["steps"] = [s.to_dict() for s in self.steps]
        return d


@dataclass
class Report:
    mission_id: str
    markdown: str
    claims: list[Claim]
    contradictions: list[Contradiction]
    sources: list[SourceRecord]
    verdict: Verdict
    gates: dict[str, bool]
    coverage: dict[str, Any]
    limitations: list[str]
    citations: list[dict[str, str]]
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "markdown": self.markdown,
            "claims": [c.to_dict() for c in self.claims],
            "contradictions": [c.to_dict() for c in self.contradictions],
            "sources": [s.to_dict() for s in self.sources],
            "verdict": self.verdict.value,
            "gates": self.gates,
            "coverage": self.coverage,
            "limitations": self.limitations,
            "citations": self.citations,
            "generated_at": self.generated_at,
        }


# --------------------------------------------------------------------------- #
# Modèles d'API (Pydantic v2, validation stricte)
# --------------------------------------------------------------------------- #
class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginIn(StrictModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_in: int


class MissionCreate(StrictModel):
    query: str = Field(min_length=3, max_length=600)
    mode: Mode = Mode.FAST
    language: str = Field(default="fr", max_length=8)
    max_sources: int | None = Field(default=None, ge=1, le=200)
    options: dict[str, Any] = Field(default_factory=dict)

    @field_validator("query")
    @classmethod
    def _check_query(cls, v: str) -> str:
        from .security import clean_user_text
        return clean_user_text(v, 600)

    @field_validator("options")
    @classmethod
    def _check_options(cls, v: dict[str, Any]) -> dict[str, Any]:
        if len(str(v)) > 4000:
            raise ValueError("options trop volumineuses")
        return v


class SettingsPatch(StrictModel):
    max_parallel_agents: int | None = Field(default=None, ge=1, le=64)
    max_concurrent_missions: int | None = Field(default=None, ge=1, le=32)
    max_sources_per_mission: int | None = Field(default=None, ge=1, le=500)
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=10000)
    retention_days: int | None = Field(default=None, ge=1, le=3650)
    disabled_providers: list[str] | None = None
    quota_overrides: dict[str, int] | None = None


class ProviderTestIn(StrictModel):
    query: str = Field(default="open source intelligence", min_length=2, max_length=200)


class PurgeIn(StrictModel):
    older_than_days: int = Field(ge=1, le=3650)
    confirm: str = Field(min_length=1, max_length=32)


class OmnibrainSubmit(StrictModel):
    """Contrat v1 : {skill, task, context} (cf. bridges/omnibrain.py)."""
    contract_version: Literal["1.0"] = "1.0"
    skill: str = Field(default="research", max_length=64)
    request: str = Field(min_length=3, max_length=600)
    task: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    mode: Mode | None = None
    callback_url: str | None = None

    @field_validator("request")
    @classmethod
    def _clean(cls, v: str) -> str:
        from .security import clean_user_text
        return clean_user_text(v, 600)
