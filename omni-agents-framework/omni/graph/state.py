"""État du graphe de workflow critique (spec → … → vérification)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GraphState:
    """État unique, sérialisable, passé de nœud en nœud.

    ``history`` est la trace déterministe des transitions (step, node, gate).
    ``human_approvals`` ne peut être renseigné que par un humain : son absence
    déclenche l'escalade Lassana aux points d'arrêt.
    """

    mission_id: str
    project_type: str = "generic"
    spec: str = ""
    implementation: str = ""
    review: str = ""
    test_report: str = ""
    verification: str = ""
    verdict: str = "NEEDS WORK"
    pending_human: bool = False
    human_approvals: dict[str, bool] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    escalations: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    tokens_in: int = 0
    tokens_out: int = 0
    stopped_at: str = ""

    def snapshot(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "project_type": self.project_type,
            "verdict": self.verdict,
            "pending_human": self.pending_human,
            "nodes": [h["node"] for h in self.history if h["kind"] == "node"],
            "escalations": list(self.escalations),
            "artifacts": dict(self.artifacts),
            "stopped_at": self.stopped_at,
        }
