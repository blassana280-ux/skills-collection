"""Phase 2.1 — mémoire d'orchestration persistante SQLite."""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from omni.memory import store as store_module
from omni.memory.store import MemoryStore, SCHEMA_VERSION, redact

TABLES = {
    "missions", "escouades", "resultats", "echecs", "recettes",
    "prompt_iterations", "benchmarks", "autofix_runs", "orchestration_logs",
}


class MemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "omnibrain.sqlite3"
        self.store = MemoryStore(self.db)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_schema_has_all_required_tables(self):
        with sqlite3.connect(self.db) as conn:
            names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue(TABLES.issubset(names), msg=f"tables manquantes : {TABLES - names}")
        with sqlite3.connect(self.db) as conn:
            version = conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()[0]
        self.assertEqual(version, str(SCHEMA_VERSION))

    def test_record_mission_and_api_module_level(self):
        mid = self.store.record_mission({"project_type": "fintech", "title": "Paiement", "spec": "Orange Money"})
        row = self.store.get_mission(mid)
        self.assertEqual(row["project_type"], "fintech")
        self.assertEqual(row["verdict"], "NEEDS WORK")
        self.store.update_mission(mid, status="done", verdict="PASS")
        self.assertEqual(self.store.get_mission(mid)["verdict"], "PASS")
        with mock.patch.object(store_module, "_STORE", self.store):
            mid2 = store_module.record_mission("Mission API", project_type="api")
            self.assertTrue(self.store.get_mission(mid2))
            self.assertEqual(store_module.get_recettes("fintech"), [])

    def test_squads_results_and_failures_are_linked(self):
        mid = self.store.record_mission({"project_type": "qa"})
        sid = self.store.record_squad(mid, "escouade-qa", wave=1)
        self.store.record_result(mid, "qa-test", escouade_id=sid, duration_ms=12.5, tokens_in=30, tokens_out=90,
                                 artifacts=["rapport.md"], evidence=["sortie CI"])
        self.store.record_failure(mid, "qa-test", "qa-test", "timeout", "durée > seuil")
        self.assertEqual(len(self.store.squads_for(mid)), 1)
        result = self.store.results_for(mid)[0]
        self.assertEqual(result["tokens_out"], 90)
        self.assertEqual(json.loads(result["artifacts"]), ["rapport.md"])
        self.assertEqual(self.store.failures_for("qa-test")[0]["error_type"], "timeout")
        self.assertEqual(self.store.stats()["echecs"], 1)

    def test_recettes_par_type_de_projet(self):
        mid = self.store.record_mission({"project_type": "cloud"})
        self.store.upsert_recette("cloud", "spec-tests-deploy", ["spécifier", "tester", "déployer"],
                                  success_delta=3, source_mission=mid)
        self.store.upsert_recette("fintech", "kyc-review", ["kyc", "revue"], success_delta=1)
        cloud = self.store.get_recettes("cloud")
        self.assertEqual(len(cloud), 1)
        self.assertEqual(cloud[0]["steps"], ["spécifier", "tester", "déployer"])
        self.assertGreater(cloud[0]["score"], 0.5)
        self.assertEqual(len(self.store.get_recettes()), 2)
        self.assertEqual(len(self.store.get_recettes(min_success=2)), 1)
        self.assertEqual(self.store.get_recettes("inconnu"), [])

    def test_persistence_across_reopen(self):
        mid = self.store.record_mission({"project_type": "memory", "title": "Persistance"})
        self.store.upsert_recette("memory", "pattern-stable", ["étape"], success_delta=1, source_mission=mid)
        self.store.log("agent", "operator", "run", {"ok": True})
        self.store.close()
        reopened = MemoryStore(self.db)
        try:
            self.assertEqual(reopened.get_mission(mid)["title"], "Persistance")
            self.assertEqual(len(reopened.get_recettes("memory")), 1)
            self.assertEqual(reopened.logs()[0]["action"], "run")
        finally:
            reopened.close()

    def test_secrets_are_redacted_before_persistence(self):
        secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        mid = self.store.record_mission({"title": f"token={secret}", "metadata": {"api_key": "supersecret"}})
        self.store.record_failure(mid, "agent", "agent", "leak", f"password={secret}")
        with sqlite3.connect(self.db) as conn:
            dump = "\n".join(str(r) for r in conn.execute("SELECT * FROM missions"))
            dump += "\n".join(str(r) for r in conn.execute("SELECT message FROM echecs"))
        self.assertNotIn(secret, dump)
        self.assertIn("[REDACTED]", dump)
        self.assertIn("[REDACTED]", redact({"token": "abc123"}))

    def test_in_memory_store_is_isolated(self):
        other = MemoryStore(":memory:")
        try:
            self.assertEqual(other.stats()["missions"], 0)
            other.record_mission("isolement")
            self.assertEqual(other.stats()["missions"], 1)
            self.assertEqual(self.store.stats()["missions"], 0)
        finally:
            other.close()


if __name__ == "__main__":
    unittest.main()
