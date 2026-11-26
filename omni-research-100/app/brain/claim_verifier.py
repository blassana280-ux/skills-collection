"""Claim Verifier : extraction, corroboration indépendante et vérification
renforcée (plusieurs passes) des affirmations produites par les agents.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ..agents import kernels as K
from ..core.db import ClaimRow, Store
from ..core.schemas import AgentOutput, Claim, SourceRecord
from ..core.security import sanitize_untrusted_text

_NORMALIZE = re.compile(r"[^a-z0-9à-ÿ ]+")


@dataclass
class VerificationReport:
    claims: list[Claim] = field(default_factory=list)
    grouped: int = 0
    passes: int = 1
    discarded: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


class ClaimVerifier:
    def __init__(self, store: Store) -> None:
        self.store = store

    @staticmethod
    def _key(statement: str) -> str:
        return " ".join(_NORMALIZE.sub(" ", statement.lower()).split())[:120]

    def verify(self, outputs: list[AgentOutput], docs: list[SourceRecord],
               mission_id: str, passes: int = 1) -> VerificationReport:
        domain_by_source = {d.id: d.domain for d in docs}
        verified_source = {d.id for d in docs if d.verified}
        groups: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"statement": "", "agents": set(), "sources": set(),
                     "scores": [], "negated": False, "domains": set()}
        )
        for output in outputs:
            if output.status != "ok":
                continue
            for finding in output.findings:
                if finding.metadata.get("empty"):
                    continue
                statement, _ = sanitize_untrusted_text(finding.statement, 600)
                key = self._key(statement)
                if len(key) < 12:
                    continue
                group = groups[key]
                group["statement"] = group["statement"] or statement
                group["agents"].add(output.agent_id)
                group["sources"].update(finding.evidence_ids)
                group["scores"].append(finding.score)
                domain = finding.metadata.get("domain")
                if isinstance(domain, str):
                    group["domains"].add(domain)
                if finding.metadata.get("negation") or finding.metadata.get("cue"):
                    group["negated"] = True
        for group in groups.values():
            for sid in group["sources"]:
                if sid in domain_by_source:
                    group["domains"].add(domain_by_source[sid])

        claims: list[Claim] = []
        discarded: list[str] = []
        for key, group in groups.items():
            domains = len(group["domains"])
            sources = len(group["sources"])
            agents = len(group["agents"])
            mean_score = sum(group["scores"]) / max(1, len(group["scores"]))
            confidence = min(1.0, 0.18 * domains + 0.08 * agents +
                             0.25 * mean_score + 0.05 * min(sources, 4) +
                             0.08 * len(group["sources"] & verified_source))
            if confidence < 0.12:
                discarded.append(key)
                continue
            if group["negated"] and domains >= 2:
                status = "contested"
            elif domains >= 2 and sources >= 2 and confidence >= 0.42:
                status = "verified"
            elif sources >= 1 and confidence >= 0.2:
                status = "uncertain"
            else:
                status = "unsupported"
            claims.append(Claim(
                text=group["statement"], support_ids=sorted(group["sources"]),
                contradict_ids=[], status=status,
                confidence=round(confidence, 4), independent_domains=domains,
                rationale=(f"{agents} agent(s), {sources} preuve(s), "
                           f"{domains} domaine(s), score moyen {mean_score:.2f}"),
            ))

        # Passes supplémentaires : cohérence numérique et signaux de contradiction.
        numeric_conflicts = K.numeric_conflicts(docs)
        signals = K.contradiction_signals(docs)
        for _ in range(max(0, passes - 1)):
            for claim in claims:
                if numeric_conflicts and re.search(r"\d", claim.text):
                    claim.confidence = round(max(0.0, claim.confidence - 0.08), 4)
                    if claim.status == "verified":
                        claim.status = "contested"
                if signals and claim.status == "verified" and claim.independent_domains < 3:
                    claim.status = "uncertain"
        claims.sort(key=lambda c: (-c.confidence, c.text))

        for claim in claims[:250]:
            self.store.add(ClaimRow(
                id=claim.claim_id, mission_id=mission_id, text=claim.text,
                status=claim.status, confidence=claim.confidence,
                support_ids=claim.support_ids, contradict_ids=claim.contradict_ids,
                independent_domains=claim.independent_domains,
                rationale=claim.rationale,
            ))
        return VerificationReport(
            claims=claims, grouped=len(groups), passes=passes,
            discarded=discarded[:50],
            stats={
                "groups": len(groups), "claims_kept": len(claims),
                "verified": sum(1 for c in claims if c.status == "verified"),
                "contested": sum(1 for c in claims if c.status == "contested"),
                "uncertain": sum(1 for c in claims if c.status == "uncertain"),
                "numeric_conflicts": len(numeric_conflicts),
                "contradiction_signals": len(signals),
            },
        )
