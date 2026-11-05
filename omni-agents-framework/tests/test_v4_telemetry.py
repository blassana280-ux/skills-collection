"""Phase 4.1 — observabilité : JSON + rapport markdown par mission."""

import json
import tempfile
import unittest
from pathlib import Path

from omni.memory.store import MemoryStore
from omni.telemetry import WaveTelemetry, from_memory, write_mission_report


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _telemetry(self):
        t = WaveTelemetry("mission-t1", project_type="fintech")
        t.record("frontend-ui", wave=1, duration_ms=12.5, tokens_in=100, tokens_out=240)
        t.record("revue_adverse", wave=2, duration_ms=4.0, tokens_in=20, tokens_out=60)
        t.record("tests", wave=2, duration_ms=8.0, tokens_in=10, tokens_out=30)
        t.record("verification", wave=3, duration_ms=2.0, tokens_in=5, tokens_out=15)
        t.record("devops-sre", wave=1, duration_ms=3.0, status="failed", verdict="NEEDS WORK", error="timeout")
        return t

    def test_summary_totals_and_failure_rate(self):
        s = self._telemetry().summary()
        self.assertEqual(s["totals"]["agents"], 5)
        self.assertEqual(s["totals"]["failures"], 1)
        self.assertEqual(s["totals"]["failure_rate"], 0.2)
        self.assertEqual(s["totals"]["tokens_in"], 135)
        self.assertEqual(s["totals"]["tokens_out"], 345)
        self.assertEqual(s["waves"], [1, 2, 3])
        self.assertTrue(all(s["reinforcements"].values()))

    def test_json_export_and_markdown_are_consistent(self):
        t = self._telemetry()
        payload = t.export_json(self.out / "telemetry.json")
        on_disk = json.loads((self.out / "telemetry.json").read_text(encoding="utf-8"))
        self.assertEqual(on_disk, payload)
        md = t.render_markdown()
        self.assertIn("# Rapport de mission — `mission-t1`", md)
        self.assertIn("Taux d'échec", md)
        self.assertIn("20.00%", md)
        self.assertIn("`frontend-ui`", md)
        self.assertIn("Renforts obligatoires", md)
        self.assertIn("Expert risque : présent", md)
        self.assertIn(str(payload["totals"]["tokens_total"]), md)

    def test_empty_wave_still_exports(self):
        t = WaveTelemetry("mission-vide")
        s = t.export_json(self.out / "empty.json")
        self.assertEqual(s["totals"]["failure_rate"], 0.0)
        self.assertIn("_aucun agent_", t.render_markdown())

    def test_start_end_measures_real_elapsed_time(self):
        t = WaveTelemetry("m")
        t.start_agent("agent-x", wave=1)
        t.end_agent("agent-x", tokens_in=5)
        self.assertGreaterEqual(t.summary()["agents"][0]["duration_ms"], 0)

    def test_from_memory_and_report_writer(self):
        store = MemoryStore(self.out / "tele.sqlite3")
        try:
            mid = store.record_mission({"project_type": "qa", "title": "rapport"})
            store.record_result(mid, "qa-test", duration_ms=9.0, tokens_in=11, tokens_out=22)
            t = from_memory(store, mid)
            self.assertEqual(t.summary()["totals"]["tokens_out"], 22)
            json_path, md_path = write_mission_report(t, self.out / "reports")
            self.assertTrue(json_path.is_file())
            self.assertTrue(md_path.is_file())
            self.assertIn("Rapport de mission", md_path.read_text(encoding="utf-8"))
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
