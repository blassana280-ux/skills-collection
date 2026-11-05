"""Classement déterministe et explicable d'une demande.

Trois niveaux, alignés sur le manifeste OmniBrain :
    simple   -> agent unique
    moyenne  -> 1 à 3 agents
    complexe -> escouade de 4 à 8 agents, en une seule vague parallèle
"""

from __future__ import annotations

import re
import unicodedata

from .models import Classification, Signal


def _normalize(text: str) -> str:
    """Minuscule + retrait des accents pour matcher le français comme l'anglais."""
    folded = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in folded if not unicodedata.combining(ch))


def keyword_present(keyword: str, norm_text: str) -> bool:
    """Détection sûre d'un mot-clé dans un texte normalisé.

    - expression multi-mots (``design system``) : recherche de sous-chaîne ;
    - token court ou acronyme (``ci``, ``orm``, ``api``, ``tva``) : frontières
      de mot obligatoires, pour éviter que ``formulaire`` déclenche ``orm``
      ou ``associés`` déclenche ``ci``.
    """
    needle = _normalize(keyword)
    if " " in needle:
        return needle in norm_text
    return re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", norm_text) is not None


class Classifier:
    def __init__(self, matrix: dict):
        cfg = matrix["classification"]
        self.simple_threshold = int(cfg["simple_threshold"])
        self.medium_threshold = int(cfg["medium_threshold"])
        self.complex_threshold = int(cfg["complex_threshold"])
        self.min_squad = int(cfg["min_squad"])
        self.max_squad = int(cfg["max_squad"])
        self.risk_domains = list(cfg.get("risk_domains", []))
        self.connectors = list(cfg.get("connectors", []))
        self.complexity_lexemes = list(cfg.get("complexity_lexemes", []))
        self._agents = [a for a in matrix["agents"] if not a.get("orchestrator", False)]

    # ------------------------------------------------------------- scoring --

    def _domain_hits(self, norm: str) -> dict[str, set[str]]:
        """Domaine -> mots-clés effectivement rencontrés dans la demande."""
        hits: dict[str, set[str]] = {}
        for agent in self._agents:
            matched = {kw for kw in agent.get("keywords", []) if keyword_present(kw, norm)}
            if matched:
                for domain in agent.get("domains", []):
                    hits.setdefault(domain, set()).update(matched)
        return hits

    def _matched_agent_count(self, norm: str) -> int:
        """Nombre d'agents distincts réellement activés (un agent = une compétence)."""
        count = 0
        for agent in self._agents:
            if any(keyword_present(kw, norm) for kw in agent.get("keywords", [])):
                count += 1
        return count

    def classify(self, task: str) -> Classification:
        norm = _normalize(task)
        signals: list[Signal] = []
        score = 0

        # 1. Couverture par domaine (poids fort : c'est le cœur du routage).
        domain_hits = self._domain_hits(norm)
        for domain, matched in sorted(domain_hits.items()):
            weight = 2
            score += weight
            signals.append(
                Signal(label=f"domaine:{domain}", weight=weight,
                       evidence=", ".join(sorted(matched)[:5]))
            )

        # 2. Connecteurs multi-partites.
        connector_hits = 0
        for connector in self.connectors:
            count = norm.count(_normalize(connector))
            if count:
                connector_hits += count
        connector_hits = min(connector_hits, 3)
        if connector_hits:
            score += connector_hits
            signals.append(Signal("connecteurs", connector_hits,
                                  f"{connector_hits} marqueur(s) de tâches multiples"))

        # 3. Lexèmes explicites de complexité.
        lex_hits = [lex for lex in self.complexity_lexemes if _normalize(lex) in norm]
        lex_weight = min(2 * len(lex_hits), 4)
        if lex_weight:
            score += lex_weight
            signals.append(Signal("lexique-complexe", lex_weight, ", ".join(lex_hits[:4])))

        # 4. Taille de la demande (proxy de richesse du périmètre).
        length = len(task.strip())
        if length > 1200:
            score += 2
            signals.append(Signal("longueur", 2, f"{length} caractères"))
        elif length > 600:
            score += 1
            signals.append(Signal("longueur", 1, f"{length} caractères"))

        # 5. Domaines à risque (sécurité, finance OHADA, devops).
        risk_present = sorted(d for d in domain_hits if d in self.risk_domains)
        if risk_present:
            score += 2
            signals.append(Signal("domaine-a-risque", 2, ", ".join(risk_present)))

        # ------------------------------------------------------- décideurs --
        # On compte les agents/compétences distincts, pas l'union des domaines :
        # un seul agent peut porter plusieurs domaines (ex. ui + frontend).
        agent_count = self._matched_agent_count(norm)
        if score >= self.complex_threshold or agent_count >= 3:
            level = "complexe"
        elif score >= self.medium_threshold or agent_count >= 2:
            level = "moyenne"
        else:
            level = "simple"

        if level == "simple":
            squad_size = 1
        elif level == "moyenne":
            # Un agent par compétence détectée, plafonné à 3.
            squad_size = max(1, min(3, agent_count or 2))
        else:
            sized = self.min_squad + max(0, agent_count - 2) + (1 if risk_present else 0)
            squad_size = max(self.min_squad, min(self.max_squad, sized))

        return Classification(
            level=level,
            score=score,
            signals=signals,
            squad_size=squad_size,
            domains=sorted(domain_hits),
        )

    @staticmethod
    def sentence_count(text: str) -> int:
        return len([s for s in re.split(r"[.!?…]\s+", text.strip()) if s.strip()])
