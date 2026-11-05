import os
import subprocess
import sys
import unittest
from pathlib import Path

from tests import ROOT


class WrapperTests(unittest.TestCase):
    def test_bin_wrapper_works_from_other_directory(self):
        wrapper = ROOT / "bin" / "omnibrain"
        self.assertTrue(wrapper.is_file(), "bin/omnibrain absent")
        self.assertTrue(os.access(wrapper, os.X_OK), "bin/omnibrain non exécutable")
        result = subprocess.run(
            [str(wrapper), "validate"],
            cwd=Path.home(),  # répertoire étranger au dépôt
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("115 agents", result.stdout)


if __name__ == "__main__":
    unittest.main()
