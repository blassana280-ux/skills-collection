"""Communication Bus SUPREME — bus central SQLite avec ACL, anti-usurpation,
déduplication, acquittement, file de messages morts et historique.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid

from .db import log_event, now, transaction
from .security import redact, scan_injection


class Bus:
    def __init__(self, conn: sqlite3.Connection, registry):
        self.conn = conn
        self.registry = registry

    def _known(self, agent_id: str) -> bool:
        return agent_id == "omnibrain-core" or self.registry.get(agent_id) is not None

    def send(self, authenticated_as: str, sender: str, recipient: str, mission_id: str | None,
             msg_type: str, payload: dict, priority: int = 5, confidence: float = 0.5,
             sources: list | None = None, expected: str = "") -> dict:
        # Anti-usurpation : l'expéditeur doit être l'identité authentifiée ou le cerveau central.
        if sender != authenticated_as and authenticated_as != "omnibrain-core":
            raise PermissionError("usurpation d'identité interdite : sender != authenticated_as")
        if not self._known(sender) or not self._known(recipient):
            raise KeyError("expéditeur ou destinataire inconnu")
        # ACL : un spécialiste ne peut écrire qu'à sa division (ou au cerveau/managers).
        s_prof = self.registry.profile(sender) if sender != "omnibrain-core" else None
        r_prof = self.registry.profile(recipient) if recipient != "omnibrain-core" else None
        if s_prof and s_prof["permissions"].get("bus") == "division":
            same_div = r_prof and r_prof["division"] == s_prof["division"]
            if not (same_div or recipient == "omnibrain-core" or (r_prof and r_prof["kind"] == "manager")):
                raise PermissionError("ACL bus : destinataire hors division")
        # Les payloads externes sont traités comme données non fiables.
        payload_text = json.dumps(payload, ensure_ascii=False)
        injection = scan_injection(payload_text)
        dedup_key = hashlib.sha256(f"{sender}|{recipient}|{mission_id}|{msg_type}|{payload_text}".encode()).hexdigest()
        mid = f"msg-{uuid.uuid4().hex[:12]}"
        try:
            with transaction(self.conn):
                self.conn.execute(
                    """INSERT INTO bus_messages(id,sender,recipient,mission_id,type,payload_json,priority,
                       confidence,sources,expected,created_at,dedup_key) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (mid, sender, recipient, mission_id, msg_type, redact(payload_text), priority,
                     confidence, json.dumps(sources or []), expected, now(), dedup_key))
        except sqlite3.IntegrityError:
            existing = self.conn.execute("SELECT id FROM bus_messages WHERE dedup_key=?", (dedup_key,)).fetchone()
            return {"id": existing["id"], "duplicated": True, "injection_flags": injection}
        log_event(self.conn, "debug", "bus", f"{sender} -> {recipient} : {msg_type}", mission_id)
        return {"id": mid, "duplicated": False, "injection_flags": injection}

    def inbox(self, recipient: str, include_delivered: bool = False) -> list[dict]:
        q = "SELECT * FROM bus_messages WHERE recipient=? AND dead=0"
        if not include_delivered:
            q += " AND delivered=0"
        q += " ORDER BY priority, created_at"
        return [dict(r) for r in self.conn.execute(q, (recipient,))]

    def deliver(self, message_id: str) -> None:
        with transaction(self.conn):
            self.conn.execute("UPDATE bus_messages SET delivered=1 WHERE id=?", (message_id,))

    def ack(self, message_id: str) -> None:
        with transaction(self.conn):
            self.conn.execute("UPDATE bus_messages SET delivered=1, ack=1 WHERE id=?", (message_id,))

    def dead_letter(self, message_id: str, reason: str) -> None:
        with transaction(self.conn):
            self.conn.execute("UPDATE bus_messages SET dead=1, dead_reason=? WHERE id=?", (reason, message_id))
        log_event(self.conn, "warning", "bus", f"message mort {message_id}: {reason}")

    def history(self, mission_id: str | None = None, limit: int = 100) -> list[dict]:
        if mission_id:
            rows = self.conn.execute("SELECT * FROM bus_messages WHERE mission_id=? ORDER BY created_at DESC LIMIT ?",
                                     (mission_id, limit)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM bus_messages ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        total = self.conn.execute("SELECT COUNT(*) c FROM bus_messages").fetchone()["c"]
        dead = self.conn.execute("SELECT COUNT(*) c FROM bus_messages WHERE dead=1").fetchone()["c"]
        acked = self.conn.execute("SELECT COUNT(*) c FROM bus_messages WHERE ack=1").fetchone()["c"]
        return {"total": total, "dead": dead, "acked": acked, "pending": total - dead - acked}
