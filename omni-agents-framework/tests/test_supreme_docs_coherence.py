"""Audit de cohérence documentaire SUPREME — empêche la dérive version/tests.

Vérifie que les documents de livraison courante affichent la même version SUPREME
et le même nombre de tests que la découverte unittest réelle. Les sections
historiques du changelog peuvent conserver leurs anciens décomptes.

`EXECUTION-REPORT.md` reste le procès-verbal historique de la livraison 1.3.0 et
n'est pas réécrit : le rapport de livraison courant est `FINAL-COMPLETION-REPORT.md`.
"""
import re
import unittest
from pathlib import Path

from supreme import SUPREME_VERSION

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = FRAMEWORK_ROOT.parent


def _discover_counts():
    suite = unittest.TestLoader().discover(str(FRAMEWORK_ROOT / "tests"))
    total = v4 = supreme = 0
    def walk(s):
        nonlocal total, v4, supreme
        for x in s:
            if isinstance(x, unittest.TestSuite):
                walk(x)
            else:
                total += 1
                if "test_supreme_" in x.__class__.__module__:
                    supreme += 1
                else:
                    v4 += 1
    walk(suite)
    return total, v4, supreme


class TestDocsCoherence(unittest.TestCase):
    def test_current_version_in_delivery_docs(self):
        docs = [
            REPO_ROOT / "OMNIBRAIN-SUPREME.md",
            REPO_ROOT / "AGENTS.md",
            FRAMEWORK_ROOT / "docs/supreme/FINAL-COMPLETION-REPORT.md",
            FRAMEWORK_ROOT / "docs/supreme/TEST-MATRIX.md",
            FRAMEWORK_ROOT / "docs/supreme/CONTINUITY.md",
            FRAMEWORK_ROOT / "docs/supreme/ECOSYSTEM.md",
            FRAMEWORK_ROOT / "docs/supreme/CHANGELOG-SUPREME.md",
        ]
        for p in docs:
            self.assertIn(SUPREME_VERSION, p.read_text(encoding="utf-8"), f"version absente dans {p}")

    def test_historical_execution_report_is_preserved(self):
        """Le PV 1.3.0 reste consultable et daté : pas de réécriture d'historique."""
        text = (FRAMEWORK_ROOT / "docs/supreme/EXECUTION-REPORT.md").read_text(encoding="utf-8")
        self.assertIn("livraison 1.3.0", text)
        self.assertIn("2026-11-05", text)

    def test_confirmation_phrases_match_between_code_and_docs(self):
        """Une consigne humaine documentée doit être exactement celle exigée par le code.

        Le CLI transmet `--confirm` sans le coder en dur : on vérifie donc les
        constantes du code contre les documents, et que le CLI expose bien l'option.
        """
        from supreme.activation import QUARANTINE_RELEASE_CONFIRM
        from supreme.provider_control import AUTH_CONFIRM, CONTEXT_CONFIRM, PRICE_CONFIRM
        from supreme.guardian import RESOLVE_CONFIRM
        docs = "\n".join(p.read_text(encoding="utf-8") for p in
                         (FRAMEWORK_ROOT / "docs/supreme").glob("*.md"))
        cli = (FRAMEWORK_ROOT / "supreme/__main__.py").read_text(encoding="utf-8")
        for phrase in (QUARANTINE_RELEASE_CONFIRM, AUTH_CONFIRM, CONTEXT_CONFIRM, PRICE_CONFIRM,
                       "REVOQUER INFERENCE"):
            self.assertIn(phrase, docs, f"confirmation absente des docs : {phrase}")
        self.assertIn('"--confirm"', cli)
        self.assertEqual(RESOLVE_CONFIRM, QUARANTINE_RELEASE_CONFIRM)
        self.assertNotIn("JE CONFIRME LA REVUE", docs + cli,
                         "ancienne phrase de confirmation encore documentée")

    def test_test_matrix_counts_match_real_discovery(self):
        total, v4, supreme = _discover_counts()
        text = (FRAMEWORK_ROOT / "docs/supreme/TEST-MATRIX.md").read_text(encoding="utf-8")
        m = re.search(r"\*\*(\d+) tests découverts\*\* = \*\*(\d+) V4/non-SUPREME \+ (\d+) SUPREME\*\*", text)
        self.assertIsNotNone(m, "décompte courant introuvable dans TEST-MATRIX.md")
        self.assertEqual((int(m.group(1)), int(m.group(2)), int(m.group(3))), (total, v4, supreme))
        self.assertEqual(total, v4 + supreme)


if __name__ == "__main__":
    unittest.main()
