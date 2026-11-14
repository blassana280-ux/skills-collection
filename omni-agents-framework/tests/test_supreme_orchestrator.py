"""Tests orchestrateur : exécution réelle, parallélisme, dépendances, idempotence,
annulation, reprise, blocage LLM honnête, permissions."""
from tests._supreme_util import SupremeTestCase


class TestOrchestrator(SupremeTestCase):
    def test_submit_and_run_completed(self):
        sub = self.core.submit({"objective": "Vérifier syntaxe Python et valider JSON"})
        res = self.core.run(sub["mission_id"])
        self.assertEqual(res["state"], "completed")
        self.assertEqual(res["cost_usd"], 0.0)
        st = self.core.status(sub["mission_id"])
        self.assertTrue(all(t["state"] == "done" for t in st["tasks"]))

    def test_parallel_independent_tasks(self):
        a = self.tool_agent("D02")
        b = self.tool_agent("D03")
        sub = self.core.submit({"objective": "test parallèle", "tasks": [
            {"agent_id": a["id"], "tool": "json_validate"},
            {"agent_id": b["id"], "tool": "secret_scan"},
        ]})
        res = self.core.run(sub["mission_id"])
        self.assertEqual(res["state"], "completed")
        self.assertEqual(res["tasks"]["done"], 2)

    def test_dependency_order(self):
        a = self.tool_agent("D02")
        mid = "mis-dep-test"
        sub = self.core.submit({"objective": "test dépendances", "mission_id": mid, "tasks": [
            {"agent_id": a["id"], "tool": "json_validate"},
            {"agent_id": a["id"], "tool": "python_syntax_check", "depends_on": [mid + "-t001"]},
        ]})
        res = self.core.run(mid)
        self.assertEqual(res["state"], "completed")
        st = self.core.status(mid)
        t1 = next(t for t in st["tasks"] if t["id"] == mid + "-t001")
        t2 = next(t for t in st["tasks"] if t["id"] == mid + "-t002")
        self.assertEqual(t1["state"], "done")
        self.assertEqual(t2["state"], "done")
        self.assertLessEqual(t1["updated_at"], t2["updated_at"])

    def test_idempotent_rerun(self):
        sub = self.core.submit({"objective": "Vérifier Python"})
        mid = sub["mission_id"]
        self.core.run(mid)
        res2 = self.core.run(mid)
        self.assertEqual(res2["state"], "completed")
        st = self.core.status(mid)
        self.assertTrue(all(t["attempts"] <= 3 for t in st["tasks"]))

    def test_llm_task_blocked_without_provider(self):
        a = self.llm_agent("D02")
        sub = self.core.submit({"objective": "test llm", "tasks": [{"agent_id": a["id"]}]})
        res = self.core.run(sub["mission_id"])
        st = self.core.status(sub["mission_id"])
        self.assertEqual(st["tasks"][0]["state"], "blocked")
        self.assertIn("fournisseur", st["tasks"][0]["error"])

    def test_unauthorized_tool_blocked(self):
        a = self.tool_agent("D02")
        # forcer un outil non autorisé directement en base
        sub = self.core.submit({"objective": "test", "tasks": [{"agent_id": a["id"], "tool": "json_validate"}]})
        tid = sub["plan"]["tasks"][0]["id"]
        self.conn.execute("UPDATE tasks SET tool='secret_scan' WHERE id=?", (tid,))
        self.conn.commit()
        self.core.run(sub["mission_id"])
        st = self.core.status(sub["mission_id"])
        self.assertEqual(st["tasks"][0]["state"], "blocked")

    def test_cancel(self):
        sub = self.core.submit({"objective": "Vérifier Python"})
        self.core.cancel(sub["mission_id"])
        res = self.core.run(sub["mission_id"])
        self.assertEqual(res["state"], "cancelled")

    def test_recovery_resets_abandoned(self):
        sub = self.core.submit({"objective": "Vérifier Python"})
        tid = sub["plan"]["tasks"][0]["id"]
        self.conn.execute("UPDATE tasks SET state='running' WHERE id=?", (tid,))
        self.conn.commit()
        rec = self.core.recover()
        self.assertGreaterEqual(rec["recovered_tasks"], 1)
        self.assertEqual(self.core._task(tid)["state"], "pending")

    def test_memory_and_bus_populated(self):
        sub = self.core.submit({"objective": "Vérifier Python et JSON"})
        self.core.run(sub["mission_id"])
        self.assertGreater(self.core.memory.stats()["total"], 0)
        self.assertGreater(self.core.bus.stats()["total"], 0)


if __name__ == "__main__":
    import unittest
    unittest.main()


class TestConcurrentMissions(SupremeTestCase):
    def test_parallel_missions_thread_safe(self):
        import concurrent.futures
        core = self.core

        def run_mission(i):
            sub = core.submit({"objective": f"Vérifier Python JSON secrets latence cron csv {i}"})
            return core.run(sub["mission_id"])["state"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            states = list(ex.map(run_mission, range(8)))
        self.assertTrue(all(s == "completed" for s in states), states)
        done = self.conn.execute("SELECT COUNT(*) c FROM tasks WHERE state='done'").fetchone()["c"]
        self.assertEqual(done, 24)  # 8 missions x 3 tâches
