"""Tests budget : quotas, coupure, alertes, historique."""
from supreme.budget import BudgetController
from tests._supreme_util import SupremeTestCase


class TestBudget(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.budget = BudgetController(self.conn)

    def test_quota_and_remaining(self):
        self.budget.set_quota("mission", "m1", 1.0)
        self.assertEqual(self.budget.remaining("mission", "m1"), 1.0)
        self.budget.record("mission", "m1", 0.3, mission_id="m1")
        self.assertAlmostEqual(self.budget.remaining("mission", "m1"), 0.7)

    def test_cutoff_on_exceed(self):
        self.budget.set_quota("mission", "m1", 0.5)
        res = self.budget.record("mission", "m1", 0.6, mission_id="m1")
        self.assertFalse(res["recorded"])
        self.assertEqual(self.budget.mission_cost("m1"), 0.0)

    def test_alert_at_90_percent(self):
        self.budget.set_quota("agent", "a1", 1.0)
        res = self.budget.record("agent", "a1", 0.95)
        self.assertTrue(res["recorded"])
        self.assertTrue(res["alerts"])

    def test_extra_scopes_enforced(self):
        self.budget.set_quota("division", "D02", 0.2)
        res = self.budget.record("mission", "m1", 0.3, mission_id="m1", extra_scopes=[("division", "D02")])
        self.assertFalse(res["recorded"])

    def test_local_tools_zero_cost(self):
        res = self.budget.record("mission", "m1", 0.0, mission_id="m1", provider="local-tool")
        self.assertTrue(res["recorded"])
        self.assertEqual(self.budget.mission_cost("m1"), 0.0)

    def test_invalid_scope_rejected(self):
        with self.assertRaises(ValueError):
            self.budget.set_quota("invalide", "x", 1.0)


if __name__ == "__main__":
    import unittest
    unittest.main()
