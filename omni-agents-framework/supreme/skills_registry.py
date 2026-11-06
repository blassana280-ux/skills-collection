"""Skill Registry SUPREME — indexe les skills documentaires existants (SKILL.md).

Distingue explicitement skill documentaire (instructions, non exécutable) et
outil exécutable (Tool Registry). Réutilise skills_index.json du dépôt.
"""
from __future__ import annotations

import json
from pathlib import Path

from .config import FRAMEWORK_ROOT
from .tools import TOOLS


class SkillRegistry:
    def __init__(self):
        self.skills: list[dict] = []
        p = FRAMEWORK_ROOT.parent / "skills_index.json"
        if p.is_file():
            try:
                self.skills = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self.skills = []

    def list(self, category: str | None = None, limit: int = 100) -> list[dict]:
        out = []
        for s in self.skills:
            if category and s.get("category") != category:
                continue
            out.append({**s, "executable": False, "kind": "documentary_skill"})
            if len(out) >= limit:
                break
        return out

    def search(self, terms: str, limit: int = 10) -> list[dict]:
        tokens = [t for t in terms.lower().split() if len(t) > 2]
        scored = []
        for s in self.skills:
            text = f"{s.get('id','')} {s.get('name','')} {s.get('description','')}".lower()
            score = sum(text.count(t) for t in tokens)
            if score:
                scored.append((score, s))
        scored.sort(key=lambda x: (-x[0], x[1].get("id", "")))
        return [{**s, "executable": False} for _, s in scored[:limit]]

    def executable_tools(self) -> list[dict]:
        return [{"name": t.name, "description": t.description, "risk": t.risk,
                 "executable": True, "version": t.version} for t in TOOLS.values()]

    def stats(self) -> dict:
        cats = {}
        for s in self.skills:
            c = s.get("category", "unknown")
            cats[c] = cats.get(c, 0) + 1
        return {"documentary_skills": len(self.skills), "executable_tools": len(TOOLS),
                "categories": len(cats), "note": "skills documentaires non exécutables ; outils exécutables séparés"}
