"""Mission Planner + Task Decomposer SUPREME — décompose un objectif en DAG de
tâches, sélectionne les agents et groupes tactiques, valide le graphe.
"""
from __future__ import annotations

import uuid

from .tools import TOOLS, run_tool


def classify(objective: str) -> dict:
    words = len(objective.split())
    connectors = sum(objective.lower().count(c) for c in (" et ", " puis ", " ensuite ", ",", " and "))
    score = words // 8 + connectors
    level = "simple" if score < 3 else ("moyenne" if score < 7 else "complexe")
    squad = {"simple": 1, "moyenne": 3, "complexe": 5}[level]
    return {"level": level, "score": score, "squad_size": squad}


class MissionPlanner:
    def __init__(self, registry, router=None):
        self.registry = registry
        self.router = router

    def _tool_agents(self, candidates: list[dict]) -> list[dict]:
        out = []
        for a in candidates:
            rep = next(e for e in a["profile"]["eval_tests"] if e["id"] == "representative")
            if rep["mode"] == "tool":
                out.append(a)
        return out

    def plan(self, spec: dict) -> dict:
        objective = spec["objective"]
        classification = classify(objective)
        mission_id = spec.get("mission_id") or f"mis-{uuid.uuid4().hex[:12]}"
        tasks: list[dict] = []

        if spec.get("tasks"):
            # Tâches explicites fournies par l'appelant (validées).
            for i, t in enumerate(spec["tasks"], 1):
                agent = self.registry.get(t["agent_id"])
                if agent is None:
                    raise KeyError(f"agent inconnu : {t['agent_id']}")
                tool = t.get("tool") or next((e.get("tool") for e in agent["profile"]["eval_tests"]
                                              if e["id"] == "representative" and e["mode"] == "tool"), None)
                if tool and tool not in agent["profile"]["allowed_tools"]:
                    raise PermissionError(f"{t['agent_id']} n'est pas autorisé à utiliser {tool}")
                tasks.append({"id": f"{mission_id}-t{i:03d}", "agent_id": t["agent_id"], "tool": tool,
                              "input": t.get("input", TOOLS[tool].fixture if tool else {}),
                              "depends_on": t.get("depends_on", []), "kind": "execute"})
        else:
            # Décomposition automatique : recherche d'agents pertinents activables hors ligne.
            candidates = self.registry.search(objective, limit=30)
            tool_agents = self._tool_agents(candidates)[:classification["squad_size"]]
            if not tool_agents:
                # repli : prendre des agents outil représentatifs des divisions partenaires
                tool_agents = self._tool_agents(self.registry.list(kind="specialist"))[:classification["squad_size"]]
            inputs = spec.get("inputs", {})
            for i, a in enumerate(tool_agents, 1):
                rep = next(e for e in a["profile"]["eval_tests"] if e["id"] == "representative")
                tool = rep["tool"]
                tasks.append({"id": f"{mission_id}-t{i:03d}", "agent_id": a["id"], "tool": tool,
                              "input": inputs.get(a["id"], TOOLS[tool].fixture),
                              "depends_on": [], "kind": "execute"})
            # Vérification indépendante par une autre division (D09 contract_check).
            exec_ids = [t["id"] for t in tasks]
            verifier = next((a for a in self.registry.list(division="D09", kind="specialist")
                             if "contract_check" in a["profile"]["allowed_tools"]), None)
            if verifier and tasks:
                tasks.append({"id": f"{mission_id}-t{len(tasks)+1:03d}", "agent_id": verifier["id"],
                              "tool": "contract_check",
                              "input": {"contract": {"name": "mission-result", "version": "1",
                                                     "fields": [{"name": "results", "type": "array"}]}},
                              "depends_on": exec_ids, "kind": "verify"})
            # Rapport par le chef de la division principale.
            if tasks:
                primary_div = self.registry.get(tasks[0]["agent_id"])["profile"]["division"]
                manager = next((a for a in self.registry.list(division=primary_div, kind="manager")), None)
                if manager:
                    tasks.append({"id": f"{mission_id}-t{len(tasks)+1:03d}", "agent_id": manager["id"],
                                  "tool": "division_report",
                                  "input": {"division": primary_div,
                                            "agents": [{"id": t["agent_id"], "status": "validated"} for t in tasks if t["kind"] == "execute"],
                                            "metrics": {}},
                                  "depends_on": [tasks[-1]["id"]], "kind": "report"})

        # Validation du DAG
        nodes = [t["id"] for t in tasks]
        edges = [[d, t["id"]] for t in tasks for d in t["depends_on"]]
        dag = run_tool("dag_validate", {"nodes": nodes, "edges": edges})
        if not dag["valid"]:
            raise ValueError("graphe de tâches invalide (cycle)")
        return {"mission_id": mission_id, "objective": objective, "classification": classification,
                "tasks": tasks, "dag_order": dag["topological_order"],
                "priority": spec.get("priority", 5), "budget_usd": spec.get("budget_usd", 0.05),
                "privacy": spec.get("privacy", "standard")}
