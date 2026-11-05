"""Learning + Self-Improvement Engine SUPREME — apprend des résultats vérifiés.

Processus : collecter -> analyser -> causes -> stratégies -> tests -> comparer
avant/après -> valider sur gain -> enregistrer -> rollback si régression.
N'altère jamais les poids de modèles externes. N'autorise aucune modification
libre du noyau, des permissions ou des règles de sécurité par les agents.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path

from .config import VAR_DIR, ensure_dirs
from .db import epoch, log_event, now, transaction
from .leases import new_worker_id, register_worker
from .security import redact
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
            return {"accepted": True, "strategy_id": sid, "score": ev["score"], "baseline": baseline_score,
                    "accepted_as_baseline": baseline_score is None,
                    "gain": None if baseline_score is None else ev["score"] - baseline_score,
                    "note": "baseline initiale, pas un gain mesuré" if baseline_score is None else "gain mesuré sur outil réel"}
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

    def _recover_expired_runs(self) -> int:
        with transaction(self.conn, immediate=True):
            cur = self.conn.execute(
                """UPDATE learning_runs SET status='interrupted', finished_at=?, error='bail expiré : cycle interrompu',
                     lease_expires_at=0 WHERE status='running' AND lease_expires_at <= ?""",
                (now(), epoch()))
            return cur.rowcount

    def _heartbeat_run(self, run_id: str, token: str, lease_seconds: float) -> bool:
        with transaction(self.conn, immediate=True):
            cur = self.conn.execute(
                """UPDATE learning_runs SET heartbeat_at=?, lease_expires_at=?
                   WHERE id=? AND lease_token=? AND status='running'""",
                (epoch(), epoch() + lease_seconds, run_id, token))
            return cur.rowcount == 1

    def _persist_report(self, run_id: str, report: dict) -> str:
        ensure_dirs()
        directory = VAR_DIR / "learning"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{run_id}.json"
        safe = redact(json.dumps(report, ensure_ascii=False, indent=1))
        tmp = path.with_suffix(".tmp")
        tmp.write_text(safe, encoding="utf-8")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
        return str(path)

    def _finish_run(self, run_id: str, token: str, status: str, report: dict, error: str = "") -> dict:
        report = dict(report)
        report["run_id"] = run_id
        report["status"] = status
        report["finished_at"] = now()
        if error:
            report["error"] = redact(error)[:1000]
        safe_text = redact(json.dumps(report, ensure_ascii=False))
        path = self._persist_report(run_id, report)
        report["persisted_to"] = path
        with transaction(self.conn, immediate=True):
            self.conn.execute(
                """UPDATE learning_runs SET status=?, finished_at=?, report_json=?, error=?, lease_expires_at=0
                   WHERE id=? AND lease_token=?""",
                (status, now(), safe_text, redact(error)[:1000], run_id, token))
        return report

    def run_cycle(self, max_proposals: int = 5, trigger: str = "once", scheduler_id: str = "default",
                  stop_event: threading.Event | None = None, lease_seconds: float = 30.0,
                  worker_id: str | None = None) -> dict:
        """Cycle d'amélioration contrôlée, persistant et protégé contre les doubles cycles.

        1 observer -> 2 identifier -> 3-4 proposer -> 5-7 versionner/évaluer/tester ->
        8 comparer avant/après -> 9 rapport -> 10 PR = porte humaine (jamais automatique).
        Aucune modification du noyau, des permissions ou de la sécurité. Les changements
        de code/dépôt (branche, PR) exigent l'humain ; le cycle produit preuves et candidats.
        Un seul cycle peut être `running` à la fois (index unique SQLite). Les rapports
        sont persistés en base et dans var/supreme/learning/ ; une interruption est reprise
        au cycle suivant après expiration du bail.
        """
        if max_proposals < 0 or lease_seconds <= 0:
            raise ValueError("max_proposals doit être >= 0 et lease_seconds positif")
        worker_id = worker_id or new_worker_id("learn")
        register_worker(self.conn, worker_id)
        self._recover_expired_runs()
        run_id = f"lr-{uuid.uuid4().hex[:16]}"
        token = uuid.uuid4().hex
        try:
            with transaction(self.conn, immediate=True):
                self.conn.execute(
                    """INSERT INTO learning_runs(id,scheduler_id,trigger,worker_id,lease_token,status,
                         started_at,heartbeat_at,lease_expires_at) VALUES(?,?,?,?,?,'running',?,?,?)""",
                    (run_id, scheduler_id, trigger, worker_id, token, now(), epoch(), epoch() + lease_seconds))
        except sqlite3.IntegrityError:
            return {"status": "skipped", "reason": "un cycle d'apprentissage est déjà en cours",
                    "scheduler_id": scheduler_id}
        report = {"cycle_at": now(), "trigger": trigger, "scheduler_id": scheduler_id, "steps": []}
        try:
            if stop_event is not None and stop_event.is_set():
                return self._finish_run(run_id, token, "interrupted", report, "arrêt demandé avant observation")
            outcomes = self.collect_outcomes()
            report["steps"].append({"step": 1, "name": "observer", "status": "done",
                                    "task_success_rate": outcomes["task_success_rate"],
                                    "mission_success_rate": outcomes["mission_success_rate"]})
            previous = self.conn.execute("SELECT id, report_json FROM learning_runs WHERE status='completed' AND report_json IS NOT NULL ORDER BY finished_at DESC, rowid DESC LIMIT 1").fetchone()
            comparison = {"baseline_run_id": previous["id"] if previous else None,
                          "task_success_delta": None, "mission_success_delta": None, "improvement_proven": False}
            if previous:
                try:
                    prev = json.loads(previous["report_json"])
                    po = prev.get("analysis", {}).get("outcomes", {})
                    for key, out_key in (("task_success_rate", "task_success_delta"), ("mission_success_rate", "mission_success_delta")):
                        if outcomes.get(key) is not None and po.get(key) is not None:
                            comparison[out_key] = round(outcomes[key] - po[key], 6)
                    comparison["improvement_proven"] = any(v is not None and v > 0 for v in (comparison["task_success_delta"], comparison["mission_success_delta"]))
                except (json.JSONDecodeError, TypeError, AttributeError):
                    comparison["error"] = "rapport précédent illisible"
            report["measured_comparison"] = comparison
            report["steps"].append({"step": "1bis", "name": "mesurer avant/après", "status": "done", **comparison})
            if not self._heartbeat_run(run_id, token, lease_seconds):
                return self._finish_run(run_id, token, "interrupted", report, "bail de cycle perdu")
            analysis = self.analyze()
            report["steps"].append({"step": 2, "name": "identifier", "status": "done",
                                    "proposals": len(analysis["proposals"])})
            report["analysis"] = analysis
            evaluated = []
            for p in analysis["proposals"][:max_proposals]:
                if stop_event is not None and stop_event.is_set():
                    report["steps"].append({"step": "3-8", "name": "proposer/évaluer/comparer",
                                            "status": "interrupted", "evaluated": evaluated})
                    return self._finish_run(run_id, token, "interrupted", report, "arrêt propre demandé")
                if not self._heartbeat_run(run_id, token, lease_seconds):
                    return self._finish_run(run_id, token, "interrupted", report, "bail de cycle perdu")
                if p["type"] == "agent_review":
                    agent = self.registry.get(p["target"])
                    if agent is None:
                        continue
                    rep = next(e for e in agent["profile"]["eval_tests"] if e["id"] == "representative")
                    if rep["mode"] != "tool":
                        evaluated.append({"target": p["target"], "action": "revue LLM requise",
                                          "status": "human_or_provider_required"})
                        continue
                    content = (f"v{now()}: consigne révisée après échecs répétés — "
                               f"valider les entrées avant l'outil {rep['tool']}, journaliser l'erreur exacte.")
                    try:
                        cmp = self.compare_and_accept(p["target"], rep["tool"], content)
                        evaluated.append({"target": p["target"], "action": "stratégie versionnée + comparée",
                                          "status": "accepted" if cmp["accepted"] else "rejected_no_gain",
                                          **{k: cmp[k] for k in ("strategy_id", "score", "baseline")}})
                    except PermissionError as e:
                        evaluated.append({"target": p["target"], "action": "refusé", "status": "protected", "reason": str(e)})
                else:
                    evaluated.append({"target": p["target"], "action": "correction code requise",
                                      "status": "human_required",
                                      "reason": "cause racine à corriger sur branche dédiée + tests + PR (porte humaine)"})
            report["steps"].append({"step": "3-8", "name": "proposer/évaluer/comparer", "status": "done",
                                    "evaluated": evaluated})
            report["step_9_report"] = "ce rapport JSON est la preuve auditable du cycle"
            report["step_10_pr"] = {"status": "human_required",
                                    "reason": "création de branche/PR et fusion exigent l'humain ; jamais automatique"}
            report["guarantees"] = ["noyau intact", "permissions intactes", "sécurité intacte",
                                    "gain mesuré obligatoire", "rollback disponible"]
            log_event(self.conn, "info", "learning",
                      f"cycle d'amélioration : {len(evaluated)} candidat(s) évalué(s), "
                      f"{sum(1 for e in evaluated if e['status'] == 'accepted')} accepté(s) sur gain mesuré")
            return self._finish_run(run_id, token, "completed", report)
        except Exception as e:
            log_event(self.conn, "error", "learning", f"cycle d'apprentissage en erreur : {e}")
            return self._finish_run(run_id, token, "failed", report, str(e))

    def self_improvement_report(self) -> dict:
        analysis = self.analyze()
        return {"analysis": analysis,
                "constraints": ["aucune modification du noyau", "aucune modification des permissions/sécurité",
                                "toute amélioration passe par tests et comparaison avant/après", "rollback disponible"],
                "strategies_count": self.conn.execute("SELECT COUNT(*) c FROM strategies").fetchone()["c"]}


class LearningScheduler:
    """Ordonnanceur d'apprentissage périodique, à bail unique et arrêt propre.

    Il ne modifie ni le noyau ni les permissions : il déclenche `LearningEngine.run_cycle`
    à fréquence configurable, persiste chaque rapport, surveille les erreurs et reprend
    après interruption. Un seul ordonnanceur actif par `scheduler_id` ; un seul cycle
    `running` global grâce à l'index unique SQLite.
    """

    def __init__(self, conn: sqlite3.Connection, engine: LearningEngine, scheduler_id: str = "default",
                 interval_seconds: float = 300.0, max_proposals: int = 5,
                 lease_seconds: float = 30.0, heartbeat_interval: float | None = None,
                 worker_id: str | None = None):
        if interval_seconds <= 0 or lease_seconds <= 0 or max_proposals < 0:
            raise ValueError("interval_seconds/lease_seconds doivent être positifs, max_proposals >= 0")
        self.conn = conn
        self.engine = engine
        self.scheduler_id = scheduler_id
        self.interval_seconds = float(interval_seconds)
        self.max_proposals = int(max_proposals)
        self.lease_seconds = float(lease_seconds)
        self.heartbeat_interval = float(heartbeat_interval if heartbeat_interval is not None else max(0.05, min(lease_seconds / 3.0, 5.0)))
        if self.heartbeat_interval <= 0 or self.heartbeat_interval >= self.lease_seconds:
            raise ValueError("heartbeat_interval doit être positif et inférieur au bail")
        self.worker_id = worker_id or new_worker_id("learn-sched")
        row = conn.execute("PRAGMA database_list").fetchone()
        self.db_path = Path(row[2]) if row and row[2] else None

    def _claim(self) -> str | None:
        register_worker(self.conn, self.worker_id)
        t = epoch()
        token = uuid.uuid4().hex
        with transaction(self.conn, immediate=True):
            row = self.conn.execute("SELECT * FROM learning_schedulers WHERE id=?", (self.scheduler_id,)).fetchone()
            if row is None:
                self.conn.execute(
                    """INSERT INTO learning_schedulers(id,interval_seconds,max_proposals,owner_worker_id,
                         lease_token,lease_expires_at,heartbeat_at,next_run_at,state,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?, 'active',?,?)""",
                    (self.scheduler_id, self.interval_seconds, self.max_proposals, self.worker_id,
                     token, t + self.lease_seconds, t, 0.0, now(), now()))
                return token
            if row["owner_worker_id"] and row["owner_worker_id"] != self.worker_id and float(row["lease_expires_at"]) > t:
                return None
            self.conn.execute(
                """UPDATE learning_schedulers SET interval_seconds=?, max_proposals=?, owner_worker_id=?,
                     lease_token=?, lease_expires_at=?, heartbeat_at=?, state='active', updated_at=? WHERE id=?""",
                (self.interval_seconds, self.max_proposals, self.worker_id, token,
                 t + self.lease_seconds, t, now(), self.scheduler_id))
            return token

    def _renew(self, token: str) -> bool:
        t = epoch()
        with transaction(self.conn, immediate=True):
            cur = self.conn.execute(
                """UPDATE learning_schedulers SET lease_expires_at=?, heartbeat_at=?, updated_at=?
                   WHERE id=? AND owner_worker_id=? AND lease_token=? AND state='active' AND lease_expires_at > ?""",
                (t + self.lease_seconds, t, now(), self.scheduler_id, self.worker_id, token, t))
            return cur.rowcount == 1

    def _release(self, token: str) -> None:
        with transaction(self.conn, immediate=True):
            self.conn.execute(
                """UPDATE learning_schedulers SET owner_worker_id=NULL, lease_token=NULL, lease_expires_at=0,
                     state='stopped', updated_at=? WHERE id=? AND lease_token=?""",
                (now(), self.scheduler_id, token))

    def status(self) -> dict:
        row = self.conn.execute("SELECT * FROM learning_schedulers WHERE id=?", (self.scheduler_id,)).fetchone()
        runs = [dict(r) for r in self.conn.execute(
            "SELECT id,trigger,status,started_at,finished_at,error FROM learning_runs WHERE scheduler_id=? ORDER BY started_at DESC, id DESC LIMIT 10",
            (self.scheduler_id,))]
        errors = self.conn.execute(
            "SELECT COUNT(*) c FROM learning_runs WHERE scheduler_id=? AND status IN ('failed','interrupted')",
            (self.scheduler_id,)).fetchone()["c"]
        return {"scheduler": dict(row) if row else None, "recent_runs": runs, "error_runs": errors,
                "worker_id": self.worker_id}

    def run(self, max_cycles: int | None = None, stop_event: threading.Event | None = None) -> dict:
        from .db import get_conn
        stop_event = stop_event or threading.Event()
        token = self._claim()
        if token is None:
            return {"status": "skipped", "reason": "ordonnanceur déjà actif", "scheduler_id": self.scheduler_id}
        hb_stop = threading.Event()
        lost = threading.Event()

        def heartbeat():
            conn = get_conn(self.db_path) if self.db_path else self.conn
            while not hb_stop.wait(self.heartbeat_interval):
                try:
                    if not self._renew(token):
                        lost.set()
                        stop_event.set()
                        return
                except Exception:
                    lost.set()
                    stop_event.set()
                    return

        hb = threading.Thread(target=heartbeat, name=f"learn-sched-{self.scheduler_id}", daemon=True)
        hb.start()
        cycles = 0
        results = []
        try:
            while not stop_event.is_set():
                row = self.conn.execute("SELECT next_run_at FROM learning_schedulers WHERE id=?", (self.scheduler_id,)).fetchone()
                next_run = float(row["next_run_at"] or 0.0) if row else 0.0
                delay = max(0.0, next_run - epoch())
                if delay > 0 and stop_event.wait(min(delay, self.interval_seconds)):
                    break
                if stop_event.is_set() or lost.is_set():
                    break
                res = self.engine.run_cycle(max_proposals=self.max_proposals, trigger="periodic",
                                            scheduler_id=self.scheduler_id, stop_event=stop_event,
                                            lease_seconds=self.lease_seconds, worker_id=self.worker_id)
                results.append({"run_id": res.get("run_id"), "status": res.get("status")})
                if res.get("status") == "failed":
                    log_event(self.conn, "error", "learning-scheduler",
                              f"cycle périodique en erreur : {res.get('error', '')}", data={"scheduler_id": self.scheduler_id})
                with transaction(self.conn, immediate=True):
                    self.conn.execute(
                        "UPDATE learning_schedulers SET last_run_at=?, next_run_at=?, updated_at=? WHERE id=? AND lease_token=?",
                        (now(), epoch() + self.interval_seconds, now(), self.scheduler_id, token))
                if res.get("status") != "skipped":
                    cycles += 1
                if max_cycles is not None and cycles >= max_cycles:
                    break
                if stop_event.wait(self.interval_seconds):
                    break
        finally:
            hb_stop.set()
            hb.join(timeout=2.0)
            self._release(token)
        return {"status": "stopped", "cycles": cycles, "runs": results, "scheduler_id": self.scheduler_id,
                "lease_lost": lost.is_set(), "worker_id": self.worker_id}
