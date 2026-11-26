"""Intelligence OmniBrain : explicabilité des choix, arbitrage des missions complexes,
activation des agents LLM sur appel réel (stub local = local réel, PAS fournisseur IA réel).
"""
import os
import unittest
from unittest import mock

import supreme.router as router_mod
from supreme.evaluation import EvaluationEngine
from supreme.orchestrator import OmniBrainCore
from supreme.router import ModelRouter, ModelSpec, Provider
from supreme.providers import ProviderClient
from tests._supreme_util import SupremeTestCase
from tests.test_supreme_providers import start_stub, _clean_env

COMPLEX_OBJECTIVE = ("analyser et vérifier puis contrôler ensuite valider, tester et auditer "
                     "puis comparer les résultats et synthétiser")


def _stub_provider(base):
    return Provider("mistral", "STUB_KEY", base, [
        ModelSpec("mistral", "mistral-small-latest", ("general",), 0.001, 0.001, 8000, True, True)],
        kind="openai", priority=1)


class TestExplainability(SupremeTestCase):
    def test_plan_has_explanation_and_task_why(self):
        sub = self.core.submit({"objective": "Vérifier la syntaxe Python et le JSON"})
        plan = sub["plan"]
        self.assertIn("explanation", plan)
        for key in ("classification", "squad_size", "strategy", "verification", "arbitrage"):
            self.assertIn(key, plan["explanation"])
        self.assertTrue(all(t.get("why") for t in plan["tasks"]))

    def test_explicit_task_why(self):
        agent = self.tool_agent("D02")
        sub = self.core.submit({"objective": "test", "tasks": [{"agent_id": agent["id"]}]})
        self.assertIn("explicitement désigné", sub["plan"]["tasks"][0]["why"])

    def test_explanation_persisted_in_mission(self):
        sub = self.core.submit({"objective": "Vérifier Python"})
        st = self.core.status(sub["mission_id"])
        self.assertIn("explanation", st["plan"])


class TestCouncilArbitration(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.server, self.thread, self.base = start_stub()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def test_complex_mission_council_unavailable_without_provider(self):
        with mock.patch.dict(os.environ, _clean_env(), clear=True):
            core = OmniBrainCore(conn=self.conn)
            sub = core.submit({"objective": COMPLEX_OBJECTIVE})
            self.assertEqual(sub["plan"]["classification"]["level"], "complexe")
            res = core.run(sub["mission_id"])
        self.assertIn("council", res)
        self.assertEqual(res["council"]["status"], "unavailable")  # honnête, pas fabriqué

    def test_complex_mission_council_needs_review_when_stub_evidence_not_referenced(self):
        with mock.patch.object(router_mod, "DEFAULT_PROVIDERS", [_stub_provider(self.base)]), \
             mock.patch.dict(os.environ, {**_clean_env(), "STUB_KEY": "stub-secret-123"}, clear=True):
            core = OmniBrainCore(conn=self.conn)
            sub = core.submit({"objective": COMPLEX_OBJECTIVE})
            res = core.run(sub["mission_id"])
        self.assertEqual(res["state"], "completed")
        self.assertEqual(res["council"]["status"], "needs_review")
        self.assertIsNone(res["council"]["decision"])
        self.assertFalse(res["council"]["verified"])
        # Une preuve auto-déclarée non référencée ne devient pas une décision mémorisée.
        mem = self.core.memory.search("omnibrain-core", query="Conseil", level="central")
        self.assertFalse(any("council" in (r.get("source") or "") for r in mem["results"]))

    def test_simple_mission_no_council(self):
        sub = self.core.submit({"objective": "Vérifier Python"})
        res = self.core.run(sub["mission_id"])
        self.assertNotIn("council", res)


class TestLlmEvaluation(SupremeTestCase):
    def setUp(self):
        super().setUp()
        self.server, self.thread, self.base = start_stub()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def test_llm_agent_deferred_without_router(self):
        agent = self.llm_agent("D02")
        ev = EvaluationEngine(self.conn, self.core.registry)
        res = ev.run_profile_tests(agent["id"])
        self.assertTrue(res["results"]["representative"]["deferred"])

    def test_llm_agent_not_activated_on_local_stub_call(self):
        agent = self.llm_agent("D02")
        with mock.patch.dict(os.environ, {**_clean_env(), "STUB_KEY": "stub-secret-123"}, clear=True):
            router = ModelRouter(providers=[_stub_provider(self.base)], allow_network=True,
                                 client=ProviderClient(timeout=10))
            ev = EvaluationEngine(self.conn, self.core.registry, router=router)
            res = ev.activate_agent(agent["id"])
        self.assertFalse(res["activated"])
        self.assertIn("non activant", res["results"]["representative"]["evidence"])
        self.assertNotEqual(self.core.registry.get(agent["id"])["status"], "monitored")

    def test_llm_agent_failed_call_not_deferred(self):
        self.server.mode = "500"
        agent = self.llm_agent("D02")
        with mock.patch.dict(os.environ, {**_clean_env(), "STUB_KEY": "stub-secret-123"}, clear=True):
            router = ModelRouter(providers=[_stub_provider(self.base)], allow_network=True,
                                 client=ProviderClient(timeout=10))
            ev = EvaluationEngine(self.conn, self.core.registry, router=router)
            res = ev.run_profile_tests(agent["id"])
        rep = res["results"]["representative"]
        self.assertFalse(rep["passed"])
        self.assertFalse(rep.get("deferred"))  # échec réel, pas différé
        self.assertIn("échoué", rep["evidence"])


if __name__ == "__main__":
    unittest.main()
