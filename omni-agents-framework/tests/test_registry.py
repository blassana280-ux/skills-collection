import unittest

from tests import ROOT
from omnibrain.config import load_matrix
from omnibrain.registry import Registry


class RegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry(root=ROOT, matrix=load_matrix(ROOT))

    def test_all_agents_loaded_with_unique_ids(self):
        agents = self.registry.agents()
        self.assertGreaterEqual(len(agents), 10)
        ids = [a.id for a in agents]
        self.assertEqual(len(ids), len(set(ids)))

    def test_orchestrator_flagged_and_excluded_from_squads(self):
        orchestrator = self.registry.by_id("omnibrain")
        self.assertTrue(orchestrator.orchestrator)
        self.assertTrue(orchestrator.file.endswith("specialized-omnibrain-orchestrator-agent.md"))

    def test_validate_returns_no_errors(self):
        errors = self.registry.validate()
        self.assertEqual(errors, [], msg="\n".join(errors))

    def test_every_agent_file_has_description(self):
        for agent in self.registry.agents():
            self.assertTrue(
                agent.description,
                msg=f"l'agent {agent.id} n'a pas de description en frontmatter",
            )

    def test_contracts_reference_known_agents(self):
        known = {a.id for a in self.registry.agents()}
        for contract in self.registry.contracts():
            self.assertTrue(contract.producers)
            self.assertTrue(contract.consumers)
            for agent_id in contract.producers + contract.consumers:
                self.assertIn(agent_id, known)


if __name__ == "__main__":
    unittest.main()
