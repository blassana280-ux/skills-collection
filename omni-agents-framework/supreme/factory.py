"""Agent Factory SUPREME — création contrôlée de nouveaux profils.

Détecte les doublons, valide le schéma, enregistre, teste en isolation, active
sur preuve. Versions et rollback. Les créations sont réversibles.
"""
from __future__ import annotations

import json
import sqlite3
import uuid

from .config import DEFAULT_LIMITS, DEFAULT_MEMORY_POLICY, GLOBAL_FORBIDDEN
from .db import log_event, now, transaction
from .profiles import EVAL_IDS, REQUIRED_FIELDS


class AgentFactory:
    def __init__(self, conn: sqlite3.Connection, registry, evaluation):
        self.conn = conn
        self.registry = registry
        self.evaluation = evaluation

    def _dedup(self, name: str, objective: str, skills: list[str], task: str) -> list[str]:
        errors = []
        for a in self.registry.list():
            p = a["profile"]
            if p["name"] == name:
                errors.append(f"nom déjà utilisé : {name} ({a['id']})")
            if p["objective"] == objective:
                errors.append(f"objectif déjà couvert : {objective} ({a['id']})")
            if (p["objective"], tuple(sorted(p["primary_skills"])), p["allowed_tasks"][0]) == (objective, tuple(sorted(skills)), task):
                errors.append(f"clone détecté de {a['id']}")
        return errors

    def create(self, spec: dict) -> dict:
        """spec minimal : {name, division, objective, primary_skills[3], task, eval, tool?, risk?}."""
        for req in ("name", "division", "objective", "primary_skills", "task", "eval"):
            if not spec.get(req):
                raise ValueError(f"champ requis manquant : {req}")
        if len(spec["primary_skills"]) != 3:
            raise ValueError("3 compétences principales requises")
        dups = self._dedup(spec["name"], spec["objective"], spec["primary_skills"], spec["task"])
        if dups:
            raise ValueError("doublons : " + "; ".join(dups))
        aid = f"F-{uuid.uuid4().hex[:8]}-{spec['name'].lower().replace(' ', '-')[:24]}"
        tool = spec.get("tool", "")
        rep = ({"id": "representative", "mode": "tool", "tool": tool, "check": "tool_eval"} if tool
               else {"id": "representative", "mode": "llm", "rubric": spec["eval"], "status": "deferred_no_provider"})
        profile = {
            "id": aid, "name": spec["name"], "division": spec["division"], "kind": "specialist",
            "role": spec["name"], "specialization": f"{spec['name']} — {spec['objective']}",
            "objective": spec["objective"],
            "system_instructions": f"Tu es {spec['name']}. Objectif : {spec['objective']}. Respecte les politiques OmniBrain.",
            "primary_skills": spec["primary_skills"], "secondary_skills": ["rapport structuré"],
            "allowed_tasks": [spec["task"]], "forbidden_tasks": list(GLOBAL_FORBIDDEN),
            "input_types": ["demande structurée"], "output_format": "JSON structuré",
            "allowed_tools": [tool] if tool else [],
            "permissions": {"memory_read": ["central", "individual", "division", "collective"],
                            "memory_write": ["individual", "division"], "bus": "division",
                            "network": "deny", "code_exec": "deny", "github_write": False,
                            "secrets": "none", "spawn_agents": False},
            "recommended_models": ["reasoning-general"], "memory_policy": dict(DEFAULT_MEMORY_POLICY),
            "collaborators": {"manager": "omnibrain-core"}, "dependencies": {"tools": [tool] if tool else [], "skills": []},
            "quality_criteria": [spec["eval"], "preuves vérifiables"],
            "eval_tests": [
                {"id": "load", "mode": "offline", "check": "profile_loads"},
                {"id": "config", "mode": "offline", "check": "schema_valid"},
                rep,
                {"id": "structured_output", "mode": "offline", "check": "output_contract"},
                {"id": "permissions", "mode": "offline", "check": "least_privilege"},
                {"id": "errors", "mode": "offline", "check": "error_handling"},
                {"id": "quality", "mode": "offline", "check": "quality_criteria"},
            ],
            "risk_level": spec.get("risk", "low"), "execution_limits": dict(DEFAULT_LIMITS),
            "version": "1.0.0",
            "changelog": [{"version": "1.0.0", "date": now()[:10], "change": "création Agent Factory"}],
            "status": "registered",
        }
        missing = [f for f in REQUIRED_FIELDS if f not in profile]
        if missing:
            raise ValueError(f"profil incomplet : {missing}")
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO agents(id,division,kind,name,profile_json,status,version,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (aid, spec["division"], "specialist", spec["name"], json.dumps(profile, ensure_ascii=False),
                 "registered", "1.0.0", now()))
            self.conn.execute("INSERT INTO agent_versions(agent_id,version,profile_json,created_at) VALUES(?,?,?,?)",
                              (aid, "1.0.0", json.dumps(profile, ensure_ascii=False), now()))
        log_event(self.conn, "info", "factory", f"agent créé : {aid}")
        # Test en isolation puis activation sur preuve
        v = self.evaluation.validate_agent(aid)
        activation = self.evaluation.activate_agent(aid) if v["validated"] else {"activated": False}
        return {"id": aid, "profile": profile, "validated": v["validated"], "activated": activation.get("activated", False)}

    def update(self, agent_id: str, changes: dict, reason: str) -> dict:
        prof = self.registry.profile(agent_id)
        old_version = prof["version"]
        with transaction(self.conn):
            self.conn.execute("INSERT INTO agent_versions(agent_id,version,profile_json,created_at) VALUES(?,?,?,?)",
                              (agent_id, old_version, json.dumps(prof, ensure_ascii=False), now()))
        prof.update(changes)
        major, minor, patch = map(int, prof["version"].split("."))
        prof["version"] = f"{major}.{minor + 1}.{patch}"
        prof["changelog"].append({"version": prof["version"], "date": now()[:10], "change": reason})
        with transaction(self.conn):
            self.conn.execute("UPDATE agents SET profile_json=?, version=?, updated_at=? WHERE id=?",
                              (json.dumps(prof, ensure_ascii=False), prof["version"], now(), agent_id))
        return {"id": agent_id, "version": prof["version"]}

    def rollback(self, agent_id: str) -> dict:
        row = self.conn.execute("SELECT * FROM agent_versions WHERE agent_id=? ORDER BY id DESC LIMIT 1", (agent_id,)).fetchone()
        if row is None:
            raise KeyError("aucune version antérieure")
        prof = json.loads(row["profile_json"])
        with transaction(self.conn):
            self.conn.execute("UPDATE agents SET profile_json=?, version=?, updated_at=? WHERE id=?",
                              (row["profile_json"], prof["version"], now(), agent_id))
        log_event(self.conn, "info", "factory", f"rollback {agent_id} -> {prof['version']}")
        return {"id": agent_id, "version": prof["version"]}

    def remove(self, agent_id: str, reason: str) -> None:
        """Suppression contrôlée d'un agent créé par la factory (réversible via versions)."""
        if not agent_id.startswith("F-"):
            raise PermissionError("seuls les agents créés par la factory peuvent être supprimés")
        with transaction(self.conn):
            self.conn.execute("DELETE FROM agents WHERE id=?", (agent_id,))
        log_event(self.conn, "info", "factory", f"agent supprimé : {agent_id} ({reason})")
