"""Store SQLite de la mémoire d'orchestration OmniBrain v4.

Remplace les « recettes en mémoire volatile » par une base transactionnelle :
``missions``, ``escouades``, ``resultats``, ``echecs``, ``recettes`` (par type
de projet), plus les journaux d'optimisation, de benchmarks, d'auto-correctifs
et d'orchestration.

API publique : ``record_mission()`` / ``get_recettes()`` (module-level, store
par défaut) et la classe ``MemoryStore`` pour un contrôle fin du chemin.

Règles (OMNIBRAIN.md §4-5) : stdlib uniquement, secrets rédigés avant toute
persistance, aucune écriture sur la branche principale, rien d'inventé.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = 1

_SECRET_PATTERNS = (
    # Formats « clé=valeur », en-têtes et JSON sérialisé (« token": "valeur" »).
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password|passwd|bearer|authorization)[\"']?\s*[:=]\s*[\"']?[^\s,;'\"}]+"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAKIA[A-Z0-9]{12,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def redact(value: Any) -> str:
    """Rédige les secrets d'une valeur avant persistance (résultat : str)."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    for pattern in _SECRET_PATTERNS:
        if pattern.groups:
            text = pattern.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
        else:
            text = pattern.sub("[REDACTED]", text)
    return text


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS missions (
    id TEXT PRIMARY KEY,
    project_type TEXT NOT NULL DEFAULT 'generic',
    title TEXT NOT NULL DEFAULT '',
    spec TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'running',
    verdict TEXT NOT NULL DEFAULT 'NEEDS WORK',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS escouades (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    wave INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS resultats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    escouade_id TEXT,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ok',
    verdict TEXT NOT NULL DEFAULT 'NEEDS WORK',
    duration_ms REAL NOT NULL DEFAULT 0,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    artifacts TEXT NOT NULL DEFAULT '[]',
    evidence TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS echecs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    profile TEXT NOT NULL,
    error_type TEXT NOT NULL,
    message TEXT NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recettes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_type TEXT NOT NULL,
    pattern TEXT NOT NULL,
    steps TEXT NOT NULL DEFAULT '[]',
    success_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    score REAL NOT NULL DEFAULT 0,
    source_mission TEXT,
    updated_at TEXT NOT NULL,
    UNIQUE(project_type, pattern)
);
CREATE TABLE IF NOT EXISTS prompt_iterations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id TEXT,
    project_type TEXT NOT NULL,
    iteration INTEGER NOT NULL,
    score_before REAL NOT NULL DEFAULT 0,
    score_after REAL NOT NULL DEFAULT 0,
    accepted INTEGER NOT NULL DEFAULT 0,
    rationale TEXT NOT NULL DEFAULT '',
    prompt_before TEXT NOT NULL DEFAULT '',
    prompt_after TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    hit_rate REAL NOT NULL DEFAULT 0,
    mean_latency_ms REAL NOT NULL DEFAULT 0,
    payload TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS autofix_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signature TEXT NOT NULL UNIQUE,
    profile TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    branch TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS orchestration_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'system',
    action TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'INFO',
    detail TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_resultats_mission ON resultats(mission_id);
CREATE INDEX IF NOT EXISTS idx_echecs_profile ON echecs(profile, created_at);
CREATE INDEX IF NOT EXISTS idx_logs_created ON orchestration_logs(created_at);
"""


def default_db_path() -> Path:
    env = os.environ.get("OMNIBRAIN_DB")
    return Path(env) if env else FRAMEWORK_ROOT / "var" / "omnibrain.sqlite3"


class MemoryStore:
    """Store SQLite transactionnel, sûr pour plusieurs threads d'une vague."""

    def __init__(self, db_path: str | Path | None = None, *, redact_secrets: bool = True):
        path = db_path if db_path is not None else default_db_path()
        self.db_path = ":memory:" if str(path) == ":memory:" else str(Path(path))
        self.redact_secrets = redact_secrets
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self.init_schema()

    # ------------------------------------------------------------------ cycle
    def init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(SCHEMA_SQL)
            self._conn.execute(
                "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> "MemoryStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _scrub(self, value: Any) -> str:
        return redact(value) if self.redact_secrets else (
            value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        )

    def _write(self, sql: str, params: Iterable[Any]) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, tuple(params))
            self._conn.commit()
            return cur

    def _rows(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(row) for row in self._conn.execute(sql, tuple(params)).fetchall()]

    # --------------------------------------------------------------- missions
    def record_mission(self, mission: Mapping[str, Any] | str | None = None, **fields: Any) -> str:
        """Enregistre une mission ; accepte un dict, un titre nu ou des kwargs."""
        if isinstance(mission, str):
            data: dict[str, Any] = {"title": mission}
        elif mission is None:
            data = {}
        else:
            data = dict(mission)
        data.update(fields)
        mission_id = str(data.get("id") or f"mission-{uuid.uuid4().hex[:12]}")
        now = _now()
        meta = data.get("metadata") or {}
        self._write(
            """INSERT INTO missions(id, project_type, title, spec, status, verdict, created_at, updated_at, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 project_type=excluded.project_type, title=excluded.title, spec=excluded.spec,
                 status=excluded.status, verdict=excluded.verdict, updated_at=excluded.updated_at,
                 metadata=excluded.metadata""",
            (
                mission_id,
                str(data.get("project_type") or "generic"),
                self._scrub(data.get("title") or ""),
                self._scrub(data.get("spec") or ""),
                str(data.get("status") or "running"),
                str(data.get("verdict") or "NEEDS WORK"),
                now,
                now,
                self._scrub(meta),
            ),
        )
        self.log("omnibrain", "orchestrator", "record_mission", {"mission_id": mission_id})
        return mission_id

    def get_mission(self, mission_id: str) -> dict[str, Any] | None:
        rows = self._rows("SELECT * FROM missions WHERE id = ?", (mission_id,))
        return rows[0] if rows else None

    def list_missions(self, project_type: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if project_type:
            return self._rows(
                "SELECT * FROM missions WHERE project_type = ? ORDER BY created_at DESC LIMIT ?",
                (project_type, limit),
            )
        return self._rows("SELECT * FROM missions ORDER BY created_at DESC LIMIT ?", (limit,))

    def update_mission(self, mission_id: str, **fields: Any) -> None:
        allowed = {"status", "verdict", "title", "spec", "project_type", "metadata"}
        cols = [k for k in fields if k in allowed]
        if not cols:
            return
        values: list[Any] = []
        for col in cols:
            value = fields[col]
            values.append(self._scrub(value) if not isinstance(value, (int, float)) else value)
        self._write(
            f"UPDATE missions SET {', '.join(f'{c} = ?' for c in cols)}, updated_at = ? WHERE id = ?",
            (*values, _now(), mission_id),
        )

    # -------------------------------------------------------------- escouades
    def record_squad(self, mission_id: str, name: str, wave: int = 0, squad_id: str | None = None) -> str:
        sid = squad_id or f"escouade-{uuid.uuid4().hex[:10]}"
        self._write(
            "INSERT OR REPLACE INTO escouades(id, mission_id, name, wave, created_at) VALUES (?, ?, ?, ?, ?)",
            (sid, mission_id, self._scrub(name), int(wave), _now()),
        )
        return sid

    def squads_for(self, mission_id: str) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM escouades WHERE mission_id = ? ORDER BY wave, id", (mission_id,))

    # -------------------------------------------------------------- résultats
    def record_result(
        self,
        mission_id: str,
        agent_id: str,
        *,
        status: str = "ok",
        verdict: str = "PASS",
        duration_ms: float = 0.0,
        tokens_in: int = 0,
        tokens_out: int = 0,
        artifacts: Iterable[str] | None = None,
        evidence: Iterable[str] | None = None,
        escouade_id: str | None = None,
    ) -> int:
        cur = self._write(
            """INSERT INTO resultats(mission_id, escouade_id, agent_id, status, verdict,
                   duration_ms, tokens_in, tokens_out, artifacts, evidence, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                mission_id, escouade_id, agent_id, status, verdict, float(duration_ms),
                int(tokens_in), int(tokens_out),
                self._scrub(list(artifacts or [])), self._scrub(list(evidence or [])), _now(),
            ),
        )
        return int(cur.lastrowid or 0)

    def results_for(self, mission_id: str) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM resultats WHERE mission_id = ? ORDER BY id", (mission_id,))

    # ---------------------------------------------------------------- échecs
    def record_failure(
        self,
        mission_id: str,
        agent_id: str,
        profile: str,
        error_type: str,
        message: str,
        attempt: int = 1,
    ) -> int:
        cur = self._write(
            """INSERT INTO echecs(mission_id, agent_id, profile, error_type, message, attempt, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (mission_id, agent_id, profile, error_type, self._scrub(message), int(attempt), _now()),
        )
        self.log("omnibrain", "orchestrator", "record_failure", {"profile": profile, "error_type": error_type}, level="WARN")
        return int(cur.lastrowid or 0)

    def failures_for(self, profile: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._rows(
            "SELECT * FROM echecs WHERE profile = ? ORDER BY id DESC LIMIT ?", (profile, limit)
        )

    def all_failures(self, project_type: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
        if project_type:
            return self._rows(
                """SELECT e.* FROM echecs e JOIN missions m ON m.id = e.mission_id
                   WHERE m.project_type = ? ORDER BY e.id LIMIT ?""",
                (project_type, limit),
            )
        return self._rows("SELECT * FROM echecs ORDER BY id LIMIT ?", (limit,))

    # --------------------------------------------------------------- recettes
    def upsert_recette(
        self,
        project_type: str,
        pattern: str,
        steps: Iterable[str],
        *,
        success_delta: int = 0,
        failure_delta: int = 0,
        source_mission: str | None = None,
    ) -> dict[str, Any]:
        existing = self._rows(
            "SELECT * FROM recettes WHERE project_type = ? AND pattern = ?", (project_type, pattern)
        )
        row = existing[0] if existing else None
        success = int(row["success_count"]) if row else 0
        failure = int(row["failure_count"]) if row else 0
        success += int(success_delta)
        failure += int(failure_delta)
        score = (success + 1.0) / (success + failure + 2.0)
        self._write(
            """INSERT INTO recettes(project_type, pattern, steps, success_count, failure_count, score, source_mission, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(project_type, pattern) DO UPDATE SET
                 steps=excluded.steps, success_count=excluded.success_count,
                 failure_count=excluded.failure_count, score=excluded.score,
                 source_mission=excluded.source_mission, updated_at=excluded.updated_at""",
            (
                project_type, pattern, self._scrub(list(steps)), success, failure, score,
                source_mission, _now(),
            ),
        )
        return self.get_recettes(project_type)[0] if not project_type else next(
            r for r in self.get_recettes(project_type) if r["pattern"] == pattern
        )

    def get_recettes(self, project_type: str | None = None, min_success: int = 0) -> list[dict[str, Any]]:
        """Recettes par type de projet, triées par score décroissant (deterministe)."""
        if project_type:
            rows = self._rows(
                """SELECT * FROM recettes WHERE project_type = ? AND success_count >= ?
                   ORDER BY score DESC, pattern ASC""",
                (project_type, min_success),
            )
        else:
            rows = self._rows(
                "SELECT * FROM recettes WHERE success_count >= ? ORDER BY score DESC, project_type, pattern",
                (min_success,),
            )
        for row in rows:
            row["steps"] = json.loads(row["steps"])
        return rows

    # ------------------------------------------------------- prompts / benchs
    def record_prompt_iteration(
        self,
        project_type: str,
        iteration: int,
        *,
        score_before: float,
        score_after: float,
        accepted: bool,
        rationale: str,
        prompt_before: str,
        prompt_after: str,
        mission_id: str | None = None,
    ) -> int:
        cur = self._write(
            """INSERT INTO prompt_iterations(mission_id, project_type, iteration, score_before,
                   score_after, accepted, rationale, prompt_before, prompt_after, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                mission_id, project_type, int(iteration), float(score_before), float(score_after),
                int(bool(accepted)), self._scrub(rationale), self._scrub(prompt_before),
                self._scrub(prompt_after), _now(),
            ),
        )
        return int(cur.lastrowid or 0)

    def prompt_iterations(self, project_type: str | None = None) -> list[dict[str, Any]]:
        if project_type:
            return self._rows(
                "SELECT * FROM prompt_iterations WHERE project_type = ? ORDER BY id", (project_type,)
            )
        return self._rows("SELECT * FROM prompt_iterations ORDER BY id")

    def record_benchmark(self, run_id: str, fingerprint: str, payload: Mapping[str, Any]) -> int:
        cur = self._write(
            "INSERT INTO benchmarks(run_id, fingerprint, hit_rate, mean_latency_ms, payload, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                run_id, fingerprint, float(payload.get("hit_rate", 0)),
                float(payload.get("mean_latency_ms", 0)), self._scrub(dict(payload)), _now(),
            ),
        )
        return int(cur.lastrowid or 0)

    def benchmark_history(self) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM benchmarks ORDER BY id")

    # ------------------------------------------------------------- auto-fixes
    def autofix_exists(self, signature: str) -> bool:
        return bool(self._rows("SELECT 1 FROM autofix_runs WHERE signature = ?", (signature,)))

    def mark_autofix(self, signature: str, profile: str, agent_id: str, branch: str, status: str) -> None:
        self._write(
            "INSERT OR IGNORE INTO autofix_runs(signature, profile, agent_id, branch, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (signature, profile, agent_id, branch, status, _now()),
        )

    # ------------------------------------------------------------------- logs
    def log(
        self,
        actor: str,
        role: str,
        action: str,
        detail: Mapping[str, Any] | None = None,
        *,
        level: str = "INFO",
    ) -> int:
        cur = self._write(
            "INSERT INTO orchestration_logs(actor, role, action, level, detail, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (actor, role, action, level, self._scrub(detail or {}), _now()),
        )
        return int(cur.lastrowid or 0)

    def logs(self, limit: int = 200) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM orchestration_logs ORDER BY id DESC LIMIT ?", (limit,))

    def stats(self) -> dict[str, int]:
        tables = (
            "missions", "escouades", "resultats", "echecs", "recettes",
            "prompt_iterations", "benchmarks", "autofix_runs", "orchestration_logs",
        )
        return {t: self._rows(f"SELECT COUNT(*) AS n FROM {t}")[0]["n"] for t in tables}


# ------------------------------------------------------- store par défaut
_STORE: MemoryStore | None = None


def get_store() -> MemoryStore:
    global _STORE
    if _STORE is None:
        _STORE = MemoryStore()
    return _STORE


def configure(db_path: str | Path | None = None, **kwargs: Any) -> MemoryStore:
    """Remplace le store par défaut (utile aux tests et au mode service)."""
    global _STORE
    if _STORE is not None:
        _STORE.close()
    _STORE = MemoryStore(db_path, **kwargs)
    return _STORE


def record_mission(mission: Mapping[str, Any] | str | None = None, **fields: Any) -> str:
    return get_store().record_mission(mission, **fields)


def get_recettes(project_type: str | None = None, min_success: int = 0) -> list[dict[str, Any]]:
    return get_store().get_recettes(project_type, min_success)
