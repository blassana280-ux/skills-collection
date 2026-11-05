"""Phase 3.3 — runtime continu, RBAC et logs d'orchestration persistants."""

import tempfile
import unittest
from pathlib import Path

from omni.memory.store import MemoryStore
from omni.sandbox.runtime import IRREVERSIBLE, RBAC, Runtime, RuntimeConfig


class RBACTests(unittest.TestCase):
    def setUp(self):
        self.rbac = RBAC({"bot-ci": "operator", "lecteur": "viewer", "qa-bot": "reviewer"})

    def test_roles_and_permissions(self):
        self.assertTrue(self.rbac.allow("bot-ci", "run_mission"))
        self.assertFalse(self.rbac.allow("lecteur", "plan"))
        self.assertTrue(self.rbac.allow("qa-bot", "approve_gate"))
        self.assertFalse(self.rbac.allow("inconnu", "run_mission"))
        with self.assertRaises(PermissionError):
            self.rbac.check("lecteur", "run_mission")
        with self.assertRaises(ValueError):
            self.rbac.assign("x", "superuser")

    def test_irreversible_actions_never_allowed_to_machines(self):
        for action in IRREVERSIBLE:
            self.assertFalse(self.rbac.allow("bot-ci", action, human_approval=True), msg=action)
            self.assertFalse(self.rbac.allow("qa-bot", action, human_approval=True), msg=action)
        self.assertFalse(self.rbac.allow("Lassana", "merge_pr"))
        self.assertTrue(self.rbac.allow("Lassana", "merge_pr", human_approval=True))
        self.assertFalse(self.rbac.allow("AutreHumain", "merge_pr", human_approval=True))
        with self.assertRaises(PermissionError):
            self.rbac.check("bot-ci", "write_main")


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = MemoryStore(Path(self.tmp.name) / "runtime.sqlite3")
        self.runtime = Runtime(
            self.store,
            config=RuntimeConfig(interval_s=0, max_ticks=2, artifacts_dir=Path(self.tmp.name) / "out"),
        )

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_submit_tick_persists_logs_and_escalation(self):
        mid = self.runtime.submit("Mission de service", project_type="service")
        self.assertEqual(self.store.get_mission(mid)["status"], "queued")
        handled = self.runtime.tick()
        self.assertEqual(handled, [mid])
        mission = self.store.get_mission(mid)
        self.assertEqual(mission["status"], "blocked")
        self.assertEqual(mission["verdict"], "NEEDS WORK")
        actions = [log["action"] for log in self.store.logs()]
        for expected in ("service_start", "submit", "tick_start", "tick_done", "escalade", "pipeline_done"):
            self.assertIn(expected, actions)
        self.assertTrue((Path(self.tmp.name) / "out" / f"rapport-mission-{mid}.md").is_file())
        self.assertTrue(self.store.logs())

    def test_bounded_scheduler_never_loops_forever(self):
        for i in range(3):
            self.runtime.submit(f"Mission {i}")
        self.assertEqual(self.runtime.start(), 2)
        self.assertEqual(len(self.runtime.queue), 1)
        self.assertEqual(self.store.logs()[0]["action"], "service_stop")

    def test_stop_halts_processing(self):
        mid = self.runtime.submit("Mission arrêtée")
        self.runtime.stop()
        self.assertEqual(self.runtime.tick(), [])
        self.assertEqual(self.store.get_mission(mid)["status"], "queued")

    def test_submit_requires_permission(self):
        with self.assertRaises(PermissionError):
            self.runtime.submit("interdit", actor="lecteur")


if __name__ == "__main__":
    unittest.main()
