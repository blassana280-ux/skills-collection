import unittest

from tests import ROOT
from omnibrain.dispatcher import Dispatcher, GATE_CHECKLIST


class DispatcherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dispatcher = Dispatcher(root=ROOT)

    def test_plan_structure(self):
        plan = self.dispatcher.plan(
            "Industrialisation d'une plateforme : frontend React, API backend, "
            "pipeline de données, sécurité et mise en production Kubernetes, avec tests."
        )
        self.assertEqual(len(plan.briefs), len(plan.decision.agents))
        self.assertEqual(plan.decision.wave, 0)
        self.assertEqual(len(plan.gates_checklist), 4)
        for brief in plan.briefs:
            self.assertTrue(brief.objective)
            self.assertTrue(brief.expected_outputs)
            self.assertTrue(brief.gate_obligations)
            self.assertIn("NEEDS WORK", " ".join(brief.gate_obligations))

    def test_simple_plan_single_brief(self):
        plan = self.dispatcher.plan("Corrige le style CSS du bouton de validation.")
        self.assertEqual(plan.classification.level, "simple")
        self.assertEqual(len(plan.briefs), 1)

    def test_plan_serializes_to_dict(self):
        plan = self.dispatcher.plan("Audit de sécurité OWASA... euh OWASP de l'API.")
        data = plan.as_dict()
        self.assertEqual(data["wave"], 0)
        self.assertIn("squad", data)
        self.assertIn("briefs", data)
        self.assertEqual(len(GATE_CHECKLIST), 4)


if __name__ == "__main__":
    unittest.main()
