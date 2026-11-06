"""Tests évaluation : 7 tests par profil, activation sur preuve, différés honnêtes."""
from supreme.evaluation import EvaluationEngine
from tests._supreme_util import SupremeTestCase


class TestEvaluation(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.ev = EvaluationEngine(self.conn, self.core.registry)

    def test_tool_agent_seven_tests_pass(self):
        a = self.tool_agent("D02")
        summary = self.ev.run_profile_tests(a["id"])
        self.assertEqual(summary["total"], 7)
        self.assertEqual(summary["passed"], 7)
        self.assertEqual(summary["deferred"], 0)

    def test_llm_agent_deferred(self):
        a = self.llm_agent("D02")
        summary = self.ev.run_profile_tests(a["id"])
        self.assertTrue(summary["results"]["representative"]["deferred"])
        self.assertEqual(summary["deferred"], 1)

    def test_validate_tool_agent(self):
        a = self.tool_agent("D02")
        res = self.ev.validate_agent(a["id"])
        self.assertTrue(res["validated"])
        self.assertEqual(self.core.registry.get(a["id"])["status"], "validated")

    def test_activate_requires_real_success(self):
        a = self.tool_agent("D02")
        res = self.ev.activate_agent(a["id"])
        self.assertTrue(res["activated"])
        self.assertEqual(self.core.registry.get(a["id"])["status"], "monitored")

    def test_llm_agent_not_activated(self):
        a = self.llm_agent("D02")
        res = self.ev.activate_agent(a["id"])
        self.assertFalse(res["activated"])

    def test_evaluate_all_counts(self):
        counts = self.ev.evaluate_all(activate=True)
        self.assertEqual(counts["validated"], 1020)
        self.assertEqual(counts["operational"], 60)
        self.assertEqual(counts["deferred"], 960)
        self.assertEqual(counts["failed"], 0)


if __name__ == "__main__":
    import unittest
    unittest.main()
