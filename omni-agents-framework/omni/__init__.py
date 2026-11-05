"""OmniBrain v4 — couche d'orchestration robuste.

Sous-paquets :
    omni.memory      mémoire persistante SQLite, auto-amélioration
    omni.telemetry   instrumentation des vagues + rapport markdown
    omni.graph       graphe d'état déterministe (type LangGraph) + gates HITL
    omni.sandbox     hook E2B avec fallback local, runtime continu + RBAC

Aucune dépendance externe : stdlib Python 3.11+ uniquement.
Aucune fusion, aucune écriture sur la branche principale : voir ``omni.sandbox.RBAC``.
"""

from __future__ import annotations

from .memory import AutoFix, MemoryStore, get_recettes, record_mission
from .telemetry import WaveTelemetry
from .graph import GraphState, StateGraph, build_pipeline, run_pipeline
from .sandbox import RBAC, Runtime, Sandbox, SandboxResult

__all__ = [
    "AutoFix",
    "GraphState",
    "MemoryStore",
    "RBAC",
    "Runtime",
    "Sandbox",
    "SandboxResult",
    "StateGraph",
    "WaveTelemetry",
    "build_pipeline",
    "get_recettes",
    "record_mission",
    "run_pipeline",
]
