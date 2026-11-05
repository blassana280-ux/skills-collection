import unittest

from omnibrain.gates import GateEngine


COMPLETE_DELIVERABLE = """# Livrable unique — synthèse et intégration

## Synthèse et intégration
Tous les contrats d'interface sont respectés : le contrat `api-contract` lie
backend-api et frontend-ui, le contrat de données est validé.

## Brief backend-api
Endpoints livrés avec trace de tests. Taux de couverture actuel 87 % (2026-10-21),
source : https://example.com/reports/coverage-2026-10

## Brief qa-test
Résultats de recette consolidés, dernière exécution le 2026-10-25.

## Brief adversarial-reviewer
### Revue adverse
Verdict : PASS — 2 observations mineures, aucune bloquante.
"""

INCOMPLETE_DELIVERABLE = "# Brouillon\n\nTODO: écrire la synthèse plus tard\n"


class GateEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = GateEngine()

    def test_complete_deliverable_passes_all_gates(self):
        report = self.engine.evaluate(
            COMPLETE_DELIVERABLE,
            expected_agents=["backend-api", "qa-test", "adversarial-reviewer"],
        )
        for gate in report.results:
            self.assertEqual(gate.status, "PASS", msg=f"{gate.gate}: {gate.evidence}")
        self.assertEqual(report.verdict, "PASS")

    def test_incomplete_deliverable_needs_work_by_default(self):
        report = self.engine.evaluate(INCOMPLETE_DELIVERABLE, expected_agents=["backend-api"])
        self.assertFalse(report.passed)
        self.assertEqual(report.verdict, "NEEDS WORK")
        gate_names = {g.gate for g in report.results}
        self.assertEqual(len(gate_names), 4)

    def test_time_sensitive_claim_without_source_fails_freshness(self):
        text = "# Livrable\n\nLe taux d'imposition actuel est de 30 %.\n"
        report = self.engine.evaluate(text)
        freshness = next(g for g in report.results if "Fraîche" in g.gate or "fraîche" in g.gate)
        self.assertEqual(freshness.status, "NEEDS WORK")

    def test_missing_adversarial_section_fails_g3(self):
        text = (
            "# Synthèse et intégration\nContrats respectés.\n"
            "## Brief backend-api\nfait, voir https://example.com (2026-10-01)\n"
        )
        report = self.engine.evaluate(text, expected_agents=["backend-api"])
        g3 = next(g for g in report.results if "Revue" in g.gate)
        self.assertEqual(g3.status, "NEEDS WORK")


if __name__ == "__main__":
    unittest.main()
