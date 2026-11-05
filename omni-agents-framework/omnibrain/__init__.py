"""OmniBrain — orchestration multi-agents parallèles.

Modules principaux :
    classifier  : classement simple / moyenne / complexe d'une demande
    router      : matrice de routage et sélection de l'escouade
    registry    : découverte et validation des agents spécialisés
    dispatcher  : briefs autonomes + contrats d'interface en une seule vague
    gates       : gates qualité (complétude, preuve fraîche, revue adverse, intégration)
    report      : rapport d'orchestration et livrable unique
"""

__version__ = "1.0.0"

from .classifier import Classifier, Classification
from .router import Router, RoutingDecision
from .registry import Registry, AgentDef
from .dispatcher import Dispatcher, OrchestrationPlan
from .gates import GateEngine, GateResult
from .config import load_matrix, find_repo_root

__all__ = [
    "__version__",
    "Classifier",
    "Classification",
    "Router",
    "RoutingDecision",
    "Registry",
    "AgentDef",
    "Dispatcher",
    "OrchestrationPlan",
    "GateEngine",
    "GateResult",
    "load_matrix",
    "find_repo_root",
]
