"""Schéma de données des fiches agents du catalogue (103 agents en v4).

Chaque module ``tools/catalog_*.py`` exporte ``SPECS`` : une liste
d'``AgentSpec``. Le générateur ``tools/generate_agents.py`` transforme ces
spécifications en fiches Markdown ``specialized/`` et en entrées TOML
``catalog/catalog-100.toml``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentSpec:
    id: str
    name: str
    emoji: str
    squad: str
    domains: tuple[str, ...]
    keywords: tuple[str, ...]
    artifacts: tuple[str, ...]
    description: str
    vibe: str
    mission: str
    rules: tuple[str, ...]
    inputs: str
    outputs: str
    when: str
    edge: str
    risk: bool = False
