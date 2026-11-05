"""Base SQLite transactionnelle unique SUPREME (registre, missions, bus, mémoire,
budget, approbations, métriques, évaluations, stratégies, événements).

WAL + clés étrangères + thread-safety. Aucune donnée simulée.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import DB_PATH, ensure_dirs

SCHEMA_VERSION = 1
_local = threading.local()
_lock = threading.RLock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: Path | None = None) -> sqlite3.Connection:
    ensure_dirs()
    p = path or DB_PATH
    conn = sqlite3.connect(str(p), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    with _lock:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY, division TEXT NOT NULL, kind TEXT NOT NULL, name TEXT NOT NULL,
    profile_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'registered',
    version TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT NOT NULL, status TEXT NOT NULL,
    evidence TEXT NOT NULL DEFAULT '', at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT NOT NULL, version TEXT NOT NULL,
    profile_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS missions (
    id TEXT PRIMARY KEY, objective TEXT NOT NULL, state TEXT NOT NULL, priority INTEGER NOT NULL DEFAULT 5,
    plan_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    budget_usd REAL NOT NULL DEFAULT 0.05, privacy TEXT NOT NULL DEFAULT 'standard', result_json TEXT
);
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY, mission_id TEXT NOT NULL REFERENCES missions(id), agent_id TEXT NOT NULL,
    tool TEXT, input_json TEXT NOT NULL DEFAULT '{}', state TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0, result_json TEXT, error TEXT,
    idempotency_key TEXT UNIQUE, depends_on TEXT NOT NULL DEFAULT '[]',
    timeout_s INTEGER NOT NULL DEFAULT 120, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bus_messages (
    id TEXT PRIMARY KEY, sender TEXT NOT NULL, recipient TEXT NOT NULL, mission_id TEXT,
    type TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT '{}', priority INTEGER NOT NULL DEFAULT 5,
    confidence REAL NOT NULL DEFAULT 0.5, sources TEXT NOT NULL DEFAULT '[]', expected TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL, delivered INTEGER NOT NULL DEFAULT 0, ack INTEGER NOT NULL DEFAULT 0,
    dedup_key TEXT UNIQUE, dead INTEGER NOT NULL DEFAULT 0, dead_reason TEXT
);
CREATE TABLE IF NOT EXISTS memory_items (
    id TEXT PRIMARY KEY, level TEXT NOT NULL, owner TEXT NOT NULL, kind TEXT NOT NULL,
    content TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}', confidence REAL NOT NULL DEFAULT 0.5,
    source TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, expires_at TEXT,
    version INTEGER NOT NULL DEFAULT 1, parent_id TEXT, deleted INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS memory_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT, src TEXT NOT NULL, dst TEXT NOT NULL, relation TEXT NOT NULL,
    UNIQUE(src, dst, relation)
);
CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY, action TEXT NOT NULL, risk TEXT NOT NULL, requested_by TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', context_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL, decided_at TEXT, decided_by TEXT
);
CREATE TABLE IF NOT EXISTS budget_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT, scope TEXT NOT NULL, scope_id TEXT NOT NULL,
    mission_id TEXT, provider TEXT, model TEXT, tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0, cost_usd REAL NOT NULL DEFAULT 0, at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quotas (
    scope TEXT NOT NULL, scope_id TEXT NOT NULL, limit_usd REAL NOT NULL, period TEXT NOT NULL DEFAULT 'total',
    PRIMARY KEY(scope, scope_id)
);
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT, mission_id TEXT, task_id TEXT, agent_id TEXT,
    name TEXT NOT NULL, value REAL NOT NULL, at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS eval_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT NOT NULL, eval_id TEXT NOT NULL,
    mode TEXT NOT NULL, passed INTEGER NOT NULL DEFAULT 0, deferred INTEGER NOT NULL DEFAULT 0,
    evidence TEXT NOT NULL DEFAULT '', at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS strategies (
    id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, version INTEGER NOT NULL, content TEXT NOT NULL,
    score REAL, active INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, level TEXT NOT NULL, component TEXT NOT NULL,
    mission_id TEXT, message TEXT NOT NULL, data_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_tasks_mission ON tasks(mission_id);
CREATE INDEX IF NOT EXISTS idx_tasks_state ON tasks(state);
CREATE INDEX IF NOT EXISTS idx_memory_level ON memory_items(level, owner);
CREATE INDEX IF NOT EXISTS idx_bus_recipient ON bus_messages(recipient, delivered);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name);
CREATE INDEX IF NOT EXISTS idx_events_mission ON events(mission_id);
"""


def init_db(conn: sqlite3.Connection) -> None:
    with transaction(conn):
        conn.executescript(SCHEMA_SQL)
        # FTS5 si disponible, sinon recherche LIKE (repli honnête documenté).
        try:
            conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(content, content='memory_items', content_rowid='rowid')")
            conn.executescript("""
                CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memory_items BEGIN
                    INSERT INTO memory_fts(rowid, content) VALUES (new.rowid, new.content);
                END;
                CREATE TRIGGER IF NOT EXISTS memory_ad AFTER DELETE ON memory_items BEGIN
                    INSERT INTO memory_fts(memory_fts, rowid, content) VALUES('delete', old.rowid, old.content);
                END;
                CREATE TRIGGER IF NOT EXISTS memory_au AFTER UPDATE ON memory_items BEGIN
                    INSERT INTO memory_fts(memory_fts, rowid, content) VALUES('delete', old.rowid, old.content);
                    INSERT INTO memory_fts(rowid, content) VALUES (new.rowid, new.content);
                END;
            """)
            fts = True
        except sqlite3.OperationalError:
            fts = False
        conn.execute("INSERT OR REPLACE INTO schema_meta(key,value) VALUES('version',?)", (str(SCHEMA_VERSION),))
        conn.execute("INSERT OR REPLACE INTO schema_meta(key,value) VALUES('fts5',?)", ("1" if fts else "0",))


def get_conn(path: Path | None = None) -> sqlite3.Connection:
    """Connexion par thread (réutilisée), initialisée."""
    key = f"conn_{path or DB_PATH}"
    conn = getattr(_local, key, None)
    if conn is None:
        conn = connect(path)
        init_db(conn)
        setattr(_local, key, conn)
    return conn


def log_event(conn: sqlite3.Connection, level: str, component: str, message: str,
              mission_id: str | None = None, data: dict | None = None) -> None:
    from .security import redact
    with transaction(conn):
        conn.execute(
            "INSERT INTO events(at,level,component,mission_id,message,data_json) VALUES(?,?,?,?,?,?)",
            (now(), level, component, mission_id, redact(message), json.dumps(data or {}, ensure_ascii=False, default=str)),
        )


def rows_to_dicts(rows) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]
