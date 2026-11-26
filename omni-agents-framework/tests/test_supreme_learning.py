"""Tests apprentissage/auto-amélioration : collecte, analyse, stratégies, gain,
rollback, interdiction d'auto-modification du noyau."""
from supreme.evaluation import EvaluationEngine
from supreme.learning import LearningEngine
from tests._supreme_util import SupremeTestCase


class TestLearning(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.ev = EvaluationEngine(self.conn, self.core.registry)
        self.learning = LearningEngine(self.conn, self.core.registry, self.ev)

    def test_collect_empty(self):
        out = self.learning.collect_outcomes()
        self.assertIsNone(out["task_success_rate"])

    def test_collect_after_mission(self):
        sub = self.core.submit({"objective": "Vérifier Python"})
        self.core.run(sub["mission_id"])
        out = self.learning.collect_outcomes()
        self.assertEqual(out["task_success_rate"], 1.0)

    def test_propose_and_evaluate_strategy(self):
        a = self.tool_agent("D02")
        sid = self.learning.propose_strategy(a["id"], "stratégie v1")
        ev = self.learning.evaluate_strategy(sid, "json_validate")
        self.assertEqual(ev["score"], 1.0)

    def test_accept_on_gain_and_rollback(self):
        a = self.tool_agent("D02")
        res = self.learning.compare_and_accept(a["id"], "json_validate", "stratégie v1")
        self.assertTrue(res["accepted"])
        # pas de gain -> refusé
        res2 = self.learning.compare_and_accept(a["id"], "json_validate", "stratégie v2")
        self.assertFalse(res2["accepted"])
        rb = self.learning.rollback(a["id"])
        self.assertTrue(rb["rolled_back"])

    def test_core_self_modification_forbidden(self):
        with self.assertRaises(PermissionError):
            self.learning.propose_strategy("omnibrain-core", "modifier le noyau")

    def test_self_improvement_report(self):
        rep = self.learning.self_improvement_report()
        self.assertIn("constraints", rep)
        self.assertTrue(any("noyau" in c for c in rep["constraints"]))


if __name__ == "__main__":
    import unittest
    unittest.main()
