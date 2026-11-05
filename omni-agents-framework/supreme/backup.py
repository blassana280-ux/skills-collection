"""Backup & Recovery Manager SUPREME — sauvegarde/restauration SQLite + catalogue.

Utilise l'API de backup SQLite (cohérente à chaud). Vérification d'intégrité.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import uuid
from pathlib import Path

from .config import BACKUP_DIR, CATALOG_DIR, DB_PATH, ensure_dirs
from .db import connect, now


class BackupManager:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH

    def backup(self, label: str = "") -> dict:
        ensure_dirs()
        bid = f"bk-{now().replace(':', '').replace('-', '')[:15]}-{uuid.uuid4().hex[:6]}"
        dest_dir = BACKUP_DIR / bid
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_db = dest_dir / "supreme.db"
        src = connect(self.db_path)
        dst = sqlite3.connect(str(dest_db))
        with dst:
            src.backup(dst)
        dst.close()
        src.close()
        # Copie du catalogue versionné
        if CATALOG_DIR.is_dir():
            shutil.copytree(CATALOG_DIR, dest_dir / "catalog", dirs_exist_ok=True)
        integrity = self._integrity(dest_db)
        meta = {"id": bid, "label": label, "created_at": now(), "db": str(dest_db),
                "integrity": integrity, "size_bytes": dest_db.stat().st_size}
        (dest_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        return meta

    def _integrity(self, path: Path) -> str:
        conn = sqlite3.connect(str(path))
        try:
            return conn.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            conn.close()

    def list_backups(self) -> list[dict]:
        ensure_dirs()
        out = []
        for d in sorted(BACKUP_DIR.iterdir()):
            meta = d / "meta.json"
            if meta.is_file():
                out.append(json.loads(meta.read_text(encoding="utf-8")))
        return out

    def restore(self, backup_id: str, target: Path | None = None) -> dict:
        src = BACKUP_DIR / backup_id / "supreme.db"
        if not src.is_file():
            raise KeyError(f"sauvegarde inconnue : {backup_id}")
        if self._integrity(src) != "ok":
            raise ValueError("sauvegarde corrompue, restauration refusée")
        target = target or self.db_path
        # Sauvegarde de sécurité de l'état courant avant écrasement.
        if target.exists():
            safety = target.with_suffix(".pre-restore.db")
            shutil.copy2(target, safety)
        shutil.copy2(src, target)
        return {"restored": backup_id, "target": str(target), "integrity": self._integrity(target)}
