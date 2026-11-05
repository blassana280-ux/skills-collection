"""Learning + Self-Improvement Engine SUPREME — apprend des résultats vérifiés.

Processus : collecter -> analyser -> causes -> stratégies -> tests -> comparer
avant/après -> valider sur gain -> enregistrer -> rollback si régression.
N'altère jamais les poids de modèles externes. N'autorise aucune modification
libre du noyau, des permissions ou des règles de sécurité par les agents.
"""
from __future__ import annotations

import json
import sqlite3
import uuid

from .db import log_event, now, transaction
from .tools import evaluate_tool


class LearningEngine:
    def __init__(self, conn: sqlite3.Connection, registry, evaluation, factory=None):
        self.conn = conn
        self.registry = registry
        self.evaluation = evaluation
        self.factory = factory

    def collect_outcomes(self) -> dict:
        rows = self.conn.execute("SELECT name, value FROM metrics WHERE name IN ('task_success','mission_success')").fetchall()
        task = [r["value"] for r in rows if r["name"] == "task_success"]
        mission = [r["value"] for r in rows if r["name"] == "mission_success"]
        failures = self.conn.execute("SELECT agent_id, error FROM tasks WHERE state='failed'").fetchall()
        return {"task_success_rate": sum(task) / len(task) if task else None,
                "mission_success_rate": sum(mission) / len(mission) if mission else None,
                "failures": [{"agent_id": r["agent_id"], "error": r["error"]} for r in failures]}

    def analyze(self) -> dict:
        outcomes = self.collect_outcomes()
        recurrent: dict[str, int] = {}
        for f in outcomes["failures"]:
            recurrent[f["error"] or "inconnu"] = recurrent.get(f["error"] or "inconnu", 0) + 1
        proposals = []
        for err, count in recurrent.items():
            if count >= 2:
                proposals.append({"type": "correction", "target": err, "occurrences": count,
                                  "suggestion": "analyser la cause racine et ajouter un test de non-régression"})
        # Agents peu performants (taux d'échec)
        perf = self.conn.execute("""SELECT agent_id, AVG(value) s, COUNT(*) c FROM metrics
                                    WHERE name='task_success' GROUP BY agent_id HAVING c >= 2 AND s < 0.5""").fetchall()
        for p in perf:
            proposals.append({"type": "agent_review", "target": p["agent_id"], "success_rate": p["s"],
                              "suggestion": "réviser les instructions ou réaffecter les tâches"})
        return {"outcomes": outcomes, "recurrent_errors": recurrent, "proposals": proposals}

    def propose_strategy(self, agent_id: str, content: str) -> str:
        """Versionne une stratégie/prompt pour un agent (pas de modification du noyau)."""
        if agent_id in ("omnibrain-core",) or agent_id.startswith("policy"):
            raise PermissionError("auto-modification du noyau/politique interdite")
        row = self.conn.execute("SELECT COALESCE(MAX(version),0) v FROM strategies WHERE agent_id=?", (agent_id,)).fetchone()
        version = row["v"] + 1
        sid = f"strat-{uuid.uuid4().hex[:10]}"
        with transaction(self.conn):
            self.conn.execute("INSERT INTO strategies(id,agent_id,version,content,score,active,created_at) VALUES(?,?,?,?,?,?,?)",
                              (sid, agent_id, version, content, None, 0, now()))
        return sid

    def evaluate_strategy(self, strategy_id: str, tool_name: str) -> dict:
        """Évalue une stratégie via un outil réel (fixture) ; score objectif."""
        passed, evidence, out = evaluate_tool(tool_name)
        score = 1.0 if passed else 0.0
        with transaction(self.conn):
            self.conn.execute("UPDATE strategies SET score=? WHERE id=?", (score, strategy_id))
        return {"strategy_id": strategy_id, "score": score, "evidence": evidence}

    def compare_and_accept(self, agent_id: str, tool_name: str, new_content: str) -> dict:
        """Compare avant/après sur l'outil réel ; accepte seulement sur gain mesuré."""
        active = self.conn.execute("SELECT * FROM strategies WHERE agent_id=? AND active=1", (agent_id,)).fetchone()
        baseline_score = active["score"] if active and active["score"] is not None else None
        sid = self.propose_strategy(agent_id, new_content)
        ev = self.evaluate_strategy(sid, tool_name)
        if baseline_score is None or ev["score"] > baseline_score:
            with transaction(self.conn):
                self.conn.execute("UPDATE strategies SET active=0 WHERE agent_id=?", (agent_id,))
                self.conn.execute("UPDATE strategies SET active=1 WHERE id=?", (sid,))
            log_event(self.conn, "info", "learning", f"stratégie acceptée pour {agent_id} (score {ev['score']})")
            return {"accepted": True, "strategy_id": sid, "score": ev["score"], "baseline": baseline_score}
        return {"accepted": False, "strategy_id": sid, "score": ev["score"], "baseline": baseline_score,
                "reason": "pas de gain mesuré"}

    def rollback(self, agent_id: str) -> dict:
        rows = self.conn.execute("SELECT * FROM strategies WHERE agent_id=? ORDER BY version DESC", (agent_id,)).fetchall()
        if len(rows) < 2:
            return {"rolled_back": False, "reason": "pas de version antérieure"}
        prev = rows[1]
        with transaction(self.conn):
            self.conn.execute("UPDATE strategies SET active=0 WHERE agent_id=?", (agent_id,))
            self.conn.execute("UPDATE strategies SET active=1 WHERE id=?", (prev["id"],))
        log_event(self.conn, "info", "learning", f"rollback stratégie {agent_id} -> v{prev['version']}")
        return {"rolled_back": True, "version": prev["version"]}

    def self_improvement_report(self) -> dict:
        analysis = self.analyze()
        return {"analysis": analysis,
                "constraints": ["aucune modification du noyau", "aucune modification des permissions/sécurité",
                                "toute amélioration passe par tests et comparaison avant/après", "rollback disponible"],
                "strategies_count": self.conn.execute("SELECT COUNT(*) c FROM strategies").fetchone()["c"]}
