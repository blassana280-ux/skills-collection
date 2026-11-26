"""Tests planificateur : classification, DAG valide, tâches explicites, permissions."""
from supreme.planner import MissionPlanner, classify
from tests._supreme_util import SupremeTestCase


class TestPlanner(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.planner = MissionPlanner(self.core.registry, self.core.router)

    def test_classification_levels(self):
        self.assertEqual(classify("court")["level"], "simple")
        self.assertEqual(classify("mot " * 60)["level"], "complexe")

    def test_plan_produces_valid_dag(self):
        plan = self.planner.plan({"objective": "Vérifier la syntaxe Python et valider un JSON"})
        self.assertTrue(plan["dag_order"])
        self.assertTrue(plan["tasks"])
        # vérification + rapport présents
        kinds = {t["kind"] for t in plan["tasks"]}
        self.assertIn("verify", kinds)
        self.assertIn("report", kinds)

    def test_explicit_tasks_validated(self):
        a = self.tool_agent("D02")
        plan = self.planner.plan({"objective": "test", "tasks": [{"agent_id": a["id"], "tool": "json_validate"}]})
        self.assertEqual(len(plan["tasks"]), 1)
        self.assertEqual(plan["tasks"][0]["agent_id"], a["id"])

    def test_unauthorized_tool_rejected(self):
        a = self.tool_agent("D02")
        with self.assertRaises(PermissionError):
            self.planner.plan({"objective": "test", "tasks": [{"agent_id": a["id"], "tool": "secret_scan"}]})

    def test_unknown_agent_rejected(self):
        with self.assertRaises(KeyError):
            self.planner.plan({"objective": "test", "tasks": [{"agent_id": "inexistant"}]})

    def test_cycle_rejected(self):
        a = self.tool_agent("D02")
        with self.assertRaises(ValueError):
            self.planner.plan({"objective": "test", "tasks": [
                {"agent_id": a["id"], "tool": "json_validate", "depends_on": ["mis-x-t002"]},
                {"agent_id": a["id"], "tool": "json_validate", "depends_on": ["mis-x-t001"]},
            ]})


if __name__ == "__main__":
    import unittest
    unittest.main()
