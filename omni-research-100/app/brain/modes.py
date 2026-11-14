"""Les trois modes de recherche — paramètres réels, aucune promesse de
parallélisme supérieure à l'infrastructure disponible.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.config import Settings
from ..core.schemas import Mode


@dataclass(frozen=True)
class ModeConfig:
    name: str
    agent_count: int
    provider_count: int
    max_sources: int
    extractions: int
    verification_passes: int
    contradiction_analysis: bool
    contradiction_deep: bool
    cross_provider_search: bool
    report_sections: tuple[str, ...]
    waves: tuple[tuple[str, ...], ...]
    description: str


MODE_CONFIG: dict[Mode, ModeConfig] = {
    Mode.FAST: ModeConfig(
        name="FAST", agent_count=3, provider_count=1, max_sources=8,
        extractions=0, verification_passes=1, contradiction_analysis=False,
        contradiction_deep=False, cross_provider_search=False,
        report_sections=("Réponse", "Sources", "Limites"),
        waves=(("WEB", "DEEP", "SYN", "FACT", "NEWS", "SCI", "TECH", "OSINT",
                "SOC", "DATA"),),
        description="Recherche rapide sur un fournisseur, synthèse extractive immédiate.",
    ),
    Mode.DEEP: ModeConfig(
        name="DEEP", agent_count=16, provider_count=3, max_sources=24,
        extractions=6, verification_passes=2, contradiction_analysis=True,
        contradiction_deep=False, cross_provider_search=True,
        report_sections=("Réponse", "Méthode", "Affirmations vérifiées",
                         "Contradictions", "Sources", "Limites"),
        waves=(
            ("WEB", "NEWS", "SCI", "TECH", "OSINT", "DATA", "SOC", "DEEP"),
            ("FACT",),
            ("SYN",),
        ),
        description="Recherche multi-fournisseurs, recoupement, analyse des contradictions.",
    ),
    Mode.MAXIMUM: ModeConfig(
        name="MAXIMUM", agent_count=100, provider_count=5, max_sources=60,
        extractions=12, verification_passes=3, contradiction_analysis=True,
        contradiction_deep=True, cross_provider_search=True,
        report_sections=("Résumé exécutif", "Méthode détaillée", "Plan de mission",
                         "Affirmations vérifiées", "Consensus", "Contradictions arbitrées",
                         "Table des preuves", "Couverture des agents", "Sources",
                         "Limites et reproductibilité"),
        waves=(
            ("WEB", "NEWS", "SCI", "TECH", "OSINT"),
            ("DATA", "SOC", "DEEP"),
            ("FACT",),
            ("SYN",),
        ),
        description=("Mobilisation adaptative des 100 agents pertinents, recherche "
                     "multi-fournisseurs, vérification renforcée, arbitrage des "
                     "contradictions et rapport complet."),
    ),
}


def effective_agent_count(mode: Mode, settings: Settings) -> int:
    """Nombre d'agents réellement planifiés, borné par les ressources déclarées."""
    wanted = MODE_CONFIG[mode].agent_count
    return min(wanted, settings.max_agents_per_mission, 100)


def effective_concurrency(mode: Mode, settings: Settings) -> int:
    return min(settings.max_parallel_agents, effective_agent_count(mode, settings))


def mode_summary(mode: Mode, settings: Settings) -> dict[str, object]:
    cfg = MODE_CONFIG[mode]
    planned = effective_agent_count(mode, settings)
    parallel = effective_concurrency(mode, settings)
    return {
        "mode": cfg.name, "description": cfg.description,
        "agents_planned": planned, "max_simultaneous_agents": parallel,
        "waves": len(cfg.waves), "providers_targeted": cfg.provider_count,
        "max_sources": min(cfg.max_sources, settings.max_sources_per_mission),
        "extractions": min(cfg.extractions, settings.max_extractions_per_mission),
        "verification_passes": cfg.verification_passes,
        "contradiction_analysis": cfg.contradiction_analysis,
        "contradiction_deep": cfg.contradiction_deep,
        "queued_not_simultaneous": max(0, planned - parallel),
        "report_sections": list(cfg.report_sections),
    }
