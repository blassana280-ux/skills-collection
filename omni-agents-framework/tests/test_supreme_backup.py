"""Tests sauvegarde/restauration : intégrité, refus de sauvegarde corrompue."""
import tempfile
from pathlib import Path

from supreme.backup import BackupManager
from tests._supreme_util import SupremeTestCase


class TestBackup(SupremeTestCase):
    def test_backup_and_restore(self):
        # données réelles
        sub = self.core.submit({"objective": "Vérifier Python"})
        self.core.run(sub["mission_id"])
        with tempfile.TemporaryDirectory() as td:
            import supreme.backup as bk
            old = bk.BACKUP_DIR
            bk.BACKUP_DIR = Path(td)
            try:
                mgr = BackupManager(self.db_path)
                meta = mgr.backup("test")
                self.assertEqual(meta["integrity"], "ok")
                self.assertTrue(Path(meta["db"]).is_file())
                # restaurer vers une cible séparée
                target = Path(td) / "restored.db"
                res = mgr.restore(meta["id"], target=target)
                self.assertEqual(res["integrity"], "ok")
                import sqlite3
                conn = sqlite3.connect(str(target))
                n = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
                conn.close()
                self.assertEqual(n, 1020)
            finally:
                bk.BACKUP_DIR = old

    def test_restore_unknown_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            import supreme.backup as bk
            old = bk.BACKUP_DIR
            bk.BACKUP_DIR = Path(td)
            try:
                mgr = BackupManager(self.db_path)
                with self.assertRaises(KeyError):
                    mgr.restore("inexistante")
            finally:
                bk.BACKUP_DIR = old


if __name__ == "__main__":
    import unittest
    unittest.main()
