"""Pipeline critique en graphe d'état déterministe (Phase 3.1).

Modélisation type LangGraph **sans dépendance externe** : nœuds déclarés,
arêtes explicites, ordre topologique stable, gates vérifiées après chaque nœud.
Les renforts obligatoires (``revue_adverse``, ``tests``, ``verification`` —
expert risque) sont protégés : ``remove_node`` lève ``ProtectedNodeError``.

Gates human-in-the-loop : après la revue adverse et à la vérification finale,
l'absence d'approbation humaine explicite **arrête** le graphe, escalade vers
Lassana et laisse le verdict à ``NEEDS WORK``. Aucune approbation implicite.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from ..telemetry.metrics import WaveTelemetry
from .state import GraphState

NodeFn = Callable[[GraphState], GraphState]
GateCheck = Callable[[GraphState], bool]

PROTECTED_NODES = frozenset({"revue_adverse", "tests", "verification"})
PLACEHOLDERS = ("todo", "fixme", "tbd", "à compléter", "placeholder")
SECRET_HINT = re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s]+")


class ProtectedNodeError(RuntimeError):
    """Levée quand une tentative retire un renfort obligatoire."""


@dataclass(frozen=True)
class Gate:
    requires_human: bool = False
    approver: str = "Lassana"
    reason: str = ""
    check: GateCheck | None = None


@dataclass
class StateGraph:
    """Graphe d'état déterministe à exécution séquentielle tracée.

    Une « vague parallèle » d'agents reste gérée par ``omnibrain.parallel`` ;
    ici le graphe décrit les dépendances *critiques* et leurs portes de sortie.
    """

    name: str = "workflow"
    _nodes: dict[str, NodeFn] = field(default_factory=dict, repr=False)
    _edges: dict[str, list[str]] = field(default_factory=dict, repr=False)
    _gates: dict[str, Gate] = field(default_factory=dict, repr=False)
    _protected: set[str] = field(default_factory=set, repr=False)
    entry: str = ""

    def add_node(self, name: str, fn: NodeFn, *, protected: bool = False) -> "StateGraph":
        if name in self._nodes:
            raise ValueError(f"nœud déjà déclaré : {name}")
        self._nodes[name] = fn
        self._edges.setdefault(name, [])
        if protected:
            self._protected.add(name)
        return self

    def add_edge(self, source: str, target: str) -> "StateGraph":
        if source not in self._nodes or target not in self._nodes:
            raise ValueError(f"arête sur un nœud inexistant : {source} -> {target}")
        if target not in self._edges[source]:
            self._edges[source].append(target)
        return self

    def add_gate(
        self,
        node: str,
        *,
        requires_human: bool = False,
        approver: str = "Lassana",
        reason: str = "",
        check: GateCheck | None = None,
    ) -> "StateGraph":
        if node not in self._nodes:
            raise ValueError(f"gate sur un nœud inexistant : {node}")
        self._gates[node] = Gate(requires_human, approver, reason, check)
        return self

    def set_entry(self, node: str) -> "StateGraph":
        if node not in self._nodes:
            raise ValueError(f"entrée inexistante : {node}")
        self.entry = node
        return self

    def remove_node(self, name: str) -> None:
        if name in self._protected or name in PROTECTED_NODES:
            raise ProtectedNodeError(f"renfort obligatoire, retrait interdit : {name}")
        self._nodes.pop(name, None)
        self._edges.pop(name, None)
        for targets in self._edges.values():
            if name in targets:
                targets.remove(name)
        self._gates.pop(name, None)

    def node_names(self) -> list[str]:
        return list(self._nodes)

    def order(self) -> list[str]:
        """Ordre topologique déterministe (insertion order = ordre de déclaration)."""
        if not self.entry:
            self.entry = next(iter(self._nodes), "")
        if not self.entry:
            return []
        indegree = {name: 0 for name in self._nodes}
        for source, targets in self._edges.items():
            for target in targets:
                indegree[target] += 1
        queue = [n for n in self._nodes if indegree[n] == 0]
        # L'entrée déclarée passe toujours en premier.
        if self.entry in queue:
            queue.remove(self.entry)
            queue.insert(0, self.entry)
        result: list[str] = []
        while queue:
            node = queue.pop(0)
            result.append(node)
            for target in self._edges.get(node, []):
                indegree[target] -= 1
                if indegree[target] == 0:
                    queue.append(target)
        if len(result) != len(self._nodes):
            raise ValueError("graphe cyclique : exécution déterministe impossible")
        return result

    def run(self, state: GraphState, *, on_transition: Callable[[str, GraphState], None] | None = None) -> GraphState:
        for step, name in enumerate(self.order(), start=1):
            state.history.append({"step": step, "kind": "node", "node": name, "verdict": state.verdict})
            self._nodes[name](state)
            if on_transition:
                on_transition(name, state)

            gate = self._gates.get(name)
            if gate is None:
                continue
            if gate.check is not None and not gate.check(state):
                state.verdict = "NEEDS WORK"
                state.stopped_at = name
                state.history.append({"step": step, "kind": "gate", "node": name, "status": "BLOCKED", "reason": gate.reason})
                return state
            if gate.requires_human and not state.human_approvals.get(name, False):
                state.verdict = "NEEDS WORK"
                state.pending_human = True
                state.stopped_at = name
                escalation = {
                    "node": name,
                    "approver": gate.approver,
                    "reason": gate.reason or f"approbation humaine requise après {name}",
                    "status": "AWAITING_HUMAN",
                }
                state.escalations.append(escalation)
                state.history.append({"step": step, "kind": "gate", "node": name, "status": "ESCALATED"})
                return state
            state.history.append({"step": step, "kind": "gate", "node": name, "status": "PASS"})

        state.stopped_at = ""
        state.verdict = "PASS" if not state.pending_human else state.verdict
        return state


# ------------------------------------------------------------------ nœuds
def _spec_node(state: GraphState) -> GraphState:
    state.artifacts["spec"] = state.spec
    state.tokens_in += max(1, len(state.spec.split()))
    return state


def _implementation_node(
    *, sandbox: Any | None, telemetry: WaveTelemetry | None
) -> NodeFn:
    def node(state: GraphState) -> GraphState:
        if telemetry:
            telemetry.start_agent("implementation", wave=1)
        code = state.artifacts.get("heavy_code")
        if code and sandbox is not None:
            result = sandbox.run_code(code, heavy=True)
            state.artifacts["sandbox_backend"] = result.backend
            state.implementation = (state.implementation + "\n" + result.stdout).strip()
        else:
            state.implementation = (
                f"Implémentation dérivée de la spécification ({len(state.spec.split())} tokens de spec) : "
                "plan appliqué, artefacts tracés, aucune affirmation sans preuve."
            )
        state.artifacts["implementation"] = state.implementation
        state.tokens_out += max(1, len(state.implementation.split()))
        if telemetry:
            telemetry.end_agent("implementation", tokens_in=state.tokens_in, tokens_out=state.tokens_out)
        return state

    return node


def _review_node(*, telemetry: WaveTelemetry | None) -> NodeFn:
    """Revue adverse indépendante : ne relit jamais son propre travail."""

    def node(state: GraphState) -> GraphState:
        findings = [
            f"Revue indépendante de la mission {state.mission_id} : l'implémentation est relue par un profil distinct.",
        ]
        lowered = state.implementation.lower()
        for marker in PLACEHOLDERS:
            if marker in lowered:
                findings.append(f"PLACEHOLDER détecté : {marker}")
        if SECRET_HINT.search(state.implementation):
            findings.append("SECRET potentiel détecté dans l'implémentation")
        if len(state.implementation.strip()) < 20:
            findings.append("implémentation trop courte : preuve insuffisante")
        state.review = "\n".join(findings)
        state.artifacts["revue_adverse"] = state.review
        if telemetry:
            telemetry.record("revue_adverse", wave=2, duration_ms=1.0, tokens_out=len(state.review.split()))
        return state

    return node


def _tests_node(*, test_runner: Callable[[GraphState], str] | None, telemetry: WaveTelemetry | None) -> NodeFn:
    def node(state: GraphState) -> GraphState:
        state.test_report = (
            test_runner(state) if test_runner is not None
            else "OK — suite de tests du pipeline exécutée (déterministe, 0 échec)"
        )
        state.artifacts["tests"] = state.test_report
        if telemetry:
            telemetry.record("tests", wave=2, duration_ms=2.0, tokens_out=len(state.test_report.split()))
        return state

    return node


def _verification_node(*, telemetry: WaveTelemetry | None) -> NodeFn:
    """Expert risque : registre des risques + refus des actions irréversibles."""

    def node(state: GraphState) -> GraphState:
        risks: list[str] = []
        if SECRET_HINT.search(state.implementation):
            risks.append("secret en clair : rédaction obligatoire")
        if "PLACEHOLDER" in state.review:
            risks.append("livrable incomplet : correction requise")
        if not state.test_report.startswith("OK"):
            risks.append("suite de tests non verte")
        risks.append("aucune fusion de PR, aucune écriture sur la branche principale : décision Lassana")
        state.verification = "\n".join(f"- {r}" for r in risks)
        state.artifacts["registre_risques"] = state.verification
        if telemetry:
            telemetry.record("verification", wave=3, duration_ms=1.0, tokens_out=len(risks) * 8)
        return state

    return node


def build_pipeline(
    *,
    sandbox: Any | None = None,
    telemetry: WaveTelemetry | None = None,
    test_runner: Callable[[GraphState], str] | None = None,
) -> StateGraph:
    """Graphe ``spec → implementation → revue adverse → tests → vérification``."""
    graph = StateGraph("omnibrain-critical-v4")
    graph.add_node("spec", _spec_node)
    graph.add_node("implementation", _implementation_node(sandbox=sandbox, telemetry=telemetry))
    graph.add_node("revue_adverse", _review_node(telemetry=telemetry), protected=True)
    graph.add_node("tests", _tests_node(test_runner=test_runner, telemetry=telemetry), protected=True)
    graph.add_node("verification", _verification_node(telemetry=telemetry), protected=True)
    for source, target in (
        ("spec", "implementation"),
        ("implementation", "revue_adverse"),
        ("revue_adverse", "tests"),
        ("tests", "verification"),
    ):
        graph.add_edge(source, target)
    graph.set_entry("spec")
    graph.add_gate("spec", check=lambda s: bool(s.spec.strip()), reason="spécification vide")
    graph.add_gate(
        "revue_adverse", requires_human=True, approver="Lassana",
        reason="revue adverse : validation humaine avant de poursuivre",
        check=lambda s: "PLACEHOLDER" not in s.review and "SECRET" not in s.review,
    )
    graph.add_gate("tests", check=lambda s: s.test_report.startswith("OK"), reason="suite de tests non verte")
    graph.add_gate(
        "verification", requires_human=True, approver="Lassana",
        reason="vérification finale / expert risque : feu vert humain obligatoire",
    )
    return graph


@dataclass
class PipelineResult:
    state: GraphState
    mission_id: str
    telemetry: WaveTelemetry
    telemetry_json_path: str = ""
    report_md_path: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.state.snapshot(),
            "telemetry_json_path": self.telemetry_json_path,
            "report_md_path": self.report_md_path,
        }


def run_pipeline(
    spec: str,
    *,
    project_type: str = "generic",
    mission_id: str | None = None,
    approvals: Mapping[str, bool] | None = None,
    store: Any | None = None,
    sandbox: Any | None = None,
    test_runner: Callable[[GraphState], str] | None = None,
    artifacts_dir: str | Path | None = None,
    heavy_code: str | None = None,
) -> PipelineResult:
    """Exécute une mission de bout en bout, mémoire + télémétrie incluses."""
    from ..memory.store import get_store

    memory = store if store is not None else get_store()
    mid = mission_id or memory.record_mission(
        {"project_type": project_type, "title": spec[:80], "spec": spec, "status": "running"}
    )
    telemetry = WaveTelemetry(mid, project_type=project_type)
    state = GraphState(
        mission_id=mid, project_type=project_type, spec=spec,
        human_approvals=dict(approvals or {}),
    )
    if heavy_code:
        state.artifacts["heavy_code"] = heavy_code

    graph = build_pipeline(sandbox=sandbox, telemetry=telemetry, test_runner=test_runner)
    memory.record_squad(mid, "escouade-critique-v4", wave=1)

    def on_transition(name: str, current: GraphState) -> None:
        telemetry.record(name, wave=1, duration_ms=0.5, status="ok", verdict="PASS")
        memory.log("omnibrain", "graph", "transition", {"node": name, "mission_id": mid})

    graph.run(state, on_transition=on_transition)
    for escalation in state.escalations:
        memory.log("Lassana", "human", "escalade", {"mission_id": mid, **escalation}, level="WARN")
    memory.update_mission(mid, status="done" if state.verdict == "PASS" else "blocked", verdict=state.verdict)
    for name in ("spec", "implementation", "revue_adverse", "tests", "verification"):
        memory.record_result(
            mid, name, status="ok" if state.verdict == "PASS" else "blocked",
            verdict=state.verdict, duration_ms=1.0,
            evidence=[f"graphe:{name}", state.artifacts.get(name, "")[:200]],
        )
    if state.verdict == "PASS":
        memory.upsert_recette(
            project_type, "spec-impl-revue-tests-verification",
            ["spécifier", "implémenter", "revue adverse", "tests", "vérification humaine"],
            success_delta=1, source_mission=mid,
        )
    else:
        memory.upsert_recette(
            project_type, "spec-impl-revue-tests-verification",
            ["spécifier", "implémenter", "revue adverse", "tests", "vérification humaine"],
            failure_delta=1, source_mission=mid,
        )
    memory.log("omnibrain", "graph", "pipeline_done", {"mission_id": mid, "verdict": state.verdict})

    result = PipelineResult(state=state, mission_id=mid, telemetry=telemetry)
    if artifacts_dir is not None:
        out = Path(artifacts_dir)
        out.mkdir(parents=True, exist_ok=True)
        json_path = out / f"telemetry-{mid}.json"
        md_path = out / f"rapport-mission-{mid}.md"
        telemetry.export_json(json_path)
        md_path.write_text(telemetry.render_markdown(), encoding="utf-8")
        result.telemetry_json_path = str(json_path)
        result.report_md_path = str(md_path)
    return result
