"""Phase 3.1 — graphe d'état déterministe, gates HITL, renforts obligatoires."""

import tempfile
import unittest
from pathlib import Path

from omni.graph import GraphState, ProtectedNodeError, StateGraph, build_pipeline, run_pipeline
from omni.memory.store import MemoryStore
from omni.sandbox import Sandbox


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = MemoryStore(Path(self.tmp.name) / "graph.sqlite3")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_deterministic_topological_order(self):
        graph = build_pipeline()
        self.assertEqual(graph.node_names(),
                         ["spec", "implementation", "revue_adverse", "tests", "verification"])
        self.assertEqual(graph.order(), graph.node_names())

    def test_cycle_is_rejected(self):
        graph = StateGraph("cycle")
        node = lambda state: state  # noqa: E731
        graph.add_node("a", node).add_node("b", node)
        graph.add_edge("a", "b").add_edge("b", "a").set_entry("a")
        with self.assertRaisesRegex(ValueError, "cyclique"):
            graph.order()

    def test_mandatory_reinforcements_cannot_be_removed(self):
        graph = build_pipeline()
        for name in ("revue_adverse", "tests", "verification"):
            with self.assertRaises(ProtectedNodeError):
                graph.remove_node(name)
        graph.remove_node("spec")
        self.assertNotIn("spec", graph.node_names())

    def test_missing_human_approval_escalates_to_lassana(self):
        result = run_pipeline("Livrer une API de paiement", project_type="fintech", store=self.store)
        state = result.state
        self.assertEqual(state.verdict, "NEEDS WORK")
        self.assertTrue(state.pending_human)
        self.assertEqual(state.stopped_at, "revue_adverse")
        self.assertEqual(state.escalations[0]["approver"], "Lassana")
        self.assertEqual(state.escalations[0]["status"], "AWAITING_HUMAN")
        nodes = [h["node"] for h in state.history if h["kind"] == "node"]
        self.assertEqual(nodes, ["spec", "implementation", "revue_adverse"])
        self.assertNotIn("tests", nodes)
        self.assertEqual(self.store.get_mission(result.mission_id)["verdict"], "NEEDS WORK")
        self.assertTrue(any(log["action"] == "escalade" for log in self.store.logs()))

    def test_approved_gates_reach_pass_and_reinforcements(self):
        result = run_pipeline(
            "Durcir le pipeline CI", project_type="devops", store=self.store,
            approvals={"revue_adverse": True, "verification": True},
        )
        self.assertEqual(result.state.verdict, "PASS")
        self.assertFalse(result.state.pending_human)
        self.assertEqual([h["node"] for h in result.state.history if h["kind"] == "node"],
                         build_pipeline().node_names())
        for key in ("spec", "implementation", "revue_adverse", "tests", "registre_risques"):
            self.assertIn(key, result.state.artifacts)
        self.assertEqual(len(self.store.get_recettes("devops")), 1)

    def test_gate_checks_block_on_empty_spec_and_red_tests(self):
        blocked = run_pipeline("   ", store=self.store,
                               approvals={"revue_adverse": True, "verification": True})
        self.assertEqual(blocked.state.stopped_at, "spec")
        red = run_pipeline("Tests rouges", store=self.store, test_runner=lambda s: "FAILED — 1 test rouge",
                           approvals={"revue_adverse": True, "verification": True})
        self.assertEqual(red.state.stopped_at, "tests")
        self.assertEqual(red.state.verdict, "NEEDS WORK")

    def test_adverse_review_blocks_a_secret_in_implementation(self):
        result = run_pipeline(
            "Calcul lourd", store=self.store, sandbox=Sandbox(),
            heavy_code="print('api_key=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123')",
            approvals={"revue_adverse": True, "verification": True},
        )
        self.assertIn("SECRET", result.state.review)
        self.assertEqual(result.state.stopped_at, "revue_adverse")

    def test_two_runs_are_deterministic(self):
        args = dict(project_type="qa", store=self.store)
        first = run_pipeline("Même mission", **args)
        second = run_pipeline("Même mission", **args)
        def trace(state):
            return [(h["step"], h["kind"], h["node"], h.get("status", "")) for h in state.history]
        self.assertEqual(trace(first.state), trace(second.state))
        self.assertEqual(first.state.verdict, second.state.verdict)
        self.assertEqual(first.state.escalations, second.state.escalations)

    def test_state_snapshot_is_serialisable(self):
        import json
        state = GraphState(mission_id="m-1", spec="spécification")
        json.dumps(state.snapshot())
        self.assertEqual(state.verdict, "NEEDS WORK")


if __name__ == "__main__":
    unittest.main()
