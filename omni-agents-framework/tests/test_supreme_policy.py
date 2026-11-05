"""Tests du Policy Engine : niveaux de risque, actions protégées, approbations."""
from supreme.policy import PolicyEngine, classify_action, requires_approval
from tests._supreme_util import SupremeTestCase


class TestPolicy(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.policy = PolicyEngine(self.conn)

    def test_risk_classification(self):
        self.assertEqual(classify_action("read"), "low")
        self.assertEqual(classify_action("run_mission"), "medium")
        self.assertEqual(classify_action("merge_pr"), "critical")
        self.assertTrue(requires_approval("high"))
        self.assertTrue(requires_approval("critical"))
        self.assertFalse(requires_approval("low"))

    def test_protected_action_denied_to_machine(self):
        self.core.policy.rbac.assign("agent-x", "operator")
        verdict = self.policy.check("agent-x", "change_policy")
        self.assertFalse(verdict["allowed"])
        self.assertTrue(verdict["approval_required"])

    def test_human_can_approve_critical(self):
        verdict = self.policy.check("Lassana", "merge_pr", human_approval=True)
        self.assertTrue(verdict["allowed"])

    def test_approval_flow(self):
        aid = self.policy.request_approval("deploy", "agent-x", {"reason": "test"})
        self.assertEqual(len(self.policy.pending_approvals()), 1)
        res = self.policy.decide(aid, True, "Lassana")
        self.assertEqual(res["status"], "approved")
        self.assertEqual(len(self.policy.pending_approvals()), 0)

    def test_machine_cannot_decide(self):
        aid = self.policy.request_approval("deploy", "agent-x")
        self.core.policy.rbac.assign("robot", "admin")
        with self.assertRaises(PermissionError):
            self.policy.decide(aid, True, "robot")

    def test_double_decision_rejected(self):
        aid = self.policy.request_approval("deploy", "agent-x")
        self.policy.decide(aid, True, "Lassana")
        with self.assertRaises(ValueError):
            self.policy.decide(aid, False, "Lassana")


if __name__ == "__main__":
    import unittest
    unittest.main()
