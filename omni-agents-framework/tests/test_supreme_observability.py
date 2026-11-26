"""Tests observabilité : KPIs réels, null si indisponible, pas de secrets."""
from supreme.observability import ObservabilityEngine
from tests._supreme_util import SupremeTestCase


class TestObservability(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.obs = ObservabilityEngine(self.conn, self.core.registry, self.core.budget, self.core.router)

    def test_kpis_null_when_no_data(self):
        k = self.obs.kpis()
        self.assertIsNone(k["agent_success_rate"])
        self.assertIsNone(k["mission_success_rate"])
        self.assertIsNone(k["model_routing_accuracy"])

    def test_kpis_real_after_mission(self):
        sub = self.core.submit({"objective": "Vérifier Python et JSON"})
        self.core.run(sub["mission_id"])
        k = self.obs.kpis()
        self.assertEqual(k["agent_success_rate"], 1.0)
        self.assertEqual(k["mission_success_rate"], 1.0)
        self.assertIsNotNone(k["average_mission_duration_ms"])
        self.assertEqual(k["cost_per_mission_usd"], 0.0)

    def test_duplicate_rate_zero(self):
        self.assertEqual(self.obs.kpis()["duplicate_agent_rate"], 0.0)

    def test_model_availability_honest(self):
        avail = self.obs.kpis()["model_availability"]
        self.assertEqual(avail["available"], 0)

    def test_system_status(self):
        s = self.obs.system_status()
        self.assertEqual(sum(s["agents"].values()), 1020)

    def test_mission_trace(self):
        sub = self.core.submit({"objective": "Vérifier Python"})
        mid = sub["mission_id"]
        self.core.run(mid)
        trace = self.obs.mission_trace(mid)
        self.assertTrue(trace["events"])
        self.assertTrue(trace["metrics"])
        self.assertTrue(trace["tasks"])

    def test_no_secrets_in_events(self):
        from supreme.db import log_event
        log_event(self.conn, "info", "test", "clé api_key=sk-" + "b" * 30)
        events = self.conn.execute("SELECT message FROM events ORDER BY id DESC LIMIT 1").fetchone()
        self.assertNotIn("sk-" + "b" * 30, events["message"])


if __name__ == "__main__":
    import unittest
    unittest.main()
