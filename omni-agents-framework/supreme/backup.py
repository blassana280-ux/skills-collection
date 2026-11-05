"""Backup & Recovery Manager SUPREME — sauvegarde/restauration SQLite + catalogue.

Utilise l'API de backup SQLite (cohérente à chaud). Vérification d'intégrité.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import uuid
from pathlib import Path

from .config import BACKUP_DIR, CATALOG_DIR, DB_PATH, ensure_dirs
from .db import connect, now


PRUNE_CONFIRM = "SUPPRIMER ANCIENNES SAUVEGARDES"


class BackupManager:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH

    def backup(self, label: str = "") -> dict:
        ensure_dirs()
        bid = f"bk-{now().replace(':', '').replace('-', '')[:15]}-{uuid.uuid4().hex[:6]}"
        dest_dir = BACKUP_DIR / bid
        # Une sauvegarde contient toute la base : répertoire 0700, fichier 0600.
        BACKUP_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(BACKUP_DIR, 0o700)
        dest_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(dest_dir, 0o700)
        dest_db = dest_dir / "supreme.db"
        src = connect(self.db_path)
        fd = os.open(dest_db, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        dst = sqlite3.connect(str(dest_db))
        with dst:
            src.backup(dst)
        dst.close()
        src.close()
        os.chmod(dest_db, 0o600)
        # Copie du catalogue versionné
        if CATALOG_DIR.is_dir():
            shutil.copytree(CATALOG_DIR, dest_dir / "catalog", dirs_exist_ok=True)
        integrity = self._integrity(dest_db)
        meta = {"id": bid, "label": label, "created_at": now(), "db": str(dest_db),
                "integrity": integrity, "size_bytes": dest_db.stat().st_size,
                "permissions": "0600", "directory_permissions": "0700"}
        meta_path = dest_dir / "meta.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        os.chmod(meta_path, 0o600)
        return meta

    def _integrity(self, path: Path) -> str:
        """Renvoie `ok` ou un motif d'échec — ne lève jamais sur fichier corrompu.

        Une sauvegarde illisible doit être signalée comme telle (et donc protégée
        de la rétention), pas faire échouer tout le contrôle de sauvegardes.
        """
        conn = None
        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            return conn.execute("PRAGMA integrity_check").fetchone()[0]
        except sqlite3.DatabaseError as exc:
            return f"unreadable: {type(exc).__name__}"
        except sqlite3.Error as exc:
            return f"error: {type(exc).__name__}"
        finally:
            if conn is not None:
                conn.close()

    def list_backups(self) -> list[dict]:
        ensure_dirs()
        out = []
        for d in sorted(BACKUP_DIR.iterdir()):
            meta = d / "meta.json"
            if meta.is_file():
                out.append(json.loads(meta.read_text(encoding="utf-8")))
        return out

    def verify_all(self) -> dict:
        """Vérifie intégrité + permissions de toutes les sauvegardes (lecture seule)."""
        results = []
        for meta in self.list_backups():
            path = Path(meta["db"])
            entry = {"id": meta["id"], "exists": path.is_file()}
            if path.is_file():
                entry["integrity"] = self._integrity(path)
                entry["mode"] = oct(path.stat().st_mode & 0o777)
                entry["private"] = (path.stat().st_mode & 0o077) == 0
                entry["size_bytes"] = path.stat().st_size
            results.append(entry)
        ok = all(r.get("integrity") == "ok" for r in results if r["exists"]) and bool(results)
        return {"backups": results, "count": len(results), "all_integrity_ok": ok,
                "all_private": all(r.get("private", False) for r in results if r["exists"])}

    def prune(self, *, keep: int, confirm: str, dry_run: bool = True) -> dict:
        """Rétention opt-in : suppression UNIQUEMENT sur confirmation humaine explicite.

        Par défaut `dry_run=True` : rien n'est supprimé, la liste est seulement
        calculée. La sauvegarde la plus récente est toujours conservée, ainsi que
        toute sauvegarde dont l'intégrité n'est pas `ok` (preuve à examiner).
        """
        if keep < 1:
            raise ValueError("keep doit être >= 1 : au moins une sauvegarde est conservée")
        backups = sorted(self.list_backups(), key=lambda m: m["created_at"], reverse=True)
        protected, candidates = [], []
        for index, meta in enumerate(backups):
            path = Path(meta["db"])
            integrity = self._integrity(path) if path.is_file() else "missing"
            if index < keep or integrity != "ok":
                protected.append({"id": meta["id"], "reason": "dans la fenêtre keep" if index < keep
                                  else f"intégrité={integrity} : à examiner, jamais supprimée"})
            else:
                candidates.append({"id": meta["id"], "created_at": meta["created_at"],
                                   "size_bytes": path.stat().st_size if path.is_file() else 0})
        result = {"keep": keep, "dry_run": dry_run, "protected": protected,
                  "would_delete": candidates, "deleted": [], "bytes_reclaimed": 0}
        if dry_run:
            return result
        if confirm != PRUNE_CONFIRM:
            raise PermissionError(f"suppression refusée : --confirm '{PRUNE_CONFIRM}' requis")
        for entry in candidates:
            directory = BACKUP_DIR / entry["id"]
            if directory.is_dir():
                shutil.rmtree(directory)
                result["deleted"].append(entry["id"])
                result["bytes_reclaimed"] += entry["size_bytes"]
        return result

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
            os.chmod(safety, 0o600)
        shutil.copy2(src, target)
        os.chmod(target, 0o600)
        return {"restored": backup_id, "target": str(target), "integrity": self._integrity(target),
                "safety_copy": str(target.with_suffix(".pre-restore.db")) if target.exists() else None}
