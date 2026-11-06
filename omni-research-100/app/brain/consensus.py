"""Consensus Engine : accord pondéré par l'indépendance des sources, la
diversité des fournisseurs et la confiance des agents.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core.schemas import AgentOutput, Claim, SourceRecord


@dataclass
class ConsensusReport:
    score: float = 0.0
    per_claim: list[dict[str, Any]] = field(default_factory=list)
    disagreements: list[dict[str, Any]] = field(default_factory=list)
    independence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"score": self.score, "per_claim": self.per_claim[:25],
                "disagreements": self.disagreements[:25],
                "independence": self.independence}


class ConsensusEngine:
    def evaluate(self, claims: list[Claim], outputs: list[AgentOutput],
                 docs: list[SourceRecord]) -> ConsensusReport:
        ok_outputs = [o for o in outputs if o.status == "ok"]
        agents_by_source: dict[str, set[str]] = {}
        for output in ok_outputs:
            for finding in output.findings:
                for sid in finding.evidence_ids:
                    agents_by_source.setdefault(sid, set()).add(output.agent_id)
        domains = {d.domain for d in docs}
        providers = {d.provider for d in docs}
        independence = {
            "domains": len(domains), "providers": len(providers),
            "verified_sources": sum(1 for d in docs if d.verified),
            "agents_ok": len(ok_outputs),
        }
        diversity = min(1.0, 0.25 * len(domains) / max(1, len(docs)) +
                        0.25 * len(providers) / max(1, len(docs)) +
                        0.25 * min(1.0, len(ok_outputs) / 10) +
                        0.25 * (1.0 if docs else 0.0))
        per_claim: list[dict[str, Any]] = []
        values: list[float] = []
        for claim in claims:
            supporting_agents = set()
            for sid in claim.support_ids:
                supporting_agents.update(agents_by_source.get(sid, set()))
            agreement = min(1.0, len(supporting_agents) / max(1, len(ok_outputs)) * 3)
            value = round(min(1.0, 0.5 * claim.confidence + 0.3 * agreement +
                              0.2 * diversity), 4)
            values.append(value)
            per_claim.append({
                "claim_id": claim.claim_id, "text": claim.text[:180],
                "status": claim.status, "confidence": claim.confidence,
                "supporting_agents": sorted(supporting_agents)[:10],
                "independent_domains": claim.independent_domains,
                "consensus": value,
            })
            if claim.status in {"contested", "unsupported"} and value > 0.2:
                pass  # les désaccords sont traités par le ConflictResolver
        disagreements = [c for c in per_claim if c["status"] in {"contested", "unsupported"}]
        score = round(sum(values) / max(1, len(values)), 4)
        return ConsensusReport(score=score, per_claim=per_claim,
                               disagreements=disagreements,
                               independence=independence)
