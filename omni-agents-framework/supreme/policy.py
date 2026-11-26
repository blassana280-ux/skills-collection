"""Policy Engine SUPREME — gouvernance par niveau de risque + approbations humaines.

Réutilise le RBAC V4 (omni.sandbox.runtime). Les agents ne peuvent jamais
modifier les politiques, permissions ou règles de sécurité eux-mêmes.
"""
from __future__ import annotations

import json
import sqlite3
import uuid

from .config import ACTION_RISK, RISK_LEVELS
from .db import log_event, now, transaction

# Réutilisation du RBAC éprouvé V4.
from omni.sandbox.runtime import RBAC, IRREVERSIBLE  # noqa: E402

PROTECTED_ACTIONS = {"change_policy", "write_secret", "merge_pr", "deploy", "delete_data", "spend", "write_main"}


def classify_action(action: str) -> str:
    return ACTION_RISK.get(action, "medium")


def requires_approval(risk: str) -> bool:
    return risk in ("high", "critical")


class PolicyEngine:
    def __init__(self, conn: sqlite3.Connection, rbac: RBAC | None = None):
        self.conn = conn
        self.rbac = rbac or RBAC()

    def check(self, actor: str, action: str, human_approval: bool = False) -> dict:
        """Retourne {allowed, reason, risk, approval_required}."""
        risk = classify_action(action)
        if action in PROTECTED_ACTIONS and self.rbac.role_of(actor) != "human":
            return {"allowed": False, "reason": "action protégée : réservée à un humain approuvé",
                    "risk": risk, "approval_required": True}
        if not self.rbac.allow(actor, action, human_approval=human_approval):
            return {"allowed": False, "reason": f"RBAC refuse {action} pour {actor}",
                    "risk": risk, "approval_required": requires_approval(risk)}
        if requires_approval(risk) and not human_approval:
            return {"allowed": False, "reason": "approbation humaine requise",
                    "risk": risk, "approval_required": True}
        return {"allowed": True, "reason": "autorisé", "risk": risk, "approval_required": False}

    def request_approval(self, action: str, requested_by: str, context: dict | None = None) -> str:
        aid = f"apr-{uuid.uuid4().hex[:12]}"
        risk = classify_action(action)
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO approvals(id,action,risk,requested_by,status,context_json,created_at) VALUES(?,?,?,?,?,?,?)",
                (aid, action, risk, requested_by, "pending", json.dumps(context or {}, ensure_ascii=False), now()))
        log_event(self.conn, "info", "policy", f"approbation demandée : {action}", data={"approval_id": aid, "risk": risk})
        return aid

    def decide(self, approval_id: str, approved: bool, decided_by: str) -> dict:
        if self.rbac.role_of(decided_by) != "human":
            raise PermissionError("seul un humain peut décider une approbation")
        with transaction(self.conn):
            row = self.conn.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
            if row is None:
                raise KeyError(f"approbation inconnue : {approval_id}")
            if row["status"] != "pending":
                raise ValueError("approbation déjà décidée")
            self.conn.execute(
                "UPDATE approvals SET status=?, decided_at=?, decided_by=? WHERE id=?",
                ("approved" if approved else "rejected", now(), decided_by, approval_id))
        log_event(self.conn, "info", "policy", f"approbation {approval_id} {'approuvée' if approved else 'rejetée'} par {decided_by}")
        return {"id": approval_id, "status": "approved" if approved else "rejected"}

    def pending_approvals(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM approvals WHERE status='pending' ORDER BY created_at").fetchall()
        return [dict(r) for r in rows]

    def approval(self, approval_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
        return dict(row) if row else None
