"""Intégration v4 : mémoire -> graphe -> sandbox -> télémétrie -> benchmarks.

Un seul scénario de bout en bout, avec preuves disque et base. Aucune fusion,
aucun appel réseau, aucun secret : exécutable hors ligne en CI.
"""

import json
import tempfile
import unittest
from pathlib import Path

from omni.graph import run_pipeline
from omni.memory.autofix import AutoFix, RecordingBackend
from omni.memory.store import MemoryStore
from omni.sandbox import RBAC, Runtime, Sandbox
from omni.telemetry import from_memory
from tools.benchmark import run_benchmark
from tools.optimize_prompts import PromptOptimizer


class IntegrationV4Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = MemoryStore(self.root / "integration.sqlite3")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_full_mission_chain(self):
        # 1. Graphe critique + sandbox de calcul + approbations humaines explicites.
        result = run_pipeline(
            "Instrumenter le calcul lourd d'une mission", project_type="integration",
            store=self.store, sandbox=Sandbox(timeout_s=5),
            heavy_code="print('calcul: 6 * 7 =', 6 * 7)",
            approvals={"revue_adverse": True, "verification": True},
            artifacts_dir=self.root / "reports",
        )
        self.assertEqual(result.state.verdict, "PASS")
        self.assertIn("calcul: 6 * 7 = 42", result.state.implementation)
        self.assertEqual(result.state.artifacts["sandbox_backend"], "local")

        # 2. Preuves disque : JSON + markdown dérivé du même objet.
        telemetry_json = json.loads(Path(result.telemetry_json_path).read_text(encoding="utf-8"))
        markdown = Path(result.report_md_path).read_text(encoding="utf-8")
        self.assertEqual(telemetry_json["mission_id"], result.mission_id)
        self.assertIn("Renforts obligatoires", markdown)
        self.assertTrue(all(telemetry_json["reinforcements"].values()))

        # 3. Mémoire : reconstruction de la télémétrie depuis la base.
        rebuilt = from_memory(self.store, result.mission_id)
        self.assertGreater(rebuilt.summary()["totals"]["agents"], 0)
        self.assertEqual(len(self.store.results_for(result.mission_id)), 5)
        self.assertEqual(len(self.store.get_recettes("integration")), 1)
        self.assertGreater(self.store.stats()["orchestration_logs"], 0)

        # 4. GEPA : chaque itération journalisée en base et en JSONL.
        self.store.record_failure(result.mission_id, "agent-flaky", "agent-flaky", "timeout", "lent")
        self.store.record_failure(result.mission_id, "agent-flaky", "agent-flaky", "gate_blocked", "sans preuve")
        optimizer = PromptOptimizer(self.store, "integration", self.root / "gepa.jsonl")
        optimization = optimizer.optimize(2)
        self.assertEqual(len((self.root / "gepa.jsonl").read_text(encoding="utf-8").splitlines()), 2)
        self.assertEqual(len(self.store.prompt_iterations("integration")), 2)
        self.assertGreaterEqual(optimization["accepted"], 1)

        # 5. Auto-amélioration : branche + PR, jamais de fusion.
        backend = RecordingBackend()
        fix = AutoFix(self.store, backend, base_dir=self.root / "fixes").check("agent-flaky")
        self.assertTrue(fix.triggered)
        self.assertTrue(fix.branch.startswith("omnibrain/fix-"))
        self.assertFalse(hasattr(backend, "merge"))
        self.assertEqual(self.store.stats()["autofix_runs"], 1)

        # 6. Benchmarks historisés + runtime RBAC.
        bench = run_benchmark(runs=1, history_path=self.root / "history.jsonl", store=self.store)
        self.assertEqual(bench["record"]["metrics"]["hits"], 10)
        self.assertEqual(self.store.stats()["benchmarks"], 1)
        runtime = Runtime(self.store)
        mid = runtime.submit("Mission service", project_type="service")
        runtime.tick()
        self.assertEqual(self.store.get_mission(mid)["verdict"], "NEEDS WORK")
        self.assertFalse(RBAC().allow("omnibrain-service", "merge_pr", human_approval=True))

        # 7. Aucun secret persisté, aucune branche principale ciblée.
        with (self.root / "dump.txt").open("w", encoding="utf-8") as fh:
            fh.write(json.dumps(self.store.stats()))
        self.assertNotIn("ghp_", (self.root / "dump.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
