import unittest

from tests import ROOT
from omnibrain.config import load_matrix
from omnibrain.classifier import Classifier


class ClassifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classifier = Classifier(load_matrix(ROOT))

    def test_simple_task_single_agent(self):
        # Requête mono-domaine délibérément sans ambiguïté (pas de mot métier
        # partagé avec une autre compétence, ex. « formulaire » -> UX writer).
        result = self.classifier.classify("Corrige le style CSS du bouton de validation.")
        self.assertEqual(result.level, "simple")
        self.assertEqual(result.squad_size, 1)
        self.assertIn("ui", result.domains)

    def test_medium_task_two_domains(self):
        result = self.classifier.classify(
            "Crée une API REST pour les commandes et ajoute les tests unitaires associés."
        )
        self.assertEqual(result.level, "moyenne")
        self.assertGreaterEqual(result.squad_size, 2)
        self.assertLessEqual(result.squad_size, 3)
        self.assertEqual(set(["backend", "qa"]), set(result.domains))

    def test_complex_task_multi_domain(self):
        task = (
            "Refonte complète de l'architecture : frontend React, API backend, pipeline de "
            "données, sécurité OWASP, déploiement Kubernetes et tests e2e, avec une revue adverse."
        )
        result = self.classifier.classify(task)
        self.assertEqual(result.level, "complexe")
        self.assertGreaterEqual(result.squad_size, 4)
        self.assertLessEqual(result.squad_size, 8)
        self.assertGreaterEqual(len(result.domains), 3)
        self.assertTrue(result.signals)

    def test_risk_domain_weighs_more(self):
        risky = self.classifier.classify("Audit de sécurité OWASP et chiffrement des secrets.")
        plain = self.classifier.classify("Rédige un texte de présentation pour la page d'accueil.")
        self.assertIn("security", risky.domains)
        self.assertGreater(risky.score, plain.score)

    def test_explainability_every_signal_has_evidence(self):
        result = self.classifier.classify("Refonte d'une API et de son pipeline de données.")
        for signal in result.signals:
            self.assertTrue(signal.evidence)
            self.assertGreater(signal.weight, 0)


if __name__ == "__main__":
    unittest.main()
