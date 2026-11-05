"""Mission Planner + Task Decomposer SUPREME — décompose un objectif en DAG de
tâches, sélectionne les agents et groupes tactiques, valide le graphe.
"""
from __future__ import annotations

import uuid

from .tools import TOOLS, run_tool


def representative_mode(agent: dict) -> str:
    return next(e for e in agent["profile"]["eval_tests"] if e["id"] == "representative")["mode"]


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
                              "depends_on": t.get("depends_on", []), "kind": "execute",
                              "why": (f"agent explicitement désigné par l'appelant ; "
                                      f"{'outil ' + tool + ' autorisé et vérifié' if tool else 'tâche LLM : exécutée via le routeur multi-modèles si fournisseur configuré, sinon bloquée honnêtement'}")})
        else:
            # Décomposition automatique. Le mode LLM est explicite : aucun repli
            # silencieux vers un outil ne doit faire croire à une inférence réelle.
            llm_mode = spec.get("mode") == "llm" or bool(spec.get("require_llm"))
            cross_division = bool(spec.get("cross_division", classification["level"] == "complexe"))
            candidates = self.registry.search(objective, limit=60)
            pool = [a for a in candidates if (representative_mode(a) == "llm") == llm_mode]
            if not pool:
                pool = [a for a in self.registry.list(kind="specialist") if (representative_mode(a) == "llm") == llm_mode]
            selected = []
            if cross_division:
                seen_div = set()
                for a in pool:
                    if a["division"] not in seen_div:
                        selected.append(a); seen_div.add(a["division"])
                    if len(selected) >= classification["squad_size"]:
                        break
            for a in pool:
                if len(selected) >= classification["squad_size"]:
                    break
                if a not in selected:
                    selected.append(a)
            inputs = spec.get("inputs", {})
            for i, a in enumerate(selected, 1):
                prof = a["profile"]
                rep = next(e for e in prof["eval_tests"] if e["id"] == "representative")
                tool = None if llm_mode else rep["tool"]
                matched = [w for w in objective.lower().split()
                           if w in (prof["objective"] + " " + " ".join(prof["primary_skills"])).lower()][:4]
                task_input = inputs.get(a["id"], {"objectif": objective, "specialite": prof["specialization"]} if llm_mode else TOOLS[tool].fixture)
                tasks.append({"id": f"{mission_id}-t{i:03d}", "agent_id": a["id"], "tool": tool,
                              "input": task_input, "depends_on": [], "kind": "execute",
                              "why": (f"termes communs : {', '.join(matched) or 'sélection par spécialité/division'} ; "
                                      f"division {prof['division']} ; "
                                      + ("inférence LLM requise, aucun substitut local simulé" if llm_mode else f"outil déterministe {tool} autorisé"))})
            exec_ids = [t["id"] for t in tasks]
            if tasks and not llm_mode:
                primary_div = self.registry.get(tasks[0]["agent_id"])["profile"]["division"]
                selected_ids = {t["agent_id"] for t in tasks}
                verifier = next((a for a in self.registry.list(kind="specialist")
                                 if "contract_check" in a["profile"]["allowed_tools"]
                                 and a["id"] not in selected_ids and a["division"] != primary_div), None)
                if verifier:
                    tasks.append({"id": f"{mission_id}-t{len(tasks)+1:03d}", "agent_id": verifier["id"],
                                  "tool": "contract_check",
                                  "input": {"contract": {"name": "mission-result", "version": "1",
                                                         "fields": [{"name": "results", "type": "array"}]}},
                                  "depends_on": exec_ids, "kind": "verify",
                                  "why": f"vérification structurelle indépendante par {verifier['division']} ; ne certifie pas la vérité métier"})
                manager = next((a for a in self.registry.list(division=primary_div, kind="manager")), None)
                if manager:
                    tasks.append({"id": f"{mission_id}-t{len(tasks)+1:03d}", "agent_id": manager["id"],
                                  "tool": "division_report",
                                  "input": {"division": primary_div,
                                            "agents": [{"id": t["agent_id"], "status": self.registry.get(t["agent_id"])["status"]} for t in tasks if t["kind"] == "execute"],
                                            "metrics": {}},
                                  "depends_on": [tasks[-1]["id"]], "kind": "report",
                                  "why": f"chef {primary_div} : consolidation de statut, sans inventer de métrique"})

        # Validation du DAG
        nodes = [t["id"] for t in tasks]
        edges = [[d, t["id"]] for t in tasks for d in t["depends_on"]]
        dag = run_tool("dag_validate", {"nodes": nodes, "edges": edges})
        if not dag["valid"]:
            raise ValueError("graphe de tâches invalide (cycle)")
        # Explicabilité : pourquoi cette stratégie, cette taille d'escouade, ces étapes.
        routable = self.router.routable_models() if self.router is not None and hasattr(self.router, "routable_models") else []
        provider_note = ("mode LLM explicite : inférence réelle requise" if spec.get("mode") == "llm" or spec.get("require_llm") else
                         "aucun fournisseur IA autorisé/tarifé : outils déterministes locaux gratuits" if not routable else
                         "fournisseur(s) autorisé(s) : inférence possible sur preuve réelle")
        explanation = {
            "classification": f"objectif de {len(objective.split())} mots, score {classification['score']} -> niveau {classification['level']}",
            "squad_size": f"escouade de {classification['squad_size']} agent(s) selon le niveau {classification['level']} (simple=1, moyenne=3, complexe=5)",
            "strategy": provider_note,
            "verification": "mode LLM : conseil avec références de preuves ; mode local : contrôle structurel indépendant, pas certification métier",
            "arbitrage": "mission complexe -> conseil multi-modèles (preuves + indépendance, pas majorité) ; sans fournisseur, statut indisponible honnête",
            "task_rationale": "chaque tâche porte un champ 'why' expliquant la sélection de l'agent et de l'outil",
        }
        return {"mission_id": mission_id, "objective": objective, "classification": classification,
                "tasks": tasks, "dag_order": dag["topological_order"], "explanation": explanation,
                "priority": spec.get("priority", 5), "budget_usd": spec.get("budget_usd", 0.05),
                "privacy": spec.get("privacy", "standard")}
