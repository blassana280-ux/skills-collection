"""Evaluation Engine SUPREME — 7 tests par profil, activation sur preuve réelle.

Un agent ne devient `operational` qu'après exécution réelle réussie de sa mission
représentative. Les missions nécessitant un LLM sans fournisseur configuré sont
`deferred` (différées), jamais comptées comme réussies.
"""
from __future__ import annotations

import json
import sqlite3

from .db import log_event, now, transaction
from .profiles import EVAL_IDS, REQUIRED_FIELDS
from .tools import TOOLS, evaluate_tool, run_tool


class EvaluationEngine:
    def __init__(self, conn: sqlite3.Connection, registry, router=None):
        self.conn = conn
        self.registry = registry
        self.router = router  # si fourni : les représentatifs LLM tentent un VRAI appel

    def _record(self, agent_id: str, eval_id: str, mode: str, passed: bool, deferred: bool, evidence: str) -> None:
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO eval_runs(agent_id,eval_id,mode,passed,deferred,evidence,at) VALUES(?,?,?,?,?,?,?)",
                (agent_id, eval_id, mode, int(passed), int(deferred), evidence[:500], now()))

    def run_profile_tests(self, agent_id: str) -> dict:
        prof = self.registry.profile(agent_id)
        results: dict[str, dict] = {}

        # 1. load
        ok = bool(prof.get("id")) and all(f in prof for f in REQUIRED_FIELDS)
        results["load"] = {"passed": ok, "evidence": "profil chargé, champs présents" if ok else "champs manquants"}
        # 2. config
        cfg_ok = (prof["risk_level"] in ("low", "medium", "high", "critical")
                  and all(t in TOOLS for t in prof["allowed_tools"])
                  and {e["id"] for e in prof["eval_tests"]} == set(EVAL_IDS))
        results["config"] = {"passed": cfg_ok, "evidence": "configuration valide" if cfg_ok else "configuration invalide"}
        # 3. representative
        rep = next(e for e in prof["eval_tests"] if e["id"] == "representative")
        if rep["mode"] == "tool":
            try:
                passed, evidence, out = evaluate_tool(rep["tool"])
                results["representative"] = {"passed": passed, "deferred": False, "evidence": evidence, "output": out}
            except Exception as e:
                results["representative"] = {"passed": False, "deferred": False, "evidence": f"erreur outil : {e}"}
        else:
            # Représentatif LLM : vrai appel si un fournisseur est configuré ; différé sinon.
            llm_done = False
            if self.router is not None:
                self.router.detect()
                if self.router.configured_models():
                    prompt = rep.get("prompt") or f"Mission représentative : {prof['objective']}"
                    res = self.router.complete(
                        {"capabilities": ["general"], "max_cost_usd": 0.02},
                        [{"role": "system", "content": prof["system_instructions"]},
                         {"role": "user", "content": prompt}],
                        max_tokens=256, agent_id=agent_id)
                    if res["ok"] and res["text"].strip():
                        results["representative"] = {
                            "passed": True, "deferred": False,
                            "evidence": f"appel LLM réel réussi via {res['provider']}/{res['model']}",
                            "output": {"text": res["text"][:500],
                                       "model": f"{res['provider']}/{res['model']}"}}
                    else:
                        results["representative"] = {
                            "passed": False, "deferred": False,
                            "evidence": f"appel LLM réel échoué : {res['error'][:200]}"}
                    llm_done = True
            if not llm_done:
                results["representative"] = {"passed": False, "deferred": True,
                                             "evidence": "mission LLM différée : aucun fournisseur configuré"}
        # 4. structured_output
        so_ok = bool(prof["output_format"])
        if rep["mode"] == "tool" and results["representative"].get("output") is not None:
            so_ok = so_ok and isinstance(results["representative"]["output"], dict)
        results["structured_output"] = {"passed": so_ok, "evidence": "format de sortie structuré respecté"}
        # 5. permissions
        perms = prof["permissions"]
        perm_ok = (perms.get("network") == "deny" and not perms.get("github_write")
                   and perms.get("secrets") == "none" and not perms.get("spawn_agents"))
        results["permissions"] = {"passed": perm_ok, "evidence": "moindre privilège respecté"}
        # 6. errors
        if rep["mode"] == "tool":
            try:
                run_tool(rep["tool"], {})
                err_ok = True  # l'outil gère l'entrée vide sans planter
                err_ev = "entrée vide gérée sans exception"
            except Exception as e:
                err_ok, err_ev = False, f"entrée vide non gérée : {e}"
        else:
            err_ok = bool(prof["forbidden_tasks"])
            err_ev = "tâches interdites définies"
        results["errors"] = {"passed": err_ok, "evidence": err_ev}
        # 7. quality
        q_ok = len(prof["quality_criteria"]) >= 2
        results["quality"] = {"passed": q_ok, "evidence": f"{len(prof['quality_criteria'])} critères de qualité"}

        for eid, r in results.items():
            self._record(agent_id, eid, rep["mode"] if eid == "representative" else "offline",
                         r["passed"], r.get("deferred", False), r["evidence"])
        passed = sum(1 for r in results.values() if r["passed"])
        deferred = sum(1 for r in results.values() if r.get("deferred"))
        return {"agent_id": agent_id, "passed": passed, "deferred": deferred,
                "total": len(results), "results": results}

    def validate_agent(self, agent_id: str) -> dict:
        summary = self.run_profile_tests(agent_id)
        rep = summary["results"]["representative"]
        offline_ok = all(summary["results"][k]["passed"] for k in EVAL_IDS if k != "representative")
        rep_ok = rep["passed"] or rep.get("deferred")
        if offline_ok and rep_ok:
            self.registry.set_status(agent_id, "validated", f"contrôles offline OK, représentatif {'réussi' if rep['passed'] else 'différé'}")
            return {"validated": True, **summary}
        return {"validated": False, **summary}

    def activate_agent(self, agent_id: str) -> dict:
        summary = self.run_profile_tests(agent_id)
        rep = summary["results"]["representative"]
        offline_ok = all(summary["results"][k]["passed"] for k in EVAL_IDS if k != "representative")
        if offline_ok and rep["passed"] and not rep.get("deferred"):
            evidence = f"mission représentative exécutée : {rep['evidence']}"
            self.registry.set_status(agent_id, "operational", evidence)
            self.registry.set_status(agent_id, "monitored", evidence + " ; performances suivies par télémétrie")
            return {"activated": True, "status": "monitored", **summary}
        return {"activated": False, "reason": "mission représentative non réussie réellement", **summary}

    def evaluate_all(self, activate: bool = True) -> dict:
        counts = {"validated": 0, "operational": 0, "deferred": 0, "failed": 0}
        for agent in self.registry.list():
            v = self.validate_agent(agent["id"])
            if v["validated"]:
                counts["validated"] += 1
            else:
                counts["failed"] += 1
            if v["deferred"]:
                counts["deferred"] += 1
            if activate:
                a = self.activate_agent(agent["id"])
                if a["activated"]:
                    counts["operational"] += 1
        log_event(self.conn, "info", "evaluation", f"évaluation globale : {counts}")
        return counts
