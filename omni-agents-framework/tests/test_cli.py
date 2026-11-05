import json
import subprocess
import sys
import unittest
from pathlib import Path

from tests import ROOT


class CliSmokeTests(unittest.TestCase):
    def run_cli(self, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "omnibrain", *args],
            cwd=ROOT,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_validate_exit_zero(self):
        result = self.run_cli("validate")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("115 agents", result.stdout)

    def test_squads_command(self):
        result = self.run_cli("squads")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("security", result.stdout)
        self.assertIn("TOTAL", result.stdout)

    def test_list_squad_filter_and_terse(self):
        result = self.run_cli("list", "--squad", "security", "--terse")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        # Les 11 agents de l'escouade sécurité, et aucun d'une autre.
        self.assertIn("pentester", result.stdout)
        self.assertNotIn("mobile-ios", result.stdout)
        self.assertNotIn("Orchestrateur central", result.stdout)

    def test_stdin_routing(self):
        result = self.run_cli("route", "-", "--json", input_text="Audit sécurité OWASP de l'API.")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        ids = [agent["id"] for agent in payload["squad"]]
        self.assertIn("security", ids)
        self.assertNotIn("omnibrain", ids)

    def test_plan_json_is_serializable(self):
        result = self.run_cli("plan", "examples/task-medium.md", "--format", "json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["wave"], 0)
        self.assertGreaterEqual(len(payload["briefs"]), 1)

    def test_gates_exit_code_needs_work(self):
        bad = Path(ROOT) / "out"
        bad.mkdir(exist_ok=True)
        target = bad / "cli-bad.md"
        target.write_text("# rien\n", encoding="utf-8")
        result = self.run_cli("gates", str(target))
        self.assertEqual(result.returncode, 2)
        self.assertIn("NEEDS WORK", result.stdout)

    def test_version(self):
        result = self.run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("omnibrain", result.stdout)


if __name__ == "__main__":
    unittest.main()
