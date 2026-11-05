"""Phase 2.2 — auto-amélioration : 2 échecs -> branche + PR, jamais de fusion."""

import tempfile
import unittest
from pathlib import Path

from omni.memory.autofix import AutoFix, CommandBackend, RecordingBackend, build_corrected_fiche
from omni.memory.store import MemoryStore


class AutoFixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = MemoryStore(Path(self.tmp.name) / "memory.sqlite3")
        self.mid = self.store.record_mission({"project_type": "qa", "title": "auto-fix"})
        self.backend = RecordingBackend()
        self.fixer = AutoFix(self.store, self.backend, base_dir=Path(self.tmp.name) / "autofix")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _fail(self, error_type="timeout", message="trop lent"):
        self.store.record_failure(self.mid, "qa-flaky", "qa-flaky", error_type, message)

    def test_below_threshold_does_nothing(self):
        self._fail()
        result = self.fixer.check("qa-flaky")
        self.assertFalse(result.triggered)
        self.assertIn("seuil", result.reason)
        self.assertEqual(self.backend.actions, [])

    def test_two_failures_open_branch_and_pr_without_merge(self):
        self._fail("timeout", "durée > seuil")
        self._fail("missing_keyword", "mot-clé trop générique")
        result = self.fixer.check("qa-flaky")
        self.assertTrue(result.triggered)
        self.assertEqual(result.branch, "omnibrain/fix-qa-flaky")
        self.assertNotIn(result.branch, {"main", "master"})
        self.assertEqual(
            [a[0] for a in self.backend.actions],
            ["create_branch", "write_fiche", "commit", "push", "open_pr"],
        )
        self.assertFalse(hasattr(self.backend, "merge"))
        self.assertTrue(result.as_dict()["merge_forbidden"])

        fiche = Path(result.fiche_path).read_text(encoding="utf-8")
        self.assertIn("human_merge_required: true", fiche)
        self.assertIn("Règles correctives", fiche)
        self.assertIn("mots-clés explicites", fiche)
        self.assertIn("2 échecs", fiche)
        self.assertIn("Aucune fusion automatique", fiche)
        self.assertIn("omnibrain/fix-qa-flaky", self.backend.actions[-1][1])

    def test_idempotent_for_same_failure_signature(self):
        self._fail()
        self._fail()
        first = self.fixer.check("qa-flaky")
        second = self.fixer.check("qa-flaky")
        self.assertTrue(first.triggered)
        self.assertFalse(second.triggered)
        self.assertIn("déjà proposé", second.reason)
        self.assertEqual(len(self.backend.actions), 5)
        self.assertEqual(self.store.stats()["autofix_runs"], 1)

    def test_command_backend_dry_run_is_safe(self):
        backend = CommandBackend(cwd=Path(self.tmp.name), dry_run=True)
        backend.create_branch("omnibrain/fix-demo")
        backend.write_fiche("var/autofix/demo.md", "contenu")
        backend.push("omnibrain/fix-demo")
        self.assertTrue(all(kind in {"dry-run", "dry-run-write"} for kind, _ in backend.actions))
        self.assertFalse((Path(self.tmp.name) / "var/autofix/demo.md").exists())
        with self.assertRaises(ValueError):
            backend.create_branch("main")

    def test_corrected_fiche_is_deterministic(self):
        failures = [{"id": 1, "error_type": "timeout", "attempt": 1, "message": "lent"},
                    {"id": 2, "error_type": "gate_blocked", "attempt": 2, "message": "gate"}]
        a = build_corrected_fiche("agent-x", failures, signature="abc123")
        b = build_corrected_fiche("agent-x", failures, signature="abc123")
        self.assertEqual(a, b)
        self.assertIn("preuve fraîche", a)


if __name__ == "__main__":
    unittest.main()
