"""Génération déterministe du catalogue des 1000 agents + 20 chefs de division.

Source de vérité : supreme/divisions/divNN.py. Sorties versionnées :
  catalog/agents.json        (profils complets)
  catalog/divisions.json     (métadonnées des 20 divisions)
  catalog/CATALOG-SUPREME.md (tableau lisible)
Le runtime lit le catalogue ; aucun processus permanent par agent.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .config import CATALOG_DIR
from .divisions import load_divisions, load_rows
from .profiles import _skill_index, expand_manager, expand_profile, validate_catalog, _resolve_neighbors
from .tools import CODE_EXEC_TOOLS, tool_names


def generate() -> tuple[list[dict], list[dict], list[str]]:
    divisions = load_divisions()
    rows = load_rows()
    skill_index = _skill_index()
    profiles: list[dict] = []
    for div in divisions:
        for idx, row in enumerate(rows[div.num], 1):
            from .profiles import parse_row
            parsed = parse_row(row)
            profiles.append(expand_profile(div, parsed, idx, len(rows[div.num]), skill_index, CODE_EXEC_TOOLS))
    _resolve_neighbors(profiles)
    managers = [expand_manager(div) for div in divisions]
    errors = validate_catalog(profiles, managers, tool_names())
    return profiles, managers, errors


def write_catalog() -> tuple[int, list[str]]:
    profiles, managers, errors = generate()
    if errors:
        return 0, errors
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    divisions = load_divisions()
    all_profiles = profiles + managers
    (CATALOG_DIR / "agents.json").write_text(
        json.dumps(all_profiles, ensure_ascii=False, indent=1), encoding="utf-8")
    (CATALOG_DIR / "divisions.json").write_text(
        json.dumps([asdict(d) for d in divisions], ensure_ascii=False, indent=1), encoding="utf-8")
    # Markdown lisible
    lines = ["# Catalogue OMNIBRAIN SUPREME 1000", "",
             f"**{len(profiles)} spécialistes** répartis en **{len(divisions)} divisions** de 50, "
             f"plus **{len(managers)} chefs de division**.", "",
             "Statut initial : `registered`. L'activation en `operational` exige une exécution réelle réussie.", ""]
    for div in divisions:
        members = [p for p in profiles if p["division"] == div.id]
        lines.append(f"## {div.id} — {div.title}")
        lines.append(f"*{div.mission}* · Chef : `{div.manager_id}` · Risque : {div.risk}")
        lines.append("")
        lines.append("| ID | Nom | Objectif | Outil représentatif |")
        lines.append("| --- | --- | --- | --- |")
        for p in members:
            rep = next(e for e in p["eval_tests"] if e["id"] == "representative")
            tool = rep.get("tool", "— (LLM requis)")
            lines.append(f"| `{p['id']}` | {p['name']} | {p['objective']} | `{tool}` |")
        lines.append("")
    (CATALOG_DIR / "CATALOG-SUPREME.md").write_text("\n".join(lines), encoding="utf-8")
    return len(all_profiles), []


def load_catalog() -> list[dict]:
    p = CATALOG_DIR / "agents.json"
    if not p.is_file():
        write_catalog()
    return json.loads(p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import sys
    if "--check" in sys.argv:
        _, _, errors = generate()
        if errors:
            print("\n".join(errors))
            sys.exit(1)
        print("OK — 1000 spécialistes + 20 chefs, aucun doublon, profils complets")
    else:
        count, errors = write_catalog()
        if errors:
            print("\n".join(errors))
            sys.exit(1)
        print(f"Catalogue écrit : {count} profils")
