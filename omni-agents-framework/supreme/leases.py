"""Baux SQLite multi-processus SUPREME — propriétaires, heartbeat, fencing, reprise.

Un worker ne réinitialise jamais une mission encore détenue par un bail vivant.
La reprise ne cible que les missions dont le bail a expiré ET dont le worker est
arrêté ou n'a plus émis de heartbeat après l'expiration. Chaque revendication
incrémente un jeton de fencing ; les écritures de l'ancien propriétaire sont refusées.
"""
from __future__ import annotations

import os
import socket
import sqlite3
import uuid
from dataclasses import dataclass

from .db import epoch, log_event, now, transaction


class LeaseLostError(RuntimeError):
    """Le bail n'est plus détenu : aucune écriture ne doit être commitée."""


@dataclass(frozen=True)
class MissionLease:
    mission_id: str
    worker_id: str
    token: str
    fencing_token: int
    expires_at: float


def new_worker_id(prefix: str = "wk") -> str:
    return f"{prefix}-{os.getpid()}-{uuid.uuid4().hex[:12]}"


def register_worker(conn: sqlite3.Connection, worker_id: str) -> None:
    t = epoch()
    with transaction(conn, immediate=True):
        conn.execute(
            """INSERT INTO workers(worker_id,pid,hostname,started_at,last_heartbeat,state)
               VALUES(?,?,?,?,?,'alive')
               ON CONFLICT(worker_id) DO UPDATE SET
                 pid=excluded.pid, hostname=excluded.hostname,
                 last_heartbeat=excluded.last_heartbeat, stopped_at=NULL, state='alive'""",
            (worker_id, os.getpid(), socket.gethostname(), t, t))


def heartbeat_worker(conn: sqlite3.Connection, worker_id: str) -> bool:
    with transaction(conn, immediate=True):
        cur = conn.execute("UPDATE workers SET last_heartbeat=?, state='alive' WHERE worker_id=? AND state='alive'",
                           (epoch(), worker_id))
        return cur.rowcount == 1


def stop_worker(conn: sqlite3.Connection, worker_id: str) -> dict:
    """Arrêt propre : le worker est marqué arrêté et ses missions non terminées replanifiées."""
    t = epoch()
    with transaction(conn, immediate=True):
        conn.execute("UPDATE workers SET state='stopped', stopped_at=?, last_heartbeat=? WHERE worker_id=?",
                     (t, t, worker_id))
        rows = conn.execute("SELECT id, lease_token, fencing_token FROM missions WHERE owner_worker_id=? AND state='running'",
                            (worker_id,)).fetchall()
        released = 0
        for r in rows:
            lease = MissionLease(r["id"], worker_id, r["lease_token"] or "", r["fencing_token"], 0)
            if release_mission(conn, lease, requeue=True):
                released += 1
    return {"worker_id": worker_id, "released": released}


def _recover_mission(conn: sqlite3.Connection, mission_id: str) -> int:
    """Replanifie une mission abandonnée ; conserve les tâches déjà terminées."""
    m = conn.execute("SELECT cancel_requested FROM missions WHERE id=?", (mission_id,)).fetchone()
    if m is None:
        return 0
    if m["cancel_requested"]:
        conn.execute("UPDATE tasks SET state='cancelled', execution_token=NULL, owner_worker_id=NULL, updated_at=? "
                     "WHERE mission_id=? AND state NOT IN ('done','failed','blocked','cancelled')", (now(), mission_id))
        conn.execute("UPDATE missions SET state='cancelled', owner_worker_id=NULL, lease_token=NULL, "
                     "lease_expires_at=0, heartbeat_at=NULL, updated_at=? WHERE id=?", (now(), mission_id))
        return 0
    # Un appel LLM interrompu peut avoir été facturé : ne pas le rejouer aveuglément.
    conn.execute(
        """UPDATE tasks SET state='blocked',
             error='appel fournisseur interrompu ; réconciliation humaine requise avant nouvelle tentative',
             execution_token=NULL, owner_worker_id=NULL, updated_at=?
           WHERE mission_id=? AND tool IS NULL AND state NOT IN ('done','failed','blocked','cancelled')
             AND EXISTS (SELECT 1 FROM budget_reservations r WHERE r.task_id=tasks.id
                         AND r.status IN ('reserved','interrupted'))""",
        (now(), mission_id))
    cur = conn.execute(
        """UPDATE tasks SET state='pending', execution_token=NULL, owner_worker_id=NULL, updated_at=?
           WHERE mission_id=? AND state IN ('assigned','running','validating')""",
        (now(), mission_id))
    n = cur.rowcount
    conn.execute(
        """UPDATE missions SET state='planned', owner_worker_id=NULL, lease_token=NULL,
             lease_expires_at=0, heartbeat_at=NULL, updated_at=? WHERE id=?""",
        (now(), mission_id))
    return n


def recover_abandoned(conn: sqlite3.Connection, at: float | None = None) -> dict:
    """Récupération exclusive des missions abandonnées (bail expiré + worker arrêté/silencieux)."""
    t = epoch() if at is None else at
    with transaction(conn, immediate=True):
        rows = conn.execute(
            """SELECT m.id FROM missions m LEFT JOIN workers w ON w.worker_id=m.owner_worker_id
               WHERE m.state='running' AND m.lease_expires_at <= ?
                 AND (w.state='stopped' OR w.last_heartbeat IS NULL OR w.last_heartbeat <= m.lease_expires_at)
               ORDER BY m.priority, m.created_at""",
            (t,)).fetchall()
        tasks = 0
        for r in rows:
            tasks += _recover_mission(conn, r["id"])
        # Tâches actives orphelines d'une mission déjà replanifiée (crash entre deux écritures).
        cur = conn.execute(
            """UPDATE tasks SET state='pending', execution_token=NULL, owner_worker_id=NULL, updated_at=?
               WHERE state IN ('assigned','running','validating')
                 AND mission_id IN (SELECT id FROM missions WHERE state='planned')""",
            (now(),))
        tasks += cur.rowcount
        if rows or tasks:
            log_event(conn, "warning", "leases", f"reprise exclusive : {len(rows)} mission(s), {tasks} tâche(s)",
                      data={"missions": [r["id"] for r in rows]})
    return {"recovered_missions": len(rows), "recovered_tasks": tasks}


def claim_next(conn: sqlite3.Connection, worker_id: str, lease_seconds: float = 30.0) -> MissionLease | None:
    if lease_seconds <= 0:
        raise ValueError("lease_seconds doit être positif")
    register_worker(conn, worker_id)
    with transaction(conn, immediate=True):
        recover_abandoned(conn)
        row = conn.execute(
            "SELECT id, fencing_token FROM missions WHERE state='planned' ORDER BY priority ASC, created_at ASC LIMIT 1").fetchone()
        if row is None:
            return None
        t = epoch()
        token = uuid.uuid4().hex
        fencing = int(row["fencing_token"]) + 1
        expires = t + lease_seconds
        cur = conn.execute(
            """UPDATE missions SET state='running', owner_worker_id=?, lease_token=?, lease_expires_at=?,
                 heartbeat_at=?, fencing_token=?, run_attempts=run_attempts+1, updated_at=?
               WHERE id=? AND state='planned'""",
            (worker_id, token, expires, t, fencing, now(), row["id"]))
        if cur.rowcount != 1:
            return None
        conn.execute("UPDATE workers SET last_heartbeat=? WHERE worker_id=?", (t, worker_id))
        return MissionLease(row["id"], worker_id, token, fencing, expires)


def claim_mission(conn: sqlite3.Connection, mission_id: str, worker_id: str,
                  lease_seconds: float = 30.0) -> MissionLease | None:
    """Revendique une mission précise si elle est planifiée (ou abandonnée récupérable)."""
    register_worker(conn, worker_id)
    with transaction(conn, immediate=True):
        recover_abandoned(conn)
        row = conn.execute("SELECT id, fencing_token, state FROM missions WHERE id=?", (mission_id,)).fetchone()
        if row is None:
            raise KeyError(f"mission inconnue : {mission_id}")
        if row["state"] != "planned":
            return None
        t = epoch()
        token = uuid.uuid4().hex
        fencing = int(row["fencing_token"]) + 1
        expires = t + lease_seconds
        conn.execute(
            """UPDATE missions SET state='running', owner_worker_id=?, lease_token=?, lease_expires_at=?,
                 heartbeat_at=?, fencing_token=?, run_attempts=run_attempts+1, updated_at=?
               WHERE id=? AND state='planned'""",
            (worker_id, token, expires, t, fencing, now(), mission_id))
        return MissionLease(mission_id, worker_id, token, fencing, expires)


def renew_mission(conn: sqlite3.Connection, lease: MissionLease, lease_seconds: float) -> bool:
    t = epoch()
    with transaction(conn, immediate=True):
        cur = conn.execute(
            """UPDATE missions SET lease_expires_at=?, heartbeat_at=?, updated_at=?
               WHERE id=? AND owner_worker_id=? AND lease_token=? AND fencing_token=?
                 AND state='running' AND cancel_requested=0 AND lease_expires_at > ?""",
            (t + lease_seconds, t, now(), lease.mission_id, lease.worker_id, lease.token,
             lease.fencing_token, t))
        ok = cur.rowcount == 1
        if ok:
            conn.execute("UPDATE workers SET last_heartbeat=? WHERE worker_id=? AND state='alive'", (t, lease.worker_id))
        return ok


def assert_mission(conn: sqlite3.Connection, lease: MissionLease) -> None:
    row = conn.execute(
        """SELECT lease_expires_at FROM missions
           WHERE id=? AND owner_worker_id=? AND lease_token=? AND fencing_token=?
             AND state='running' AND cancel_requested=0""",
        (lease.mission_id, lease.worker_id, lease.token, lease.fencing_token)).fetchone()
    if row is None or float(row["lease_expires_at"]) <= epoch():
        raise LeaseLostError(f"bail perdu pour la mission {lease.mission_id}")


def complete_mission(conn: sqlite3.Connection, lease: MissionLease, state: str, result: dict) -> bool:
    import json
    with transaction(conn, immediate=True):
        assert_mission(conn, lease)
        cur = conn.execute(
            """UPDATE missions SET state=?, result_json=?, lease_expires_at=0, heartbeat_at=?, updated_at=?
               WHERE id=? AND owner_worker_id=? AND lease_token=? AND fencing_token=? AND state='running'""",
            (state, json.dumps(result, ensure_ascii=False), epoch(), now(),
             lease.mission_id, lease.worker_id, lease.token, lease.fencing_token))
        return cur.rowcount == 1


def release_mission(conn: sqlite3.Connection, lease: MissionLease, requeue: bool = True) -> bool:
    with transaction(conn, immediate=True):
        row = conn.execute(
            "SELECT cancel_requested FROM missions WHERE id=? AND owner_worker_id=? AND lease_token=? AND fencing_token=? AND state='running'",
            (lease.mission_id, lease.worker_id, lease.token, lease.fencing_token)).fetchone()
        if row is None:
            return False
        if row["cancel_requested"]:
            conn.execute("UPDATE tasks SET state='cancelled', execution_token=NULL, owner_worker_id=NULL, updated_at=? "
                         "WHERE mission_id=? AND state NOT IN ('done','failed','blocked','cancelled')", (now(), lease.mission_id))
            conn.execute("UPDATE missions SET state='cancelled', owner_worker_id=NULL, lease_token=NULL, "
                         "lease_expires_at=0, heartbeat_at=NULL, updated_at=? WHERE id=?", (now(), lease.mission_id))
            return True
        if requeue:
            conn.execute("UPDATE tasks SET state='pending', execution_token=NULL, owner_worker_id=NULL, updated_at=? "
                         "WHERE mission_id=? AND state IN ('assigned','running','validating')", (now(), lease.mission_id))
            conn.execute("UPDATE missions SET state='planned', owner_worker_id=NULL, lease_token=NULL, "
                         "lease_expires_at=0, heartbeat_at=NULL, updated_at=? WHERE id=?", (now(), lease.mission_id))
        else:
            conn.execute("UPDATE missions SET lease_expires_at=0, updated_at=? WHERE id=?", (now(), lease.mission_id))
        return True
