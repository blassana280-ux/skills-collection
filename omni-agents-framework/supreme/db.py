"""Base SQLite transactionnelle unique SUPREME (registre, missions, bus, mémoire,
budget, approbations, métriques, évaluations, stratégies, événements).

WAL + clés étrangères + thread-safety. Aucune donnée simulée.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import DB_PATH, ensure_dirs

SCHEMA_VERSION = 4
_local = threading.local()
_tx_local = threading.local()
_lock = threading.RLock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def epoch() -> float:
    """Horloge partagée par les processus pour les baux (secondes Unix)."""
    return time.time()


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
def transaction(conn: sqlite3.Connection, immediate: bool = False) -> Iterator[sqlite3.Connection]:
    """Transaction réentrante par connexion.

    `immediate=True` prend le verrou d'écriture SQLite dès l'entrée (BEGIN IMMEDIATE) :
    indispensable aux sections lire-réserver-écrire partagées entre processus. Les
    appels imbriqués utilisent des SAVEPOINTs et ne committent pas prématurément.
    """
    depths = getattr(_tx_local, "depths", None)
    if depths is None:
        depths = {}
        _tx_local.depths = depths
    key = id(conn)
    depth = depths.get(key, 0)
    if depth:
        savepoint = f"sp_{key}_{depth}"
        conn.execute(f"SAVEPOINT {savepoint}")
        depths[key] = depth + 1
        try:
            yield conn
            conn.execute(f"RELEASE SAVEPOINT {savepoint}")
        except Exception:
            conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            conn.execute(f"RELEASE SAVEPOINT {savepoint}")
            raise
        finally:
            depths[key] = depth
        return
    with _lock:
        if immediate:
            conn.execute("BEGIN IMMEDIATE")
        depths[key] = 1
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            depths[key] = 0


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
    budget_usd REAL NOT NULL DEFAULT 0.05, privacy TEXT NOT NULL DEFAULT 'standard', result_json TEXT,
    owner_worker_id TEXT, lease_token TEXT, lease_expires_at REAL NOT NULL DEFAULT 0,
    heartbeat_at REAL, fencing_token INTEGER NOT NULL DEFAULT 0,
    run_attempts INTEGER NOT NULL DEFAULT 0, cancel_requested INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY, mission_id TEXT NOT NULL REFERENCES missions(id), agent_id TEXT NOT NULL,
    tool TEXT, input_json TEXT NOT NULL DEFAULT '{}', state TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0, result_json TEXT, error TEXT,
    idempotency_key TEXT UNIQUE, depends_on TEXT NOT NULL DEFAULT '[]',
    timeout_s INTEGER NOT NULL DEFAULT 120, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    execution_token TEXT, owner_worker_id TEXT
);
CREATE TABLE IF NOT EXISTS task_executions (
    task_id TEXT PRIMARY KEY REFERENCES tasks(id), mission_id TEXT NOT NULL,
    idempotency_key TEXT UNIQUE, fencing_token INTEGER NOT NULL,
    worker_id TEXT NOT NULL, result_json TEXT NOT NULL, completed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS workers (
    worker_id TEXT PRIMARY KEY, pid INTEGER NOT NULL, hostname TEXT NOT NULL,
    started_at REAL NOT NULL, last_heartbeat REAL NOT NULL, stopped_at REAL,
    state TEXT NOT NULL DEFAULT 'alive'
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
    tokens_out INTEGER NOT NULL DEFAULT 0, cost_usd REAL NOT NULL DEFAULT 0, at TEXT NOT NULL,
    reservation_id TEXT, call_key TEXT
);
CREATE TABLE IF NOT EXISTS budget_reservations (
    id TEXT PRIMARY KEY, call_key TEXT UNIQUE, mission_id TEXT, task_id TEXT,
    provider TEXT, model TEXT, status TEXT NOT NULL DEFAULT 'reserved',
    amount_usd REAL NOT NULL, actual_cost_usd REAL, tokens_in_est INTEGER NOT NULL DEFAULT 0,
    tokens_out_est INTEGER NOT NULL DEFAULT 0, tokens_in_actual INTEGER, tokens_out_actual INTEGER,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, error TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS budget_reservation_scopes (
    reservation_id TEXT NOT NULL REFERENCES budget_reservations(id),
    scope TEXT NOT NULL, scope_id TEXT NOT NULL, amount_usd REAL NOT NULL,
    PRIMARY KEY(reservation_id, scope, scope_id)
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
CREATE TABLE IF NOT EXISTS learning_schedulers (
    id TEXT PRIMARY KEY, interval_seconds REAL NOT NULL, max_proposals INTEGER NOT NULL DEFAULT 5,
    owner_worker_id TEXT, lease_token TEXT, lease_expires_at REAL NOT NULL DEFAULT 0,
    heartbeat_at REAL, last_run_at TEXT, next_run_at REAL, state TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS learning_runs (
    id TEXT PRIMARY KEY, scheduler_id TEXT NOT NULL DEFAULT 'default', trigger TEXT NOT NULL,
    worker_id TEXT NOT NULL, lease_token TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'running',
    started_at TEXT NOT NULL, finished_at TEXT, heartbeat_at REAL, lease_expires_at REAL NOT NULL,
    report_json TEXT, error TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, level TEXT NOT NULL, component TEXT NOT NULL,
    mission_id TEXT, message TEXT NOT NULL, data_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS provider_controls (
    provider TEXT PRIMARY KEY, inference_enabled INTEGER NOT NULL DEFAULT 0,
    approved_by TEXT, approved_at TEXT, expires_at REAL NOT NULL DEFAULT 0,
    max_total_usd REAL NOT NULL DEFAULT 0, max_calls INTEGER NOT NULL DEFAULT 0,
    pricing_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS provider_models (
    provider TEXT NOT NULL, model TEXT NOT NULL, capabilities_json TEXT NOT NULL DEFAULT '[]',
    context INTEGER NOT NULL DEFAULT 0, tools INTEGER NOT NULL DEFAULT 0,
    discovered_at TEXT NOT NULL, endpoint_host TEXT NOT NULL, request_id TEXT,
    category TEXT NOT NULL, context_attested INTEGER NOT NULL DEFAULT 0,
    context_source TEXT NOT NULL DEFAULT '', context_attested_at TEXT,
    PRIMARY KEY(provider, model)
);
CREATE TABLE IF NOT EXISTS provider_verifications (
    id TEXT PRIMARY KEY, provider TEXT NOT NULL, ok INTEGER NOT NULL, category TEXT NOT NULL,
    http_status INTEGER NOT NULL DEFAULT 0, endpoint_host TEXT NOT NULL, request_id TEXT,
    latency_ms REAL NOT NULL DEFAULT 0, models_json TEXT NOT NULL DEFAULT '[]',
    error TEXT NOT NULL DEFAULT '', checked_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS activation_campaigns (
    id TEXT PRIMARY KEY, target_size INTEGER NOT NULL, provider TEXT NOT NULL, model TEXT,
    status TEXT NOT NULL DEFAULT 'prepared', budget_usd REAL NOT NULL,
    per_agent_usd REAL NOT NULL, created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT,
    owner_worker_id TEXT, lease_token TEXT, lease_expires_at REAL NOT NULL DEFAULT 0,
    heartbeat_at REAL, report_json TEXT, error TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS activation_members (
    campaign_id TEXT NOT NULL REFERENCES activation_campaigns(id), agent_id TEXT NOT NULL,
    position INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending', proof_id TEXT,
    error TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL,
    PRIMARY KEY(campaign_id, agent_id), UNIQUE(campaign_id, position)
);
CREATE TABLE IF NOT EXISTS activation_proofs (
    id TEXT PRIMARY KEY, campaign_id TEXT REFERENCES activation_campaigns(id), agent_id TEXT NOT NULL,
    category TEXT NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL,
    http_status INTEGER NOT NULL, endpoint_host TEXT NOT NULL, request_id TEXT,
    reservation_id TEXT, output_sha256 TEXT NOT NULL, usage_json TEXT NOT NULL,
    cost_usd REAL NOT NULL, latency_ms REAL NOT NULL, usable INTEGER NOT NULL,
    permissions_ok INTEGER NOT NULL, budget_ok INTEGER NOT NULL, checked_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS guardian_runs (
    id TEXT PRIMARY KEY, trigger TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'running',
    started_at TEXT NOT NULL, finished_at TEXT, checks_json TEXT NOT NULL DEFAULT '{}',
    findings INTEGER NOT NULL DEFAULT 0, critical INTEGER NOT NULL DEFAULT 0,
    owner_worker_id TEXT, lease_token TEXT, lease_expires_at REAL NOT NULL DEFAULT 0,
    heartbeat_at REAL, error TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS security_findings (
    id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL UNIQUE, code TEXT NOT NULL,
    severity TEXT NOT NULL, component TEXT NOT NULL, detail TEXT NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL DEFAULT 'open',
    first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, occurrences INTEGER NOT NULL DEFAULT 1,
    resolved_at TEXT, resolution TEXT NOT NULL DEFAULT '', acknowledged_by TEXT
);
CREATE TABLE IF NOT EXISTS guardian_schedulers (
    id TEXT PRIMARY KEY, interval_seconds REAL NOT NULL, owner_worker_id TEXT,
    lease_token TEXT, lease_expires_at REAL NOT NULL DEFAULT 0, heartbeat_at REAL,
    next_run_at REAL NOT NULL DEFAULT 0, state TEXT NOT NULL DEFAULT 'active',
    cycles INTEGER NOT NULL DEFAULT 0, last_error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS integrity_baseline (
    path TEXT PRIMARY KEY, sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL, recorded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_quarantine (
    agent_id TEXT PRIMARY KEY, reason TEXT NOT NULL, isolated_at TEXT NOT NULL,
    review_required INTEGER NOT NULL DEFAULT 1, campaign_id TEXT, proof_id TEXT,
    released_at TEXT, release_evidence TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_activation_one_active ON activation_campaigns(status) WHERE status='running';
CREATE INDEX IF NOT EXISTS idx_activation_proofs_agent ON activation_proofs(agent_id, checked_at);
CREATE INDEX IF NOT EXISTS idx_provider_verifications_provider ON provider_verifications(provider, checked_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_learning_one_running ON learning_runs(status) WHERE status='running';
CREATE UNIQUE INDEX IF NOT EXISTS idx_guardian_one_running ON guardian_runs(status) WHERE status='running';
CREATE INDEX IF NOT EXISTS idx_findings_status ON security_findings(status, severity);
CREATE INDEX IF NOT EXISTS idx_findings_code ON security_findings(code, last_seen_at);
CREATE INDEX IF NOT EXISTS idx_missions_queue ON missions(state, priority, created_at);
CREATE INDEX IF NOT EXISTS idx_budget_reservations_status ON budget_reservations(status);
CREATE INDEX IF NOT EXISTS idx_budget_reservation_scopes ON budget_reservation_scopes(scope, scope_id);
CREATE INDEX IF NOT EXISTS idx_tasks_mission ON tasks(mission_id);
CREATE INDEX IF NOT EXISTS idx_tasks_state ON tasks(state);
CREATE INDEX IF NOT EXISTS idx_memory_level ON memory_items(level, owner);
CREATE INDEX IF NOT EXISTS idx_bus_recipient ON bus_messages(recipient, delivered);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name);
CREATE INDEX IF NOT EXISTS idx_events_mission ON events(mission_id);
"""


def _add_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    present = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    for name, decl in columns.items():
        if name not in present:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


def _migrate(conn: sqlite3.Connection) -> None:
    """Migrations additives v1 -> v2 -> v3 -> v4 : aucune suppression, aucune réécriture de données."""
    _add_columns(conn, "missions", {
        "owner_worker_id": "TEXT", "lease_token": "TEXT",
        "lease_expires_at": "REAL NOT NULL DEFAULT 0", "heartbeat_at": "REAL",
        "fencing_token": "INTEGER NOT NULL DEFAULT 0", "run_attempts": "INTEGER NOT NULL DEFAULT 0",
        "cancel_requested": "INTEGER NOT NULL DEFAULT 0",
    })
    _add_columns(conn, "tasks", {"execution_token": "TEXT", "owner_worker_id": "TEXT"})
    _add_columns(conn, "budget_ledger", {"reservation_id": "TEXT", "call_key": "TEXT"})
    _add_columns(conn, "activation_campaigns", {"model": "TEXT"})
    # v4 : contexte attesté par l'opérateur quand l'API ne l'expose pas (OpenAI/DeepSeek).
    _add_columns(conn, "provider_models", {
        "context_attested": "INTEGER NOT NULL DEFAULT 0",
        "context_source": "TEXT NOT NULL DEFAULT ''",
        "context_attested_at": "TEXT",
    })


def init_db(conn: sqlite3.Connection) -> None:
    with transaction(conn):
        conn.executescript(SCHEMA_SQL)
        _migrate(conn)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_missions_lease ON missions(state, lease_expires_at)")
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
