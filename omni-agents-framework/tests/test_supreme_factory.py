"""Tests de l'Agent Factory : création, doublons, validation, rollback."""
from supreme.evaluation import EvaluationEngine
from supreme.factory import AgentFactory
from tests._supreme_util import SupremeTestCase


class TestFactory(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.ev = EvaluationEngine(self.conn, self.core.registry)
        self.factory = AgentFactory(self.conn, self.core.registry, self.ev)

    def _spec(self, name="Agent Test Unique"):
        return {"name": name, "division": "D02", "objective": f"Objectif unique pour {name}",
                "primary_skills": ["compétence-a", "compétence-b", "compétence-c"],
                "task": f"Tâche représentative de {name}", "eval": "critère objectif",
                "tool": "json_validate"}

    def test_create_valid_activates(self):
        res = self.factory.create(self._spec())
        self.assertTrue(res["validated"])
        self.assertTrue(res["activated"])
        self.assertEqual(self.core.registry.get(res["id"])["status"], "monitored")

    def test_duplicate_name_rejected(self):
        self.factory.create(self._spec())
        with self.assertRaises(ValueError):
            self.factory.create(self._spec())

    def test_incomplete_rejected(self):
        with self.assertRaises(ValueError):
            self.factory.create({"name": "X"})

    def test_wrong_skill_count_rejected(self):
        spec = self._spec()
        spec["primary_skills"] = ["une-seule"]
        with self.assertRaises(ValueError):
            self.factory.create(spec)

    def test_update_and_rollback(self):
        res = self.factory.create(self._spec())
        aid = res["id"]
        self.factory.update(aid, {"objective": "Objectif modifié"}, "test modification")
        self.assertEqual(self.core.registry.profile(aid)["version"], "1.1.0")
        self.factory.rollback(aid)
        self.assertEqual(self.core.registry.profile(aid)["version"], "1.0.0")

    def test_remove_only_factory_agents(self):
        res = self.factory.create(self._spec())
        self.factory.remove(res["id"], "test")
        self.assertIsNone(self.core.registry.get(res["id"]))
        catalog_agent = self.tool_agent()
        with self.assertRaises(PermissionError):
            self.factory.remove(catalog_agent["id"], "interdit")


if __name__ == "__main__":
    import unittest
    unittest.main()
