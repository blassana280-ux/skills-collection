"""Opérations SUPREME : worker séparé (Phase G), audit exécutable (Phase I),
cycle d'amélioration contrôlée (Phase 13). Tous des tests LOCAUX RÉELS.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from supreme.db import connect, init_db, transaction
from supreme.orchestrator import OmniBrainCore
from supreme.worker import claim_next_mission, run_worker
from supreme.audit import run_audit
from supreme.learning import LearningEngine
from supreme.evaluation import EvaluationEngine
from tests._supreme_util import SupremeTestCase

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent


class TestWorker(SupremeTestCase):
    def test_worker_processes_queued_mission(self):
        sub = self.core.submit({"objective": "Vérifier Python JSON", "run": False})
        # Un worker avec sa PROPRE connexion (même base) revendique et exécute.
        conn2 = connect(self.db_path)
        worker_core = OmniBrainCore(conn=conn2)
        res = run_worker(once=True, core=worker_core)
        conn2.close()
        self.assertEqual(res["processed"], 1)
        self.assertEqual(res["missions"][0]["state"], "completed")
        self.assertEqual(self.core.status(sub["mission_id"])["state"], "completed")

    def test_claim_is_atomic(self):
        self.core.submit({"objective": "Vérifier Python", "run": False})
        conn2 = connect(self.db_path)
        core2 = OmniBrainCore(conn=conn2)
        mid1 = claim_next_mission(self.core)
        mid2 = claim_next_mission(core2)
        conn2.close()
        self.assertIsNotNone(mid1)
        self.assertIsNone(mid2)  # pas de double exécution possible

    def test_worker_empty_queue(self):
        res = run_worker(once=True, core=self.core)
        self.assertEqual(res["processed"], 0)

    def test_worker_real_subprocess(self):
        """VRAI processus séparé : `python3 -m supreme worker --once` sur la même base."""
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "supreme.db"
            conn = connect(db)
            init_db(conn)
            core = OmniBrainCore(conn=conn)
            core.registry.sync_catalog()
            sub = core.submit({"objective": "Vérifier Python JSON secrets", "run": False})
            env = {**os.environ, "SUPREME_VAR_DIR": tmp}
            proc = subprocess.run([sys.executable, "-m", "supreme", "worker", "--once"],
                                  cwd=FRAMEWORK_ROOT, env=env, capture_output=True,
                                  text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
            out = json.loads(proc.stdout)
            state = core.status(sub["mission_id"])["state"]
            conn.close()
        self.assertEqual(out["processed"], 1)
        self.assertEqual(state, "completed")


class TestAudit(SupremeTestCase):
    def test_audit_structure_and_ok(self):
        report = run_audit(save=False, conn=self.conn)
        self.assertTrue(report["catalog"]["ok"], report["catalog"]["validation_errors"][:3])
        self.assertEqual(report["catalog"]["specialists"], 1000)
        self.assertEqual(report["catalog"]["managers"], 20)
        self.assertTrue(report["catalog"]["per_division_ok"])
        self.assertTrue(report["security"]["ok"], report["security"])
        self.assertFalse(report["security"]["code_prints_token"])
        self.assertGreater(report["tests_discovered"], 250)
        self.assertIn("distinctions", report)
        self.assertTrue(report["ok"])

    def test_audit_saves_report(self):
        import supreme.audit as audit_mod
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(audit_mod, "VAR_DIR", Path(tmp)):
                report = run_audit(save=True, conn=self.conn)
                self.assertIn("saved_to", report)
                self.assertTrue(Path(report["saved_to"]).is_file())
                saved = json.loads(Path(report["saved_to"]).read_text())
                self.assertEqual(saved["catalog"]["specialists"], 1000)


class TestLearningCycle(SupremeTestCase):
    def _seed_failures(self, agent_id):
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO missions(id,objective,state,priority,plan_json,created_at,updated_at,budget_usd,privacy) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                ("m-fail", "mission en échec", "failed", 5, "{}", "2026-11-05", "2026-11-05", 0.05, "standard"))
            for i in range(2):
                self.conn.execute("INSERT INTO metrics(agent_id,name,value,at) VALUES(?,?,?,?)",
                                  (agent_id, "task_success", 0, f"2026-11-05T00:00:0{i}"))
                self.conn.execute(
                    "INSERT INTO tasks(id,mission_id,agent_id,tool,input_json,state,error,depends_on,timeout_s,idempotency_key,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (f"t-fail-{i}", "m-fail", agent_id, "json_validate", "{}", "failed",
                     "entrée invalide récurrente", "[]", 10, f"k{i}", "2026-11-05", "2026-11-05"))

    def test_cycle_observes_proposes_compares(self):
        agent = self.tool_agent("D02")
        self._seed_failures(agent["id"])
        le = LearningEngine(self.conn, self.core.registry,
                            EvaluationEngine(self.conn, self.core.registry))
        report = le.run_cycle()
        self.assertEqual(report["steps"][0]["name"], "observer")
        evaluated = next(step["evaluated"] for step in report["steps"] if "evaluated" in step)
        accepted = [e for e in evaluated if e["status"] == "accepted"]
        self.assertTrue(accepted, evaluated)  # gain mesuré sur outil réel -> accepté
        self.assertEqual(accepted[0]["target"], agent["id"])
        self.assertEqual(report["step_10_pr"]["status"], "human_required")
        self.assertIn("noyau intact", report["guarantees"])
        # la stratégie est versionnée et active
        row = self.conn.execute("SELECT * FROM strategies WHERE agent_id=? AND active=1",
                                (agent["id"],)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["score"], 1.0)

    def test_cycle_no_data_no_crash(self):
        le = LearningEngine(self.conn, self.core.registry,
                            EvaluationEngine(self.conn, self.core.registry))
        report = le.run_cycle()
        self.assertIsNone(report["steps"][0]["task_success_rate"])
        self.assertEqual(next(step["evaluated"] for step in report["steps"] if "evaluated" in step), [])

    def test_cycle_never_touches_core(self):
        le = LearningEngine(self.conn, self.core.registry,
                            EvaluationEngine(self.conn, self.core.registry))
        with self.assertRaises(PermissionError):
            le.propose_strategy("omnibrain-core", "modification interdite")


if __name__ == "__main__":
    unittest.main()
