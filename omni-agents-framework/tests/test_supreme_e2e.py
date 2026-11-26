"""Test de bout en bout : mission réelle -> mémoire -> télémétrie -> rapport."""
from supreme.observability import ObservabilityEngine
from supreme.reporting import ReportingEngine
from tests._supreme_util import SupremeTestCase


class TestEndToEnd(SupremeTestCase):
    def test_full_mission_lifecycle(self):
        core = self.core
        # 1. Mission réelle multi-agents
        sub = core.submit({"objective": "Vérifier la syntaxe Python, valider un JSON et détecter les secrets",
                           "priority": 2})
        mid = sub["mission_id"]
        self.assertGreaterEqual(len(sub["plan"]["tasks"]), 3)
        # 2. Exécution
        res = core.run(mid)
        self.assertEqual(res["state"], "completed")
        # 3. Toutes les tâches terminées
        st = core.status(mid)
        self.assertTrue(all(t["state"] == "done" for t in st["tasks"]))
        # 4. Mémoire collective alimentée avec provenance
        mem = core.memory.search("omnibrain-core", query="Mission", level="collective")
        self.assertTrue(mem["results"])
        self.assertTrue(all(r["source"].startswith("orchestrator:") for r in mem["results"]))
        # 5. Télémétrie réelle
        obs = ObservabilityEngine(core.conn, core.registry, core.budget, core.router)
        kpis = obs.kpis()
        self.assertEqual(kpis["mission_success_rate"], 1.0)
        self.assertIsNotNone(kpis["average_mission_duration_ms"])
        # 6. Rapport dérivé des données réelles
        rep = ReportingEngine(core.conn, core.registry, obs)
        report = rep.global_report()
        self.assertEqual(sum(report["system"]["agents"].values()), 1020)
        md = rep.to_markdown(report)
        self.assertIn("OMNIBRAIN SUPREME", md)
        # 7. Traçabilité complète
        trace = obs.mission_trace(mid)
        self.assertTrue(trace["events"])
        self.assertTrue(trace["tasks"])
        # 8. Coût nul (outils locaux gratuits)
        self.assertEqual(res["cost_usd"], 0.0)


if __name__ == "__main__":
    import unittest
    unittest.main()
