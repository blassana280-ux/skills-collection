"""Phase 2.3 — boucle GEPA : réflexion en base, journal de chaque itération."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests import ROOT
from omni.memory.store import MemoryStore
from tools.optimize_prompts import BASE_PROMPT, PromptOptimizer


class OptimizePromptsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "gepa.sqlite3"
        self.journal = Path(self.tmp.name) / "iterations.jsonl"
        self.store = MemoryStore(self.db)
        mid = self.store.record_mission({"project_type": "gepa", "title": "Optimisation", "verdict": "PASS"})
        self.store.record_result(mid, "agent-a", status="ok", verdict="PASS")
        self.store.record_failure(mid, "agent-a", "agent-a", "timeout", "trop lent")
        self.store.record_failure(mid, "agent-b", "agent-b", "missing_keyword", "mot-clé absent")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_every_iteration_is_journalised_and_accepted_only_on_gain(self):
        result = PromptOptimizer(self.store, "gepa", self.journal).optimize(3)
        lines = [json.loads(line) for line in self.journal.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(lines), 3)
        self.assertEqual([line["iteration"] for line in lines], [1, 2, 3])
        for line in lines:
            self.assertIn("score_before", line)
            self.assertIn("score_after", line)
            self.assertIn("accepted", line)
            self.assertIn("rationale", line)
            self.assertIn("evidence", line)
            self.assertEqual(line["project_type"], "gepa")
        self.assertEqual(len(self.store.prompt_iterations("gepa")), 3)
        self.assertGreaterEqual(result["accepted"], 1)
        self.assertGreater(result["final_score"], result["initial_score"])
        self.assertIn("RÈGLE GEPA", result["prompt"])
        scores = [line["score_after"] for line in lines]
        self.assertEqual(scores, sorted(scores))
        self.assertTrue(self.store.logs())

    def test_no_failure_still_produces_a_deterministic_trace(self):
        empty = MemoryStore(":memory:")
        try:
            journal = Path(self.tmp.name) / "empty.jsonl"
            result = PromptOptimizer(empty, "vide", journal).optimize(2)
            self.assertEqual(len(journal.read_text(encoding="utf-8").splitlines()), 2)
            self.assertEqual(result["initial_score"], 0.0)
            self.assertIn("RÈGLE GEPA-08", result["prompt"])
        finally:
            empty.close()

    def test_cli_exits_zero_and_writes_journal(self):
        proc = subprocess.run(
            [sys.executable, "tools/optimize_prompts.py", "--project-type", "gepa",
             "--iterations", "2", "--db", str(self.db), "--journal", str(Path(self.tmp.name) / "cli.jsonl")],
            cwd=ROOT, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["iterations"], 2)
        self.assertEqual(len((Path(self.tmp.name) / "cli.jsonl").read_text(encoding="utf-8").splitlines()), 2)

    def test_score_covers_each_observed_error_type(self):
        optimizer = PromptOptimizer(self.store, "gepa", self.journal)
        evidence = optimizer.evidence()
        self.assertEqual(sorted(evidence["error_types"]), ["missing_keyword", "timeout"])
        self.assertEqual(optimizer.score(BASE_PROMPT, evidence), 0.3 * evidence["success_rate"])
        full = BASE_PROMPT + "\n" + "\n".join(
            ["RÈGLE GEPA-01 : employer des mots-clés composés explicites et vérifier l'activation de chaque agent par un test de fumée.",
             "RÈGLE GEPA-03 : borner chaque étape, mesurer sa durée et découper avant de réessayer."]
        )
        self.assertAlmostEqual(optimizer.score(full, evidence), 0.7 + 0.3 * evidence["success_rate"], places=4)


if __name__ == "__main__":
    unittest.main()
