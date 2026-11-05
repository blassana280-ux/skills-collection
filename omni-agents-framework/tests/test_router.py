import unittest

from tests import ROOT
from omnibrain.config import load_matrix
from omnibrain.registry import Registry
from omnibrain.classifier import Classifier
from omnibrain.router import Router


class RouterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        matrix = load_matrix(ROOT)
        cls.registry = Registry(root=ROOT, matrix=matrix)
        cls.router = Router(cls.registry, Classifier(matrix))

    def test_frontend_routing(self):
        decision = self.router.route("Conçois les composants React et le design system de la page.")
        ids = [a.id for a in decision.agents]
        self.assertIn("frontend-ui", ids)
        self.assertNotIn("omnibrain", ids)  # l'orchestrateur ne rejoint jamais une escouade

    def test_complex_task_forces_review_and_qa(self):
        task = (
            "Refonte bout en bout : interface React, API backend, pipeline de données, "
            "sécurité OWASP, déploiement Kubernetes et tests e2e."
        )
        classification = self.router.classifier.classify(task)
        decision = self.router.route(task, classification)
        ids = [a.id for a in decision.agents]
        self.assertEqual(classification.level, "complexe")
        self.assertIn("adversarial-reviewer", ids)
        self.assertIn("qa-test", ids)
        self.assertIn("security", ids)
        self.assertLessEqual(len(ids), 8)
        self.assertEqual(decision.wave, 0)  # une seule vague parallèle

    def test_ohada_risk_routes_finance_expert(self):
        decision = self.router.route(
            "Mets à jour la liasse fiscale OHADA et le calendrier TVA avec audit de conformité."
        )
        ids = [a.id for a in decision.agents]
        self.assertIn("ohada-finance", ids)

    def test_unknown_task_falls_back_to_scoping(self):
        decision = self.router.route("xyzzy nonsense globbernash")
        ids = [a.id for a in decision.agents]
        self.assertTrue(ids)
        self.assertIn("product-delivery", ids)

    def test_contracts_only_when_both_parties_present(self):
        decision = self.router.route("Refonte du design system et des composants React seuls.")
        for contract in decision.contracts:
            squad = {a.id for a in decision.agents}
            self.assertTrue(squad.intersection(contract.producers))
            self.assertTrue(squad.intersection(contract.consumers))


if __name__ == "__main__":
    unittest.main()
