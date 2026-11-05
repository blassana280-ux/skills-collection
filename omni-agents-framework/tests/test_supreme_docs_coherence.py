"""Audit de cohérence documentaire SUPREME — empêche la dérive version/tests.

Vérifie que les documents de livraison courante affichent la même version SUPREME
et le même nombre de tests que la découverte unittest réelle. Les sections
historiques du changelog peuvent conserver leurs anciens décomptes.
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
            FRAMEWORK_ROOT / "docs/supreme/EXECUTION-REPORT.md",
            FRAMEWORK_ROOT / "docs/supreme/TEST-MATRIX.md",
            FRAMEWORK_ROOT / "docs/supreme/CONTINUITY.md",
            FRAMEWORK_ROOT / "docs/supreme/ECOSYSTEM.md",
            FRAMEWORK_ROOT / "docs/supreme/CHANGELOG-SUPREME.md",
        ]
        for p in docs:
            self.assertIn(SUPREME_VERSION, p.read_text(encoding="utf-8"), f"version absente dans {p}")

    def test_test_matrix_counts_match_real_discovery(self):
        total, v4, supreme = _discover_counts()
        text = (FRAMEWORK_ROOT / "docs/supreme/TEST-MATRIX.md").read_text(encoding="utf-8")
        m = re.search(r"\*\*(\d+) tests verts\*\* = \*\*(\d+) V4/non-SUPREME \+ (\d+) SUPREME\*\*", text)
        self.assertIsNotNone(m, "décompte courant introuvable dans TEST-MATRIX.md")
        self.assertEqual((int(m.group(1)), int(m.group(2)), int(m.group(3))), (total, v4, supreme))
        self.assertEqual(total, v4 + supreme)


if __name__ == "__main__":
    unittest.main()
