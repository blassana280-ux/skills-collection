"""Conflict Resolver — règle d'arbitrage alignée sur OmniBrain :

    nombre de preuves > exécution réelle > critères satisfaits > id de tâche

Égalité parfaite ⇒ `unresolved` (aucun choix arbitraire), ce qui fait échouer
la gate `arbitration` et maintient le verdict `NEEDS_WORK`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..agents import kernels as K
from ..core.db import ContradictionRow, Store
from ..core.schemas import AgentOutput, Claim, Contradiction, SourceRecord


@dataclass
class ConflictReport:
    contradictions: list[Contradiction] = field(default_factory=list)
    resolved: int = 0
    unresolved: int = 0
    signals: int = 0
    rule: str = "evidence_count > real_execution > criteria_satisfied > task_id"

    def to_dict(self) -> dict[str, Any]:
        return {
            "contradictions": [c.to_dict() for c in self.contradictions],
            "resolved": self.resolved, "unresolved": self.unresolved,
            "signals": self.signals, "rule": self.rule,
        }


class ConflictResolver:
    def __init__(self, store: Store) -> None:
        self.store = store

    @staticmethod
    def _score(evidence: int, executed: bool, criteria: int, task_id: str) -> tuple:
        return (evidence, 1 if executed else 0, criteria, task_id)

    def resolve(self, claims: list[Claim], outputs: list[AgentOutput],
                docs: list[SourceRecord], mission_id: str,
                deep: bool = False) -> ConflictReport:
        report = ConflictReport()
        signals = K.contradiction_signals(docs) if deep else K.contradiction_signals(docs)[:6]
        report.signals = len(signals)
        executed_ids = {eid for o in outputs if o.status == "ok"
                        for f in o.findings for eid in f.evidence_ids}
        claims_by_domain: dict[str, Claim] = {}
        for claim in claims:
            for sid in claim.support_ids:
                doc = next((d for d in docs if d.id == sid), None)
                if doc:
                    claims_by_domain.setdefault(doc.domain, claim)

        for index, signal in enumerate(signals[:20]):
            claim_a = claims_by_domain.get(signal["domain_a"])
            claim_b = claims_by_domain.get(signal["domain_b"])
            statement_a = claim_a.text[:300] if claim_a else signal["positive"][:300]
            statement_b = claim_b.text[:300] if claim_b else signal["negative"][:300]
            evidence_a = len(claim_a.support_ids) if claim_a else len(signal["evidence_ids"])
            evidence_b = len(claim_b.support_ids) if claim_b else len(signal["evidence_ids"])
            executed_a = bool(claim_a and any(sid in executed_ids
                                              for sid in claim_a.support_ids))
            executed_b = bool(claim_b and any(sid in executed_ids
                                              for sid in claim_b.support_ids))
            criteria_a = len(claim_a.rationale) if claim_a else 0
            criteria_b = len(claim_b.rationale) if claim_b else 0
            id_a = claim_a.claim_id if claim_a else f"A{index}"
            id_b = claim_b.claim_id if claim_b else f"B{index}"
            score_a = self._score(evidence_a, executed_a, criteria_a, id_a)
            score_b = self._score(evidence_b, executed_b, criteria_b, id_b)
            if score_a > score_b:
                resolution, winner = "resolved", "A"
                rationale = (f"Arbitrage OmniBrain : A ({evidence_a} preuves) > "
                             f"B ({evidence_b} preuves)")
            elif score_b > score_a:
                resolution, winner = "resolved", "B"
                rationale = (f"Arbitrage OmniBrain : B ({evidence_b} preuves) > "
                             f"A ({evidence_a} preuves)")
            else:
                resolution, winner = "unresolved", ""
                rationale = "Égalité parfaite : aucun arbitre arbitraire, contradiction conservée"
            contradiction = Contradiction(
                claim_id=(claim_a or claim_b).claim_id if (claim_a or claim_b) else "",
                statement_a=statement_a, statement_b=statement_b,
                resolution=resolution, winner=winner, rationale=rationale,
                evidence_ids=list(signal["evidence_ids"]),
            )
            report.contradictions.append(contradiction)
            self.store.add(ContradictionRow(
                id=contradiction.contradiction_id, mission_id=mission_id,
                claim_id=contradiction.claim_id,
                statement_a=statement_a, statement_b=statement_b,
                resolution=resolution, winner=winner, rationale=rationale,
                evidence_ids=contradiction.evidence_ids,
            ))
        report.resolved = sum(1 for c in report.contradictions if c.resolution == "resolved")
        report.unresolved = len(report.contradictions) - report.resolved
        return report
