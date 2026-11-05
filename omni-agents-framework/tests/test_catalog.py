import unittest
from pathlib import Path

from tests import ROOT
from omnibrain.config import load_matrix
from omnibrain.registry import Registry
from omnibrain.router import Router
from omnibrain.classifier import Classifier, keyword_present, _normalize

EXPECTED_TOTAL = 115          # 12 agents cœur + 103 agents catalogue (v4)
EXPECTED_CATALOG = 103
EXPECTED_SQUADS = 10
CORE_IDS = {
    "omnibrain", "frontend-ui", "backend-api", "data-ai", "qa-test",
    "devops-sre", "security", "adversarial-reviewer", "ohada-finance",
    "marketing-growth", "research-intel", "product-delivery",
}


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = load_matrix(ROOT)
        cls.registry = Registry(root=ROOT, matrix=cls.matrix)
        cls.agents = cls.registry.agents()
        cls.catalog_agents = [a for a in cls.agents if a.squad != "core"]

    def test_total_agent_count(self):
        self.assertEqual(len(self.agents), EXPECTED_TOTAL)
        self.assertEqual(len(self.catalog_agents), EXPECTED_CATALOG)

    def test_unique_ids_and_core_preserved(self):
        ids = [a.id for a in self.agents]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(CORE_IDS.issubset(set(ids)))

    def test_ten_squads_with_expected_sizes(self):
        sizes: dict[str, int] = {}
        for agent in self.catalog_agents:
            sizes[agent.squad] = sizes.get(agent.squad, 0) + 1
        self.assertEqual(len(sizes), EXPECTED_SQUADS)
        self.assertEqual(sizes["engineering"], 17)
        self.assertEqual(sizes["data-ai"], 13)
        self.assertEqual(sizes["cloud-infra"], 10)
        self.assertEqual(sizes["security"], 11)
        self.assertEqual(sizes["qa-testing"], 6)
        self.assertEqual(sizes["design-ux"], 8)
        self.assertEqual(sizes["product-delivery"], 9)
        self.assertEqual(sizes["marketing-growth"], 10)
        self.assertEqual(sizes["finance-legal"], 12)
        self.assertEqual(sizes["west-africa-sectors"], 7)

    def test_every_catalog_file_exists_with_required_sections(self):
        required = ("## Mission principale", "## Règles critiques", "## Protocoles universels",
                    "## Entrées / sorties", "## Quand mobiliser", "## Bord de croissance")
        for agent in self.catalog_agents:
            path = ROOT / agent.file
            self.assertTrue(path.is_file(), msg=f"fiche manquante : {agent.file}")
            body = path.read_text(encoding="utf-8")
            for section in required:
                self.assertIn(section, body, msg=f"{agent.id}: section {section} manquante")
            # 5 règles critiques numérotées.
            self.assertIn("5. ", body, msg=f"{agent.id}: 5 règles critiques attendues")

    def test_every_agent_is_routable_on_its_own_keywords(self):
        """Test de fumée d'activation : chaque agent doit matcher une requête
        synthétique construite depuis ses propres mots-clés."""
        for agent in self.catalog_agents:
            synthetic = f"Mission spécialisée : {', '.join(agent.keywords[:3])}."
            norm = _normalize(synthetic)
            self.assertTrue(
                any(keyword_present(kw, norm) for kw in agent.keywords),
                msg=f"{agent.id}: aucun mot-clé ne s'active sur {synthetic!r}",
            )

    def test_router_picks_catalog_agent_on_specialized_query(self):
        router = Router(self.registry, Classifier(self.matrix))
        cases = {
            "Audit pentest de l'API avec test d'intrusion": "pentester",
            "Intégration du paiement Orange Money et Wave avec KYC": "mobile-money-fintech",
            "Traduction et localisation en bambara bamanankan des SMS": "localization-bambara",
            "Déploiement Terraform et durcissement du cluster Kubernetes": "terraform-iac",
            "Test de charge k6 pour mesurer la latence p95": "performance-testing",
        }
        for query, expected_id in cases.items():
            decision = router.route(query)
            ids = [a.id for a in decision.agents]
            self.assertIn(expected_id, ids, msg=f"requête {query!r} -> {ids}")

    def test_risk_agents_flagged(self):
        risk_ids = {a.id for a in self.agents if a.risk}
        for must_have in ("pentester", "data-protection-lawyer", "mobile-money-fintech",
                          "remittance-compliance", "tax-planner", "external-auditor"):
            self.assertIn(must_have, risk_ids)
        # Les 11 agents de l'escouade sécurité sont tous à risque.
        security = [a for a in self.catalog_agents if a.squad == "security"]
        self.assertEqual(len(security), 11)
        self.assertTrue(all(a.risk for a in security))

    def test_catalog_toml_is_generated_and_consistent(self):
        toml_path = ROOT / "catalog" / "catalog-100.toml"
        self.assertTrue(toml_path.is_file())
        text = toml_path.read_text(encoding="utf-8")
        self.assertEqual(text.count("[[agents]]"), EXPECTED_CATALOG)

    def test_keyword_hygiene_no_generic_short_tokens(self):
        """Un mot-clé mono-mot d'au moins 3 caractères évite les faux positifs
        (« plan », « audit », « go », « bi »...). Les expressions multi-mots
        restent libres puisque leur contexte est explicite."""
        for agent in self.catalog_agents:
            for keyword in agent.keywords:
                # Les noms technologiques contenant #, +, & ou . (C#, FP&A, .NET)
                # sont légitimes même courts ; seuls les mots alpha courts sont bannis.
                if " " not in keyword and keyword.isalpha() and len(keyword) < 3:
                    self.fail(f"{agent.id}: mot-clé trop générique/court {keyword!r}")

    def test_no_cross_domain_false_positives(self):
        router = Router(self.registry, Classifier(self.matrix))
        # « audit d'accessibilité » ne doit pas réveiller la finance ni la sécurité.
        scores = router._score_agents(_normalize(
            "Tests de charge k6, automatisation Playwright et audit d'accessibilité WCAG"))
        for must_stay_zero in ("grc-compliance", "external-auditor", "terraform-iac"):
            self.assertEqual(scores.get(must_stay_zero, 0), 0,
                             msg=f"faux positif {must_stay_zero} sur une requête accessibilité")
        # « plan fiscal » ne doit pas réveiller Terraform.
        fiscal = router._score_agents(_normalize("Établir le plan fiscal et la liasse OHADA"))
        self.assertEqual(fiscal.get("terraform-iac", 0), 0)
        # Mais les vrais signaux fonctionnent toujours.
        self.assertGreater(scores["accessibility-testing"], 0)
        self.assertGreater(fiscal["ohada-finance"], 0)
        # Et une vraie demande fiscale réveille bien le planificateur fiscal.
        tax = router._score_agents(_normalize("Optimisation fiscale et prix de transfert du groupe"))
        self.assertGreater(tax["tax-planner"], 0)


if __name__ == "__main__":
    unittest.main()
