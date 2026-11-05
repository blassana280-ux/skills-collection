import unittest
from pathlib import Path

from tests import ROOT
from omnibrain.parallel import run_plans_parallel


class ParallelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = [
            (ROOT / "examples" / "task-simple.md").read_text(encoding="utf-8"),
            (ROOT / "examples" / "task-medium.md").read_text(encoding="utf-8"),
            (ROOT / "examples" / "task-complex.md").read_text(encoding="utf-8"),
        ]

    def test_parallel_run_returns_one_plan_per_task(self):
        run = run_plans_parallel(self.tasks, max_workers=2)
        self.assertEqual(len(run.plans), len(self.tasks))
        self.assertEqual(run.workers, 2)
        for plan in run.plans:
            self.assertEqual(plan["wave"], 0)
            self.assertTrue(plan["briefs"])

    def test_brief_count_matches_squads(self):
        run = run_plans_parallel(self.tasks, max_workers=3)
        expected = sum(len(plan["briefs"]) for plan in run.plans)
        self.assertEqual(run.total_briefs(), expected)
        self.assertGreaterEqual(run.total_briefs(), 8)

    def test_coverage_indexes_every_agent(self):
        run = run_plans_parallel(self.tasks, max_workers=2)
        coverage = run.coverage()
        for agent_id, plan_indexes in coverage.items():
            self.assertTrue(plan_indexes)
            self.assertTrue(all(0 <= i < len(run.plans) for i in plan_indexes))
        # La demande complexe fait intervenir au moins 4 spécialistes.
        complex_plan = run.plans[2]
        self.assertGreaterEqual(len(complex_plan["squad"]), 4)

    def test_empty_task_list_raises(self):
        with self.assertRaises(ValueError):
            run_plans_parallel([], max_workers=2)

    def test_workers_capped_to_task_count(self):
        run = run_plans_parallel(self.tasks[:1], max_workers=8)
        self.assertEqual(run.workers, 1)


if __name__ == "__main__":
    unittest.main()
