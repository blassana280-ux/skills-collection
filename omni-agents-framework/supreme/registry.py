"""Agent Registry SUPREME — registre SQLite exploitable par le runtime.

Sépare profil (catalogue versionné), enregistrement (base), statut (preuve) et
instance d'exécution (runtime). Les transitions de statut exigent des preuves.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from .catalog import load_catalog
from .config import AGENT_STATUSES
from .db import get_conn, log_event, now, transaction


class Registry:
    def __init__(self, conn: sqlite3.Connection | None = None):
        self.conn = conn or get_conn()

    def sync_catalog(self) -> dict[str, int]:
        """Charge le catalogue versionné dans le registre (idempotent)."""
        profiles = load_catalog()
        added = updated = 0
        with transaction(self.conn):
            for p in profiles:
                existing = self.conn.execute("SELECT status, version FROM agents WHERE id=?", (p["id"],)).fetchone()
                if existing is None:
                    self.conn.execute(
                        "INSERT INTO agents(id,division,kind,name,profile_json,status,version,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                        (p["id"], p["division"], p["kind"], p["name"], json.dumps(p, ensure_ascii=False),
                         "registered", p["version"], now()))
                    self._history(p["id"], "registered", "catalogue SUPREME 1000")
                    added += 1
                elif existing["version"] != p["version"]:
                    self.conn.execute(
                        "UPDATE agents SET profile_json=?, version=?, updated_at=? WHERE id=?",
                        (json.dumps(p, ensure_ascii=False), p["version"], now(), p["id"]))
                    updated += 1
        log_event(self.conn, "info", "registry", f"catalogue synchronisé : {added} ajoutés, {updated} mis à jour")
        return {"added": added, "updated": updated, "total": len(profiles)}

    def _history(self, agent_id: str, status: str, evidence: str) -> None:
        self.conn.execute(
            "INSERT INTO agent_status_history(agent_id,status,evidence,at) VALUES(?,?,?,?)",
            (agent_id, status, evidence, now()))

    def get(self, agent_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["profile"] = json.loads(d.pop("profile_json"))
        return d

    def profile(self, agent_id: str) -> dict[str, Any]:
        a = self.get(agent_id)
        if a is None:
            raise KeyError(f"agent inconnu : {agent_id}")
        return a["profile"]

    def list(self, division: str | None = None, kind: str | None = None,
             status: str | None = None) -> list[dict[str, Any]]:
        q = "SELECT * FROM agents WHERE 1=1"
        params: list = []
        if division:
            q += " AND division=?"
            params.append(division)
        if kind:
            q += " AND kind=?"
            params.append(kind)
        if status:
            q += " AND status=?"
            params.append(status)
        q += " ORDER BY id"
        out = []
        for row in self.conn.execute(q, params):
            d = dict(row)
            d["profile"] = json.loads(d.pop("profile_json"))
            out.append(d)
        return out

    def set_status(self, agent_id: str, status: str, evidence: str) -> None:
        if status not in AGENT_STATUSES:
            raise ValueError(f"statut inconnu : {status}")
        if status in ("operational", "monitored") and not evidence.strip():
            raise ValueError("un statut operational/monitored exige une preuve d'exécution réelle")
        with transaction(self.conn):
            self.conn.execute("UPDATE agents SET status=?, updated_at=? WHERE id=?", (status, now(), agent_id))
            self._history(agent_id, status, evidence)
        log_event(self.conn, "info", "registry", f"{agent_id} -> {status}", data={"evidence": evidence[:200]})

    def status_counts(self, kind: str | None = None) -> dict[str, int]:
        q = "SELECT status, COUNT(*) c FROM agents"
        params: list = []
        if kind:
            q += " WHERE kind=?"
            params.append(kind)
        q += " GROUP BY status"
        counts = {s: 0 for s in AGENT_STATUSES}
        for row in self.conn.execute(q, params):
            counts[row["status"]] = row["c"]
        return counts

    def divisions_summary(self) -> list[dict[str, Any]]:
        out = []
        for div in sorted({a["division"] for a in self.list()}):
            members = self.list(division=div, kind="specialist")
            counts = {s: 0 for s in AGENT_STATUSES}
            for m in members:
                counts[m["status"]] += 1
            manager = next((a for a in self.list(division=div, kind="manager")), None)
            out.append({"division": div, "total": len(members), "status_counts": counts,
                        "manager": manager["id"] if manager else None,
                        "manager_status": manager["status"] if manager else None})
        return out

    def search(self, terms: str, limit: int = 10) -> list[dict[str, Any]]:
        """Recherche par compétences/objectif/nom (lexicale, déterministe)."""
        tokens = [t for t in terms.lower().split() if len(t) > 2]
        scored = []
        for a in self.list(kind="specialist"):
            p = a["profile"]
            text = " ".join([p["name"], p["objective"], " ".join(p["primary_skills"]), p["specialization"]]).lower()
            score = sum(text.count(t) for t in tokens)
            if score > 0:
                scored.append((score, a))
        scored.sort(key=lambda x: (-x[0], x[1]["id"]))
        return [a for _, a in scored[:limit]]
