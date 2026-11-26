"""Agent Registry : validation, sélection par pertinence, export OmniBrain v1."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable

from ..core.errors import ValidationError
from ..core.schemas import Mode
from .base import AgentSpec, TOOL_CATALOG
from .catalog_data import SPECS
from .profiles import HANDLERS

# Actions irréversibles refusées sans validation humaine explicite.
# Aligné sur registry/permissions.json d'OmniBrain + superset CF100.
DANGEROUS_ACTIONS: tuple[str, ...] = (
    "merge_pr", "force_push", "delete_repo", "delete_branch", "rotate_secret",
    "write_main", "delete_data", "change_permissions", "disable_protection",
    "purge_evidence", "deploy_production",
)
OMNIBRAIN_DANGEROUS_ACTIONS: tuple[str, ...] = (
    "merge_pr", "force_push", "delete_repo", "delete_branch", "rotate_secret",
    "write_main",
)
OMNIBRAIN_GATES: tuple[str, ...] = (
    "completeness", "evidence", "execution", "arbitration", "secrets", "trace",
)

_STOPWORDS = {"le", "la", "les", "de", "des", "du", "et", "en", "un", "une",
              "que", "dans", "pour", "est", "sur", "par", "au", "aux", "avec",
              "the", "and", "of", "to", "in", "a", "is", "are", "for", "on",
              "what", "how", "why", "comment", "pourquoi", "quel", "quelle"}

_DIVISION_HINTS: dict[str, tuple[str, ...]] = {
    "WEB": ("web", "site", "page", "crawl", "domaine", "domain"),
    "DEEP": ("analyse", "approfondi", "pourquoi", "impact", "revue", "compare", "deep"),
    "NEWS": ("actualité", "news", "récent", "aujourd'hui", "événement", "breaking"),
    "SCI": ("étude", "science", "paper", "clinical", "doi", "pubmed", "arxiv"),
    "TECH": ("api", "version", "release", "github", "code", "framework", "benchmark"),
    "OSINT": ("osint", "repository", "commit", "maintainer", "package", "whois"),
    "SOC": ("social", "tweet", "post", "hashtag", "sentiment", "reddit", "forum"),
    "FACT": ("vrai", "faux", "verify", "vérifier", "fact", "claim", "rumeur", "démenti"),
    "DATA": ("dataset", "csv", "statistics", "données", "data", "corrélation", "timeseries"),
    "SYN": ("synthèse", "rapport", "résumé", "consensus", "citation", "synthesis"),
}


def tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zà-ÿ0-9]{3,}", (text or "").lower())
            if t not in _STOPWORDS}


class AgentRegistry:
    def __init__(self, specs: Iterable[AgentSpec] | None = None,
                 handlers: dict[str, Any] | None = None,
                 validate: bool = True) -> None:
        self.specs: tuple[AgentSpec, ...] = tuple(specs or SPECS)
        self.handlers: dict[str, Any] = dict(handlers or HANDLERS)
        self._by_id = {s.id: s for s in self.specs}
        if validate:
            self.validate()

    def validate(self) -> dict[str, Any]:
        errors: list[str] = []
        if len(self.specs) != 100:
            errors.append(f"100 profils attendus, {len(self.specs)} trouvés")
        if len(self._by_id) != len(self.specs):
            errors.append("identifiants d'agents dupliqués")
        divisions = Counter(s.division_code for s in self.specs)
        if len(divisions) != 10 or set(divisions.values()) != {10}:
            errors.append(f"10 divisions de 10 agents attendues : {dict(divisions)}")
        for spec in self.specs:
            if spec.id not in self.handlers:
                errors.append(f"handler manquant : {spec.id}/{spec.handler_name}")
            unknown = set(spec.allowed_tools) - set(TOOL_CATALOG)
            if unknown:
                errors.append(f"outils inconnus {unknown} pour {spec.id}")
            if not spec.skills or not spec.mission or not spec.focus:
                errors.append(f"profil incomplet : {spec.id}")
            if not spec.input_schema.get("required") or not spec.output_schema.get("required"):
                errors.append(f"schémas manquants : {spec.id}")
            if not (0 <= spec.threshold <= 1 and 0 <= spec.weight <= 1):
                errors.append(f"paramètres hors bornes : {spec.id}")
        if errors:
            raise ValidationError("Registre d'agents invalide", errors=errors[:20])
        return {"agents": len(self.specs), "divisions": dict(divisions),
                "handlers": len(self.handlers),
                "tools": sorted({t for s in self.specs for t in s.allowed_tools})}

    def get(self, agent_id: str) -> AgentSpec:
        try:
            return self._by_id[agent_id]
        except KeyError as exc:
            raise ValidationError(f"Agent inconnu : {agent_id}") from exc

    def handler(self, agent_id: str) -> Any:
        return self.handlers[self.get(agent_id).id]

    def relevance(self, spec: AgentSpec, query: str) -> float:
        tokens = tokenize(query)
        if not tokens:
            return 0.0
        haystack = " ".join([
            spec.name.lower(), spec.mission.lower(), spec.division_name.lower(),
            " ".join(spec.skills).lower(), " ".join(spec.focus).lower(),
        ])
        words = set(re.findall(r"[a-zà-ÿ0-9]{3,}", haystack))
        overlap = tokens & words
        score = 1.2 * len(overlap) + 0.3 * sum(
            1 for token in tokens if token in haystack
        )
        hints = _DIVISION_HINTS.get(spec.division_code, ())
        score += 0.8 * sum(1 for hint in hints if hint in query.lower())
        score += (10 - spec.priority) * 0.01
        return round(score, 4)

    def select(self, query: str, mode: Mode, limit: int | None = None,
               divisions: list[str] | None = None) -> list[tuple[AgentSpec, float]]:
        pool = [s for s in self.specs
                if not divisions or s.division_code in divisions]
        ranked = sorted(((s, self.relevance(s, query)) for s in pool),
                        key=lambda pair: (-pair[1], pair[0].id))
        if limit is not None:
            ranked = ranked[: max(1, limit)]
        return ranked

    def by_division(self) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {}
        for spec in self.specs:
            out.setdefault(spec.division_code, []).append(spec.to_dict())
        return out

    def describe(self) -> dict[str, Any]:
        return {
            "total": len(self.specs),
            "divisions": {code: {"name": next(
                s.division_name for s in self.specs if s.division_code == code),
                "count": sum(1 for s in self.specs if s.division_code == code)}
                for code in sorted({s.division_code for s in self.specs})},
            "templates": sorted({s.template for s in self.specs}),
            "tool_catalog": TOOL_CATALOG,
            "agents": [s.to_dict() for s in self.specs],
        }

    # -- contrat OmniBrain (registry/agents.json) ---------------------------
    def export_for_omnibrain(self) -> dict[str, Any]:
        """Export au format vérifié `id, title, specialties, skills, provenance,
        boundaries, brief_template` (cf. cf100/bridges/omnibrain.py)."""
        agents = []
        for spec in self.specs:
            boundaries = ["defensive only", "no code execution from web sources",
                          "no simulated search results", "untrusted web data only"]
            boundaries += [f"deny {action}" for action in DANGEROUS_ACTIONS]
            agents.append({
                "id": f"or100-{spec.id.lower()}",
                "title": f"{spec.name} ({spec.division_name})",
                "specialties": list(spec.skills),
                "skills": [f"or100-{skill}" for skill in spec.skills],
                "provenance": (f"omni-research-100 division {spec.division_code} "
                               f"kernel={spec.template} handler={spec.handler_name}"),
                "boundaries": boundaries,
                "brief_template": (
                    f"Exécuter la mission : {spec.mission}. "
                    f"Outils autorisés : {', '.join(spec.allowed_tools)}. "
                    f"Entrée : INPUT_SCHEMA ; sortie : OUTPUT_SCHEMA."),
            })
        return {
            "version": 1,
            "description": "OMNI-RESEARCH 100 — export compatible OmniBrain registry/agents.json",
            "source_of_truth": "blassana280-ux/omni-agents-framework:OMNIBRAIN.md",
            "agents": agents,
            "dangerous_actions": list(DANGEROUS_ACTIONS),
            "gates": list(OMNIBRAIN_GATES),
        }

    def dangerous_action_alignment(self) -> dict[str, Any]:
        ours, omni = set(DANGEROUS_ACTIONS), set(OMNIBRAIN_DANGEROUS_ACTIONS)
        return {"common": sorted(ours & omni), "or100_only": sorted(ours - omni),
                "omni_only": sorted(omni - ours), "aligned": omni <= ours}
