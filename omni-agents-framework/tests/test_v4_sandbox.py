"""Phase 3.2 — hook E2B avec fallback local tracé."""

import unittest

from omni.sandbox import Sandbox


class FakeExecution:
    def __init__(self, stdout="", stderr="", exit_code=0):
        self.stdout, self.stderr, self.exit_code = stdout, stderr, exit_code


class FakeE2B:
    def __init__(self, *, fail=False, **kwargs):
        if fail:
            raise RuntimeError("E2B indisponible")
        self.kwargs = kwargs

    def run_code(self, code):
        return FakeExecution(stdout=f"e2b:{code.strip()[:20]}")

    # Compatibilité SDK JS / runCode.
    @property
    def runCode(self):
        return self.run_code


class SandboxTests(unittest.TestCase):
    def test_local_fallback_when_no_api_key(self):
        sandbox = Sandbox(api_key=None)
        result = sandbox.run_code("print(6 * 7)", heavy=True)
        self.assertEqual(result.backend, "local")
        self.assertEqual(result.stdout.strip(), "42")
        self.assertTrue(result.ok)
        self.assertIn("e2b_not_configured", result.fallback_reason)
        self.assertTrue(result.heavy)
        self.assertGreater(result.duration_ms, 0)
        self.assertEqual(sandbox.events[-1]["attempt"], "local")

    def test_e2b_failure_falls_back_to_local_with_reason(self):
        sandbox = Sandbox(api_key="fake", e2b_factory=lambda: FakeE2B(fail=True))
        result = sandbox.run_code("print('fallback ok')")
        self.assertEqual(result.backend, "local")
        self.assertEqual(result.stdout.strip(), "fallback ok")
        self.assertIn("e2b_unavailable", result.fallback_reason)

    def test_e2b_success_uses_remote_backend(self):
        sandbox = Sandbox(api_key="fake", e2b_factory=lambda: FakeE2B())
        result = sandbox.run_code("print('remote')")
        self.assertEqual(result.backend, "e2b")
        self.assertTrue(result.stdout.startswith("e2b:"))
        self.assertTrue(result.ok)

    def test_syntax_error_is_reported_not_swallowed(self):
        result = Sandbox(api_key=None).run_code("def broken(:")
        self.assertEqual(result.backend, "local")
        self.assertNotEqual(result.exit_code, 0)
        self.assertFalse(result.ok)
        self.assertIn("SyntaxError", result.stderr)

    def test_timeout_is_bounded(self):
        result = Sandbox(api_key=None, timeout_s=0.3).run_code("import time; time.sleep(3)")
        self.assertEqual(result.backend, "local")
        self.assertEqual(result.exit_code, 124)
        self.assertIn("timeout", result.error)

    def test_unsupported_language_is_refused_explicitly(self):
        result = Sandbox(api_key=None).run_code("SELECT 1", language="sql")
        self.assertEqual(result.backend, "none")
        self.assertEqual(result.exit_code, 2)
        self.assertIn("non supporté", result.error)

    def test_local_environment_is_isolated(self):
        result = Sandbox(api_key=None).run_code("import sys; print('OK' if sys.flags.isolated else 'NOT')")
        self.assertIn("OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
