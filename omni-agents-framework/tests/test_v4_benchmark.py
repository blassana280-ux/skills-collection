"""Phase 4.2 — 10 tâches figées, gains mesurés, historisation."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests import ROOT
from omni.memory.store import MemoryStore
from tools.benchmark import (
    BENCHMARK_TASKS,
    compute_gains,
    read_history,
    run_benchmark,
    run_once,
    task_fingerprint,
)


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.history = Path(self.tmp.name) / "history.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_ten_frozen_tasks_with_stable_fingerprint(self):
        self.assertEqual(len(BENCHMARK_TASKS), 10)
        ids = [t.id for t in BENCHMARK_TASKS]
        self.assertEqual(len(set(ids)), 10)
        self.assertEqual(len(task_fingerprint()), 64)
        self.assertEqual(task_fingerprint(), task_fingerprint())
        for task in BENCHMARK_TASKS:
            self.assertTrue(task.query.strip())
            self.assertTrue(task.expected_id)

    def test_real_router_hits_all_expected_agents(self):
        result = run_once(ROOT)
        self.assertEqual(result["tasks"], 10)
        self.assertEqual(result["hits"], 10)
        self.assertEqual(result["hit_rate"], 1.0)
        self.assertEqual(result["wave_count"], 1)
        self.assertEqual(len(result["details"]), 10)
        self.assertTrue(all(d["hit"] for d in result["details"]))
        self.assertGreater(result["mean_latency_ms"], 0)

    def test_history_is_appended_and_gains_are_computed(self):
        store = MemoryStore(Path(self.tmp.name) / "bench.sqlite3")
        try:
            first = run_benchmark(runs=1, history_path=self.history, store=store)
            self.assertIsNone(first["record"]["gains"]["baseline"])
            second = run_benchmark(runs=2, history_path=self.history, store=store)
            history = read_history(self.history)
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0]["fingerprint"], history[1]["fingerprint"])
            self.assertIsNotNone(second["record"]["gains"]["baseline"])
            self.assertEqual(second["record"]["gains"]["runs_in_history"], 1)
            self.assertEqual(second["passes"], 2)
            self.assertEqual(store.stats()["benchmarks"], 2)
        finally:
            store.close()

    def test_gain_computation_direction(self):
        baseline = {"fingerprint": "abc", "metrics": {"hit_rate": 0.8, "mean_latency_ms": 100.0, "measured_at": "t0"}}
        current = {"fingerprint": "abc", "hit_rate": 0.9, "mean_latency_ms": 50.0}
        gains = compute_gains(current, [baseline])
        self.assertEqual(gains["gain_latency_pct"], 50.0)
        self.assertAlmostEqual(gains["gain_hit_rate_pp"], 10.0)
        self.assertIsNone(compute_gains(current, [])["baseline"])

    def test_no_write_keeps_history_clean_and_cli_green(self):
        run_benchmark(runs=1, history_path=self.history, write=False)
        self.assertFalse(self.history.exists())
        proc = subprocess.run(
            [sys.executable, "tools/benchmark.py", "--no-write", "--history", str(self.history)],
            cwd=ROOT, capture_output=True, text=True, timeout=90,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["hit_rate"], 1.0)
        self.assertFalse(self.history.exists())


if __name__ == "__main__":
    unittest.main()
