"""Tests du registre SQLite : sync, statuts sur preuve, recherche, divisions."""
from tests._supreme_util import SupremeTestCase


class TestRegistry(SupremeTestCase):
    def test_sync_idempotent(self):
        # setUp a déjà synchronisé : un nouveau sync n'ajoute rien.
        second = self.core.registry.sync_catalog()
        self.assertEqual(second["added"], 0)
        self.assertEqual(second["total"], 1020)
        self.assertEqual(sum(self.core.registry.status_counts().values()), 1020)

    def test_get_and_profile(self):
        a = self.tool_agent()
        got = self.core.registry.get(a["id"])
        self.assertEqual(got["id"], a["id"])
        self.assertIn("objective", got["profile"])

    def test_status_requires_evidence(self):
        a = self.tool_agent()
        with self.assertRaises(ValueError):
            self.core.registry.set_status(a["id"], "operational", "")
        self.core.registry.set_status(a["id"], "operational", "preuve d'exécution réelle")
        self.assertEqual(self.core.registry.get(a["id"])["status"], "operational")

    def test_unknown_status_rejected(self):
        a = self.tool_agent()
        with self.assertRaises(ValueError):
            self.core.registry.set_status(a["id"], "inexistant", "x")

    def test_search_finds_relevant(self):
        res = self.core.registry.search("python syntaxe", limit=5)
        self.assertTrue(res)
        self.assertTrue(any("python" in a["profile"]["objective"].lower() or "python" in a["name"].lower() for a in res))

    def test_divisions_summary(self):
        summary = self.core.registry.divisions_summary()
        self.assertEqual(len(summary), 20)
        self.assertTrue(all(d["total"] == 50 for d in summary))
        self.assertTrue(all(d["manager"] for d in summary))

    def test_status_counts(self):
        counts = self.core.registry.status_counts()
        self.assertEqual(sum(counts.values()), 1020)
        self.assertEqual(counts["registered"], 1020)


if __name__ == "__main__":
    import unittest
    unittest.main()
