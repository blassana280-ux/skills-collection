"""Tests du catalogue 1000 agents : comptes, unicité, complétude, permissions."""
import unittest

from supreme.catalog import generate
from supreme.profiles import EVAL_IDS, REQUIRED_FIELDS
from supreme.tools import tool_names


class TestCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles, cls.managers, cls.errors = generate()

    def test_no_validation_errors(self):
        self.assertEqual(self.errors, [])

    def test_exact_counts(self):
        specialists = [p for p in self.profiles if p["kind"] == "specialist"]
        self.assertEqual(len(specialists), 1000)
        self.assertEqual(len(self.managers), 20)

    def test_twenty_divisions_of_fifty(self):
        from collections import Counter
        c = Counter(p["division"] for p in self.profiles)
        self.assertEqual(len(c), 20)
        self.assertTrue(all(v == 50 for v in c.values()))

    def test_unique_ids_names_objectives(self):
        for key in ("id", "name", "objective"):
            vals = [p[key] for p in self.profiles]
            self.assertEqual(len(vals), len(set(vals)), f"doublons sur {key}")

    def test_required_fields_present(self):
        for p in self.profiles + self.managers:
            for f in REQUIRED_FIELDS:
                self.assertIn(f, p, f"{p['id']} manque {f}")
                self.assertTrue(p[f] not in ("", None, [], {}), f"{p['id']} champ vide {f}")

    def test_seven_evals_each(self):
        for p in self.profiles + self.managers:
            self.assertEqual({e["id"] for e in p["eval_tests"]}, set(EVAL_IDS), p["id"])

    def test_tools_valid_and_least_privilege(self):
        names = tool_names()
        for p in self.profiles + self.managers:
            for t in p["allowed_tools"]:
                self.assertIn(t, names)
            perms = p["permissions"]
            self.assertEqual(perms["network"], "deny")
            self.assertFalse(perms["github_write"])
            self.assertEqual(perms["secrets"], "none")
            self.assertFalse(perms["spawn_agents"])

    def test_deterministic_generation(self):
        p2, m2, e2 = generate()
        self.assertEqual(p2, self.profiles)
        self.assertEqual(m2, self.managers)

    def test_distinct_specializations(self):
        # Pas de clones (objectif+compétences+tâche identiques)
        sigs = [(p["objective"], tuple(sorted(p["primary_skills"])), p["allowed_tasks"][0]) for p in self.profiles]
        self.assertEqual(len(sigs), len(set(sigs)))


if __name__ == "__main__":
    unittest.main()
