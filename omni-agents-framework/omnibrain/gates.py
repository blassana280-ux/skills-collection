"""Moteur de gates qualité.

Valeur par défaut du réseau : « NEEDS WORK ». Un gate ne passe que sur
preuve explicite. Le moteur est déterministe et exécutable en CI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .classifier import _normalize
from .models import GateResult

PLACEHOLDERS = ("todo", "fixme", "tbd", "xxx", "à compléter", "a completer", "placeholder")
TIME_SENSITIVE = (
    "actuellement", "aujourd'hui", "dernier", "dernière", "récent", "taux",
    "version actuelle", "en vigueur", "loi de finances", "tarif", "quota",
)
DATE_PATTERN = re.compile(r"(19|20)\d{2}(-\d{2}(-\d{2})?)?|\b\d{1,2}/\d{1,2}/(19|20)\d{2}\b")
URL_PATTERN = re.compile(r"https?://[^\s)>]+")
SECTION_PATTERN = re.compile(r"^#{1,4}\s+(.+)$", re.MULTILINE)


@dataclass
class GateReport:
    results: list[GateResult]

    @property
    def passed(self) -> bool:
        return all(g.passed for g in self.results)

    @property
    def verdict(self) -> str:
        return "PASS" if self.passed else "NEEDS WORK"


class GateEngine:
    """Évalue un livrable Markdown au regard des 4 gates du manifeste."""

    def evaluate(self, deliverable: str, expected_agents: list[str] | None = None) -> GateReport:
        expected_agents = expected_agents or []
        norm = _normalize(deliverable)
        headings = [h.strip().lower() for h in SECTION_PATTERN.findall(deliverable)]
        results = [
            self._completeness(deliverable, norm, headings, expected_agents),
            self._freshness(deliverable, norm, headings),
            self._adversarial(norm, headings),
            self._integration(norm, headings),
        ]
        return GateReport(results)

    # -------------------------------------------------------------- les gates

    def _completeness(self, raw: str, norm: str, headings: list[str], agents: list[str]) -> GateResult:
        evidence: list[str] = []
        ok = True
        for marker in PLACEHOLDERS:
            if re.search(rf"\b{re.escape(marker)}\b", norm):
                ok = False
                evidence.append(f"placeholder détecté : {marker}")
        for agent_id in agents:
            if agent_id.lower() not in norm:
                ok = False
                evidence.append(f"livrable de l'agent {agent_id} absent du document")
        if ok:
            evidence.append("aucun placeholder ; tous les agents attendus sont couverts")
        return GateResult("G1 — Complétude", "PASS" if ok else "NEEDS WORK", evidence)

    def _freshness(self, raw: str, norm: str, headings: list[str]) -> GateResult:
        evidence: list[str] = []
        urls = URL_PATTERN.findall(raw)
        dates = DATE_PATTERN.findall(raw)
        sensitive = [word for word in TIME_SENSITIVE if word in norm]
        ok = True
        if sensitive and not urls:
            ok = False
            evidence.append(f"énoncés temporels ({', '.join(sensitive[:4])}) sans aucune source URL")
        if sensitive and not dates:
            ok = False
            evidence.append("énoncés temporels sans date associée")
        if urls:
            evidence.append(f"{len(urls)} source(s) URL citée(s)")
        if dates:
            evidence.append(f"{len(dates)} date(s) explicite(s)")
        if not sensitive:
            evidence.append("aucun énoncé temporel critique détecté")
        return GateResult("G2 — Preuve fraîche", "PASS" if ok else "NEEDS WORK", evidence)

    def _adversarial(self, norm: str, headings: list[str]) -> GateResult:
        has_section = any(("revue" in h and "adverse" in h) or "adversarial" in h for h in headings)
        has_verdict = "needs work" in norm or "verdict" in norm
        ok = has_section and has_verdict
        evidence = []
        if has_section:
            evidence.append("section de revue adverse présente")
        else:
            evidence.append("section « Revue adverse » introuvable")
        if has_verdict:
            evidence.append("verdict explicite (PASS / NEEDS WORK) présent")
        return GateResult("G3 — Revue adverse", "PASS" if ok else "NEEDS WORK", evidence)

    def _integration(self, norm: str, headings: list[str]) -> GateResult:
        has_synthesis = any(
            any(token in h for token in ("synthese", "integration", "livrable unique", "assemblage"))
            for h in headings
        )
        mentions_contract = "contrat" in norm or "interface" in norm
        ok = has_synthesis and mentions_contract
        evidence = []
        evidence.append(
            "section de synthèse/intégration présente" if has_synthesis
            else "section de synthèse/intégration introuvable"
        )
        evidence.append(
            "contrats d'interface mentionnés" if mentions_contract
            else "aucune mention des contrats d'interface"
        )
        return GateResult("G4 — Intégration", "PASS" if ok else "NEEDS WORK", evidence)
