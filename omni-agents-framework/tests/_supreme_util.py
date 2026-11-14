"""Utilitaire de test SUPREME : base SQLite temporaire isolée."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from supreme.db import connect, init_db
from supreme.orchestrator import OmniBrainCore


class SupremeTestCase(unittest.TestCase):
    """Chaque test dispose d'une base temporaire fraîche (pas de pollution)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "test.db"
        self.conn = connect(self.db_path)
        init_db(self.conn)
        self.core = OmniBrainCore(conn=self.conn)
        self.core.registry.sync_catalog()

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()

    def tool_agent(self, division="D02"):
        for a in self.core.registry.list(division=division, kind="specialist"):
            rep = next(e for e in a["profile"]["eval_tests"] if e["id"] == "representative")
            if rep["mode"] == "tool":
                return a
        raise AssertionError("aucun agent outil trouvé")

    def llm_agent(self, division="D02"):
        for a in self.core.registry.list(division=division, kind="specialist"):
            rep = next(e for e in a["profile"]["eval_tests"] if e["id"] == "representative")
            if rep["mode"] == "llm":
                return a
        raise AssertionError("aucun agent LLM trouvé")
