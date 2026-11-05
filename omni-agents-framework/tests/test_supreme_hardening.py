"""Durcissement SUPREME 1.2.1 — tests LOCAUX RÉELS de concurrence, crash,
apprentissage périodique et budget strict. Aucun fournisseur IA réel, aucun cloud.

Catégories :
- multi-processus SQLite / subprocess / SIGKILL / SIGTERM : local réel ;
- HTTP contre stub 127.0.0.1 : local réel (pas un fournisseur IA réel) ;
- fixtures d'analyses du conseil : simulé, explicitement séparé dans test_supreme_router.
"""
from __future__ import annotations

import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

import supreme.learning as L
from supreme.budget import BudgetController
from supreme.council import Council, CouncilConfig
from supreme.db import connect, epoch, init_db, transaction
from supreme.evaluation import EvaluationEngine
from supreme.leases import LeaseLostError, claim_next, complete_mission, recover_abandoned
from supreme.orchestrator import OmniBrainCore
from supreme.providers import ProviderClient
from supreme.registry import Registry
from supreme.router import ModelRouter, ModelSpec, Provider
from tests._supreme_util import SupremeTestCase
from tests.test_supreme_providers import _clean_env, start_stub

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent


def _tool_agent(core, division="D02"):
    for a in core.registry.list(division=division, kind="specialist"):
        rep = next(e for e in a["profile"]["eval_tests"] if e["id"] == "representative")
        if rep["mode"] == "tool":
            return a
    raise AssertionError("aucun agent outil")


class TestSchemaMigration(unittest.TestCase):
    def test_v1_to_v2_migration_is_additive(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "old.db"
            conn = connect(db)
            conn.executescript("""
                CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                INSERT INTO schema_meta(key,value) VALUES('version','1');
                CREATE TABLE missions (
                    id TEXT PRIMARY KEY, objective TEXT NOT NULL, state TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 5, plan_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    budget_usd REAL NOT NULL DEFAULT 0.05, privacy TEXT NOT NULL DEFAULT 'standard', result_json TEXT
                );
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY, mission_id TEXT NOT NULL REFERENCES missions(id), agent_id TEXT NOT NULL,
                    tool TEXT, input_json TEXT NOT NULL DEFAULT '{}', state TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0, result_json TEXT, error TEXT,
                    idempotency_key TEXT UNIQUE, depends_on TEXT NOT NULL DEFAULT '[]',
                    timeout_s INTEGER NOT NULL DEFAULT 120, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE budget_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, scope TEXT NOT NULL, scope_id TEXT NOT NULL,
                    mission_id TEXT, provider TEXT, model TEXT, tokens_in INTEGER NOT NULL DEFAULT 0,
                    tokens_out INTEGER NOT NULL DEFAULT 0, cost_usd REAL NOT NULL DEFAULT 0, at TEXT NOT NULL
                );
                INSERT INTO missions(id,objective,state,created_at,updated_at) VALUES('m-old','ancienne mission','completed','t','t');
                INSERT INTO tasks(id,mission_id,agent_id,tool,state,idempotency_key,created_at,updated_at)
                    VALUES('t-old','m-old','a-old','json_validate','done','k-old','t','t');
                INSERT INTO budget_ledger(scope,scope_id,cost_usd,at) VALUES('mission','m-old',0.0,'t');
            """)
            conn.commit()
            init_db(conn)
            mcols = {r[1] for r in conn.execute("PRAGMA table_info(missions)")}
            tcols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)")}
            bcols = {r[1] for r in conn.execute("PRAGMA table_info(budget_ledger)")}
            self.assertTrue({"owner_worker_id", "lease_token", "lease_expires_at", "fencing_token"} <= mcols)
            self.assertTrue({"execution_token", "owner_worker_id"} <= tcols)
            self.assertTrue({"reservation_id", "call_key"} <= bcols)
            self.assertEqual(conn.execute("SELECT objective FROM missions WHERE id='m-old'").fetchone()[0], "ancienne mission")
            self.assertEqual(conn.execute("SELECT state FROM tasks WHERE id='t-old'").fetchone()[0], "done")
            self.assertEqual(conn.execute("SELECT value FROM schema_meta WHERE key='version'").fetchone()[0], "3")
            self.assertIsNotNone(conn.execute("SELECT name FROM sqlite_master WHERE name='activation_campaigns'").fetchone())
            conn.close()


class TestMultiProcessWorkers(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.var = Path(self._tmp.name)
        self.db_path = self.var / "supreme.db"
        self.conn = connect(self.db_path)
        init_db(self.conn)
        self.core = OmniBrainCore(conn=self.conn)
        self.core.registry.sync_catalog()
        agent = _tool_agent(self.core)
        sub = self.core.submit({"objective": "mission concurrence réelle", "tasks": [
            {"agent_id": agent["id"], "tool": "json_validate", "input": {"json": "{}"}}]})
        self.mid = sub["mission_id"]

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()

    def _env(self, **extra):
        env = _clean_env()
        env.update({"SUPREME_VAR_DIR": str(self.var), "PYTHONPATH": str(FRAMEWORK_ROOT)})
        env.update(extra)
        return env

    def _wait_marker(self, proc, timeout=20):
        marker = self.var / "tool-starts.jsonl"
        deadline = time.time() + timeout
        while time.time() < deadline:
            if marker.is_file() and marker.read_text().strip():
                return
            if proc.poll() is not None:
                out, err = proc.communicate()
                raise AssertionError(f"worker sorti avant démarrage: {out[-500:]} {err[-500:]}")
            time.sleep(0.05)
        raise AssertionError("marker de démarrage non produit")

    def _state(self):
        return self.core.status(self.mid)

    def test_worker_b_starts_during_a_without_double_execution(self):
        a = subprocess.Popen([sys.executable, "-m", "tests._supreme_worker_helper"],
                             cwd=FRAMEWORK_ROOT, env=self._env(TEST_WORKER_ID="worker-A", TEST_SLOW_SECONDS="4",
                                                                TEST_LEASE_SECONDS="30", TEST_HEARTBEAT_SECONDS="0.2"),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self._wait_marker(a)
            b = subprocess.run([sys.executable, "-m", "supreme", "worker", "--once", "--worker-id", "worker-B",
                                "--lease-seconds", "30", "--heartbeat-seconds", "0.2"],
                               cwd=FRAMEWORK_ROOT, env=self._env(), capture_output=True, text=True, timeout=60)
            self.assertEqual(b.returncode, 0, b.stderr[-800:])
            bout = json.loads(b.stdout)
            self.assertEqual(bout["processed"], 0)  # B ne vole pas la mission active de A
            aout, aerr = a.communicate(timeout=30)
            self.assertEqual(a.returncode, 0, aerr[-800:])
            self.assertEqual(json.loads(aout)["processed"], 1)
        finally:
            if a.poll() is None:
                a.kill()
                a.communicate()
        st = self._state()
        self.assertEqual(st["state"], "completed")
        self.assertEqual(st["run_attempts"], 1)
        executions = self.conn.execute("SELECT COUNT(*) c FROM task_executions WHERE mission_id=?", (self.mid,)).fetchone()["c"]
        metrics = self.conn.execute("SELECT COUNT(*) c FROM metrics WHERE mission_id=? AND name='task_success'", (self.mid,)).fetchone()["c"]
        starts = len((self.var / "tool-starts.jsonl").read_text().splitlines())
        self.assertEqual(executions, 1)
        self.assertEqual(metrics, 1)
        self.assertEqual(starts, 1)

    def test_sigkill_crash_then_restart_completes_once(self):
        a = subprocess.Popen([sys.executable, "-m", "tests._supreme_worker_helper"],
                             cwd=FRAMEWORK_ROOT, env=self._env(TEST_WORKER_ID="worker-crash", TEST_SLOW_SECONDS="5",
                                                                TEST_LEASE_SECONDS="1", TEST_HEARTBEAT_SECONDS="0.2"),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self._wait_marker(a)
            os.kill(a.pid, signal.SIGKILL)
            a.communicate(timeout=10)
        finally:
            if a.poll() is None:
                a.kill()
                a.communicate()
        row = self.conn.execute("SELECT lease_expires_at FROM missions WHERE id=?", (self.mid,)).fetchone()
        deadline = time.time() + 10
        while epoch() <= float(row["lease_expires_at"]) + 0.1 and time.time() < deadline:
            time.sleep(0.05)
        b = subprocess.run([sys.executable, "-m", "supreme", "worker", "--once", "--worker-id", "worker-restart",
                            "--lease-seconds", "1", "--heartbeat-seconds", "0.2"],
                           cwd=FRAMEWORK_ROOT, env=self._env(), capture_output=True, text=True, timeout=60)
        self.assertEqual(b.returncode, 0, b.stderr[-800:])
        self.assertEqual(json.loads(b.stdout)["processed"], 1)
        st = self._state()
        self.assertEqual(st["state"], "completed")
        self.assertEqual(st["run_attempts"], 2)
        executions = self.conn.execute("SELECT COUNT(*) c FROM task_executions WHERE mission_id=?", (self.mid,)).fetchone()["c"]
        self.assertEqual(executions, 1)  # un seul résultat commité malgré le crash
        self.assertGreaterEqual(st["tasks"][0]["attempts"], 1)  # la tâche a bien été reprise et exécutée

    def test_sigterm_graceful_requeues_then_restart(self):
        a = subprocess.Popen([sys.executable, "-m", "tests._supreme_worker_helper"],
                             cwd=FRAMEWORK_ROOT, env=self._env(TEST_WORKER_ID="worker-graceful", TEST_SLOW_SECONDS="3",
                                                                TEST_LEASE_SECONDS="30", TEST_HEARTBEAT_SECONDS="0.2"),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self._wait_marker(a)
            os.kill(a.pid, signal.SIGTERM)
            aout, aerr = a.communicate(timeout=20)
            self.assertEqual(a.returncode, 0, aerr[-800:])
            self.assertEqual(json.loads(aout)["missions"][0]["state"], "interrupted")
        finally:
            if a.poll() is None:
                a.kill()
                a.communicate()
        self.assertEqual(self._state()["state"], "planned")
        b = subprocess.run([sys.executable, "-m", "supreme", "worker", "--once", "--worker-id", "worker-after-term"],
                           cwd=FRAMEWORK_ROOT, env=self._env(), capture_output=True, text=True, timeout=60)
        self.assertEqual(b.returncode, 0, b.stderr[-800:])
        self.assertEqual(json.loads(b.stdout)["processed"], 1)
        self.assertEqual(self._state()["state"], "completed")
        executions = self.conn.execute("SELECT COUNT(*) c FROM task_executions WHERE mission_id=?", (self.mid,)).fetchone()["c"]
        self.assertEqual(executions, 1)


class TestLeaseFencing(SupremeTestCase):
    def test_active_lease_not_recovered_and_stale_owner_fenced(self):
        self.core.submit({"objective": "Vérifier Python"})
        lease_a = claim_next(self.conn, "worker-A", lease_seconds=30)
        self.assertIsNotNone(lease_a)
        conn2 = connect(self.db_path)
        core2 = OmniBrainCore(conn=conn2)
        self.assertEqual(core2.recover()["recovered_missions"], 0)
        self.assertEqual(self.core.status(lease_a.mission_id)["owner_worker_id"], "worker-A")
        # Simule l'expiration réelle du bail et le silence du worker A.
        with transaction(self.conn, immediate=True):
            self.conn.execute("UPDATE missions SET lease_expires_at=? WHERE id=?", (epoch() - 1, lease_a.mission_id))
            self.conn.execute("UPDATE workers SET last_heartbeat=? WHERE worker_id='worker-A'", (epoch() - 2,))
        lease_b = claim_next(conn2, "worker-B", lease_seconds=30)
        self.assertIsNotNone(lease_b)
        self.assertGreater(lease_b.fencing_token, lease_a.fencing_token)
        with self.assertRaises(LeaseLostError):
            complete_mission(self.conn, lease_a, "completed", {"state": "completed"})
        self.assertEqual(self.core.status(lease_a.mission_id)["owner_worker_id"], "worker-B")
        conn2.close()


class TestLearningHardening(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.var = Path(self._tmp.name) / "learning-var"
        self._patch_var = mock.patch.object(L, "VAR_DIR", self.var)
        self._patch_dirs = mock.patch.object(L, "ensure_dirs", lambda: None)
        self._patch_var.start()
        self._patch_dirs.start()
        self.engine = L.LearningEngine(self.conn, self.core.registry,
                                       EvaluationEngine(self.conn, self.core.registry))

    def tearDown(self):
        self._patch_dirs.stop()
        self._patch_var.stop()
        super().tearDown()

    def test_run_cycle_persists_report(self):
        res = self.engine.run_cycle()
        self.assertEqual(res["status"], "completed")
        self.assertTrue(Path(res["persisted_to"]).is_file())
        row = self.conn.execute("SELECT status, report_json FROM learning_runs WHERE id=?", (res["run_id"],)).fetchone()
        self.assertEqual(row["status"], "completed")
        self.assertIn("steps", json.loads(row["report_json"]))

    def test_two_cycles_cannot_run_simultaneously(self):
        started = threading.Event()
        release = threading.Event()
        original = self.engine.collect_outcomes
        def blocked():
            started.set()
            release.wait(10)
            return original()
        self.engine.collect_outcomes = blocked
        results = []
        t = threading.Thread(target=lambda: results.append(self.engine.run_cycle()))
        t.start()
        self.assertTrue(started.wait(5))
        conn2 = connect(self.db_path)
        reg2 = Registry(conn2)
        engine2 = L.LearningEngine(conn2, reg2, EvaluationEngine(conn2, reg2))
        skipped = engine2.run_cycle()
        conn2.close()
        self.assertEqual(skipped["status"], "skipped")
        release.set()
        t.join(timeout=10)
        self.assertEqual(results[0]["status"], "completed")
        running = self.conn.execute("SELECT COUNT(*) c FROM learning_runs WHERE status='running'").fetchone()["c"]
        self.assertEqual(running, 0)

    def test_periodic_scheduler_bounded_and_persistent(self):
        sched = L.LearningScheduler(self.conn, self.engine, interval_seconds=0.05,
                                    lease_seconds=1, heartbeat_interval=0.1)
        res = sched.run(max_cycles=2)
        self.assertEqual(res["status"], "stopped")
        self.assertEqual(res["cycles"], 2)
        rows = self.conn.execute("SELECT status, report_json FROM learning_runs ORDER BY started_at").fetchall()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["status"] == "completed" for r in rows))
        self.assertEqual(len(list((self.var / "learning").glob("*.json"))), 2)
        self.assertEqual(sched.status()["scheduler"]["state"], "stopped")

    def test_scheduler_lease_exclusive(self):
        s1 = L.LearningScheduler(self.conn, self.engine, scheduler_id="excl", interval_seconds=1,
                                 lease_seconds=30, worker_id="sched-1")
        s2 = L.LearningScheduler(self.conn, self.engine, scheduler_id="excl", interval_seconds=1,
                                 lease_seconds=30, worker_id="sched-2")
        token = s1._claim()
        self.assertIsNotNone(token)
        self.assertEqual(s2.run(max_cycles=1)["status"], "skipped")
        s1._release(token)

    def test_error_is_persisted_and_surveilled(self):
        with mock.patch.object(self.engine, "collect_outcomes", side_effect=RuntimeError("erreur test")):
            res = self.engine.run_cycle()
        self.assertEqual(res["status"], "failed")
        self.assertIn("erreur test", res["error"])
        self.assertTrue(Path(res["persisted_to"]).is_file())
        sched = L.LearningScheduler(self.conn, self.engine)
        self.assertEqual(sched.status()["error_runs"], 1)

    def test_expired_cycle_is_interrupted_then_resumed(self):
        with transaction(self.conn, immediate=True):
            self.conn.execute(
                """INSERT INTO learning_runs(id,scheduler_id,trigger,worker_id,lease_token,status,
                     started_at,heartbeat_at,lease_expires_at) VALUES(?,?,?,?,?,'running',?,?,?)""",
                ("lr-expired", "default", "periodic", "dead", "tok", L.now(), epoch() - 10, epoch() - 5))
        res = self.engine.run_cycle()
        self.assertEqual(res["status"], "completed")
        old = self.conn.execute("SELECT status FROM learning_runs WHERE id='lr-expired'").fetchone()
        self.assertEqual(old["status"], "interrupted")


class TestCliLearningPeriodic(unittest.TestCase):
    def test_cli_periodic_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = _clean_env()
            env.update({"SUPREME_VAR_DIR": tmp, "PYTHONPATH": str(FRAMEWORK_ROOT)})
            proc = subprocess.run([sys.executable, "-m", "supreme", "learn", "--periodic",
                                   "--interval", "0.05", "--max-cycles", "2",
                                   "--lease-seconds", "1", "--heartbeat-seconds", "0.1"],
                                  cwd=FRAMEWORK_ROOT, env=env, capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr[-800:])
            out = json.loads(proc.stdout)
            self.assertEqual(out["cycles"], 2)
            self.assertEqual(out["status"], "stopped")

    def test_cli_periodic_sigterm_clean_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = _clean_env()
            env.update({"SUPREME_VAR_DIR": tmp, "PYTHONPATH": str(FRAMEWORK_ROOT)})
            proc = subprocess.Popen([sys.executable, "-m", "supreme", "learn", "--periodic",
                                     "--interval", "10", "--lease-seconds", "2", "--heartbeat-seconds", "0.2"],
                                    cwd=FRAMEWORK_ROOT, env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True)
            db = Path(tmp) / "supreme.db"
            deadline = time.time() + 60
            seen = False
            while time.time() < deadline:
                if db.is_file():
                    c = sqlite3.connect(db)
                    try:
                        n = c.execute("SELECT COUNT(*) FROM learning_runs WHERE status='completed'").fetchone()[0]
                    except sqlite3.OperationalError:
                        n = 0
                    c.close()
                    if n >= 1:
                        seen = True
                        break
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
            self.assertTrue(seen, "aucun cycle périodique produit")
            os.kill(proc.pid, signal.SIGTERM)
            out, err = proc.communicate(timeout=30)
            self.assertEqual(proc.returncode, 0, err[-800:])
            res = json.loads(out)
            self.assertEqual(res["status"], "stopped")
            self.assertGreaterEqual(res["cycles"], 1)


class TestCouncilBudgetHardening(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.server, self.thread, self.base = start_stub()
        self.budget = self.core.budget

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def _provider(self, name="mistral", rate=0.001, context=8000):
        return Provider(name, f"{name.upper()}_STUB_KEY", self.base, [
            ModelSpec(name, f"{name}-model", ("general",), rate, rate, context, True, True)],
            kind="openai", priority=1)

    def _env(self, providers):
        env = _clean_env()
        for p in providers:
            env[p.env_var] = "stub-secret-123"
        return env

    def test_reservation_exists_before_http_call(self):
        p = self._provider()
        real = ProviderClient(timeout=10)
        seen = []
        def checking(**kwargs):
            seen.append(self.conn.execute("SELECT COUNT(*) c FROM budget_reservations WHERE status='reserved'").fetchone()["c"])
            return real.complete(**kwargs)
        client = mock.Mock()
        client.complete.side_effect = checking
        self.budget.set_quota("mission", "m-reserve", 1.0)
        with mock.patch.dict(os.environ, self._env([p]), clear=True):
            router = ModelRouter(conn=self.conn, providers=[p], budget=self.budget, client=client)
            res = router.complete({"capabilities": ["general"], "max_cost_usd": 1.0},
                                  [{"role": "user", "content": "x"}], mission_id="m-reserve")
        self.assertTrue(res["ok"], res["error"])
        self.assertGreaterEqual(seen[0], 1)
        row = self.conn.execute("SELECT status FROM budget_reservations WHERE id=?", (res["reservation_id"],)).fetchone()
        self.assertEqual(row["status"], "settled")
        self.assertGreater(self.budget.mission_cost("m-reserve"), 0.0)

    def test_individual_budget_blocks_before_http(self):
        p = self._provider()
        with mock.patch.dict(os.environ, self._env([p]), clear=True):
            router = ModelRouter(conn=self.conn, providers=[p], budget=self.budget)
            res = router.complete({"capabilities": ["general"], "max_cost_usd": 0.005},
                                  [{"role": "user", "content": "x" * 5000}], max_tokens=1024)
        self.assertFalse(res["ok"])
        self.assertFalse(any(r["method"] == "POST" for r in self.server.requests))
        self.assertTrue(any(a.get("skipped") for a in res["attempts"]))

    def test_collective_council_budget_stops_after_affordable_models(self):
        providers = [self._provider(name, rate=0.01) for name in ("mistral", "groq", "deepseek")]
        with mock.patch.dict(os.environ, self._env(providers), clear=True):
            router = ModelRouter(conn=self.conn, providers=providers, budget=self.budget)
            res = Council(router, CouncilConfig(max_models=3, max_cost_usd=0.035, max_tokens=600)).deliberate("p")
        posts = [r for r in self.server.requests if r["method"] == "POST"]
        self.assertEqual(res["status"], "needs_review")
        self.assertEqual(len(posts), 1)
        self.assertLessEqual(res["budget_reserved_bound_usd"], res["budget_max_usd"] + 1e-12)
        self.assertTrue(any("budget collectif restant" in e["error"] for e in res["errors"]))

    def test_central_quota_blocks_council(self):
        p = self._provider()
        self.budget.set_quota("mission", "m-council", 1e-9)
        with mock.patch.dict(os.environ, self._env([p]), clear=True):
            router = ModelRouter(conn=self.conn, providers=[p], budget=self.budget)
            res = Council(router).deliberate("p", mission_id="m-council")
        self.assertEqual(res["status"], "unavailable")
        self.assertFalse(any(r["method"] == "POST" for r in self.server.requests))

    def test_uncertain_500_holds_reservation_but_401_releases(self):
        p = self._provider()
        self.budget.set_quota("mission", "m-500", 1.0)
        self.server.mode = "500"
        with mock.patch.dict(os.environ, self._env([p]), clear=True):
            router = ModelRouter(conn=self.conn, providers=[p], budget=self.budget)
            res = router.complete({"capabilities": ["general"], "max_cost_usd": 1.0},
                                  [{"role": "user", "content": "x"}], mission_id="m-500")
        self.assertFalse(res["ok"])
        self.assertGreater(self.budget.reserved("mission", "m-500"), 0.0)
        self.assertEqual(self.budget.mission_cost("m-500"), 0.0)
        self.server.mode = "401"
        self.budget.set_quota("mission", "m-401", 1.0)
        with mock.patch.dict(os.environ, self._env([p]), clear=True):
            router = ModelRouter(conn=self.conn, providers=[p], budget=self.budget)
            res2 = router.complete({"capabilities": ["general"], "max_cost_usd": 1.0},
                                   [{"role": "user", "content": "x"}], mission_id="m-401")
        self.assertFalse(res2["ok"])
        self.assertEqual(self.budget.reserved("mission", "m-401"), 0.0)

    def test_token_limits_block_before_http(self):
        p = self._provider(context=10)
        with mock.patch.dict(os.environ, self._env([p]), clear=True):
            router = ModelRouter(conn=self.conn, providers=[p], budget=self.budget)
            r0 = router.complete({"capabilities": ["general"], "max_cost_usd": 1.0},
                                 [{"role": "user", "content": "x"}], max_tokens=0)
            r1 = router.complete({"capabilities": ["general"], "max_cost_usd": 1.0},
                                 [{"role": "user", "content": "x"}], max_tokens=5)
        self.assertFalse(r0["ok"])
        self.assertFalse(r1["ok"])
        self.assertFalse(any(r["method"] == "POST" for r in self.server.requests))

    def test_concurrent_reservations_cannot_overspend_global_quota(self):
        self.budget.set_quota("global", "default", 0.001)
        def reserve_one(_):
            conn = connect(self.db_path)
            b = BudgetController(conn)
            res = b.reserve([("global", "default")], 0.0006, mission_id="m-race")
            conn.close()
            return res.get("reserved", False)
        with ThreadPoolExecutor(max_workers=2) as ex:
            results = list(ex.map(reserve_one, range(2)))
        self.assertEqual(sum(results), 1)
        self.assertLessEqual(self.budget.exposure("global", "default"), 0.001 + 1e-12)


if __name__ == "__main__":
    unittest.main()
