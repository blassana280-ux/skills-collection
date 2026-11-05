"""Phase 4.3 — hygiène des mots-clés étendue + 3 nouveaux agents utiles."""

import subprocess
import sys
import unittest

from tests import ROOT
from omnibrain.classifier import Classifier, _normalize
from omnibrain.config import load_matrix
from omnibrain.registry import Registry
from omnibrain.router import Router

NEW_IDS = ("observability-telemetry", "memory-sqlite", "risk-gate-keeper")
BANNED_GENERIC = {
    "audit", "plan", "state", "go", "bi", "ml", "pr", "stock", "demande",
    "contrat", "formation", "x", "test", "data", "api", "todo", "tbd",
}


class CatalogV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = load_matrix(ROOT)
        cls.registry = Registry(root=ROOT, matrix=cls.matrix)
        cls.agents = cls.registry.agents()
        cls.catalog = [a for a in cls.agents if a.squad != "core"]
        cls.router = Router(cls.registry, Classifier(cls.matrix))

    def test_v4_counts_and_squad_sizes(self):
        self.assertEqual(len(self.agents), 115)
        self.assertEqual(len(self.catalog), 103)
        sizes = {}
        for agent in self.catalog:
            sizes[agent.squad] = sizes.get(agent.squad, 0) + 1
        self.assertEqual(sizes["engineering"], 17)
        self.assertEqual(sizes["data-ai"], 13)
        self.assertEqual(sizes["qa-testing"], 6)
        self.assertEqual(len(sizes), 10)

    def test_three_new_agents_exist_with_generated_fiches(self):
        by_id = {a.id: a for a in self.catalog}
        for new_id in NEW_IDS:
            self.assertIn(new_id, by_id)
            agent = by_id[new_id]
            self.assertTrue((ROOT / agent.file).is_file())
            body = (ROOT / agent.file).read_text(encoding="utf-8")
            for section in ("## Mission principale", "## Règles critiques", "## Protocoles universels",
                            "## Entrées / sorties", "## Quand mobiliser", "## Bord de croissance"):
                self.assertIn(section, body)
            self.assertIn("5. ", body)

    def test_new_agents_are_routable_and_do_not_wake_unrelated_domains(self):
        cases = {
            "Instrumentation des vagues avec télémétrie json et rapport de mission": "observability-telemetry",
            "Mémoire sqlite et recettes par projet pour l'historique des missions": "memory-sqlite",
            "Gate humaine et escalade lassana pour plan de fusion": "risk-gate-keeper",
        }
        for query, expected in cases.items():
            self.assertIn(expected, [a.id for a in self.router.route(query).agents])
        scores = self.router._score_agents(_normalize("Mémoire sqlite et recettes par projet"))
        self.assertEqual(scores.get("terraform-iac", 0), 0)
        self.assertEqual(scores.get("external-auditor", 0), 0)

    def test_extended_keyword_hygiene(self):
        for agent in self.catalog:
            keywords = list(agent.keywords)
            self.assertTrue(3 <= len(keywords) <= 12, msg=agent.id)
            self.assertEqual(len(keywords), len(set(keywords)), msg=f"doublon interne : {agent.id}")
            for keyword in keywords:
                self.assertEqual(keyword, keyword.strip(), msg=f"{agent.id}: espace autour de {keyword!r}")
                self.assertNotIn(keyword.lower(), BANNED_GENERIC, msg=f"{agent.id}: mot-clé générique {keyword!r}")
                if " " not in keyword and keyword.isalpha():
                    self.assertGreaterEqual(len(keyword), 3, msg=f"{agent.id}: mot-clé trop court {keyword!r}")

    def test_risk_officer_flagged_and_generated_toml_consistent(self):
        self.assertTrue({a.id: a for a in self.agents}["risk-gate-keeper"].risk)
        toml = (ROOT / "catalog" / "catalog-100.toml").read_text(encoding="utf-8")
        self.assertEqual(toml.count("[[agents]]"), 103)
        for new_id in NEW_IDS:
            self.assertIn(f'id = "{new_id}"', toml)

    def test_generator_check_is_green(self):
        proc = subprocess.run(
            [sys.executable, "tools/generate_agents.py", "--check"],
            cwd=ROOT, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("103 agents", proc.stdout)
        self.assertIn("aucune anomalie", proc.stdout)


if __name__ == "__main__":
    unittest.main()
