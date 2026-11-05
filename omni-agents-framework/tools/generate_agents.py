#!/usr/bin/env python3
"""Génère les fiches agents du catalogue (103 en v4) et le catalogue TOML à partir de tools/catalog_*.py.

Sorties :
    specialized/specialized-<id>-agent.md   (fiche par agent)
    catalog/catalog-100.toml                (entrées [[agents]] pour la matrice)

Usage :
    python3 tools/generate_agents.py           # génère
    python3 tools/generate_agents.py --check   # vérifie seulement (compte, doublons)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.agent_spec import AgentSpec  # noqa: E402
from tools import (  # noqa: E402
    catalog_01_engineering,
    catalog_02_data_ai,
    catalog_03_cloud,
    catalog_04_security,
    catalog_05_qa_design,
    catalog_06_product_marketing,
    catalog_07_finance_sectors,
)

EXPECTED_SPECS = 103  # 100 agents v3 + 3 agents v4 (télémétrie, mémoire, gate humaine)

MODULES = [
    catalog_01_engineering,
    catalog_02_data_ai,
    catalog_03_cloud,
    catalog_04_security,
    catalog_05_qa_design,
    catalog_06_product_marketing,
    catalog_07_finance_sectors,
]

UNIVERSAL_PROTOCOLS = (
    "**Raisonner par l'exécution** : ne jamais affirmer qu'une chose fonctionne sans l'avoir exécutée, testée ou tracée.",
    "**Preuve fraîche** : re-vérifier les affirmations factuelles sur des sources courantes. Verdict par défaut d'un travail non vérifié : NEEDS WORK.",
    "**Cause racine avant correctif** : diagnostiquer avant réparer ; un symptôme n'est pas une cause.",
    "**Économie de tokens** : contexte minimal et ciblé, lecture paresseuse des références, aucun dump hors périmètre.",
    "**Mode escouade** : annoncer son id d'agent ; travailler en brief isolé, contrats d'interface respectés, vague parallèle unique.",
    "**Fraîcheur d'abord** : les faits datés (lois, versions, tarifs, menaces) se cherchent, ils ne se supposent pas.",
)

SQUAD_TITLES = {
    "engineering": "Ingénierie logicielle",
    "data-ai": "Data & IA",
    "cloud-infra": "Cloud & Infrastructure",
    "security": "Sécurité",
    "qa-testing": "QA & Tests",
    "design-ux": "Design & UX",
    "product-delivery": "Produit & Gestion",
    "marketing-growth": "Marketing & Croissance",
    "finance-legal": "Finance & Juridique",
    "west-africa-sectors": "Secteurs ouest-africains & Localisation",
}


def all_specs() -> list[AgentSpec]:
    specs: list[AgentSpec] = []
    for module in MODULES:
        specs.extend(module.SPECS)
    return specs


def validate_specs(specs: list[AgentSpec]) -> list[str]:
    errors: list[str] = []
    ids: dict[str, str] = {}
    for spec in specs:
        if spec.id in ids:
            errors.append(f"id dupliqué : {spec.id} ({ids[spec.id]} / {spec.squad})")
        ids[spec.id] = spec.squad
        if len(spec.rules) != 5:
            errors.append(f"{spec.id}: {len(spec.rules)} règles critiques (5 attendues)")
        if not (3 <= len(spec.keywords) <= 12):
            errors.append(f"{spec.id}: {len(spec.keywords)} mots-clés (3 à 12 attendus)")
        if not spec.artifacts:
            errors.append(f"{spec.id}: aucun artefact déclaré")
        if not spec.domains:
            errors.append(f"{spec.id}: aucun domaine")
    return errors


def render_markdown(spec: AgentSpec) -> str:
    squad_title = SQUAD_TITLES.get(spec.squad, spec.squad)
    lines = [
        "---",
        f"id: {spec.id}",
        f"name: {spec.name}",
        f"description: {json.dumps(spec.description, ensure_ascii=False)}",
        f"domains: [{', '.join(spec.domains)}]",
        f"squad: {spec.squad}",
        f"emoji: {json.dumps(spec.emoji, ensure_ascii=False)}",
        f"vibe: {json.dumps(spec.vibe, ensure_ascii=False)}",
        f"risk: {'true' if spec.risk else 'false'}",
        "---",
        "",
        f"# {spec.name}",
        "",
        "## Identité",
        "",
        f"- **Rôle :** spécialiste de l'escouade *{squad_title}* ({spec.squad}).",
        f"- **Personnalité :** discipliné par les preuves, précis sur son périmètre, soucieux de la valeur livrée.",
        "- **Voix :** directe, technique, orientée décisions vérifiables.",
        "- **Standard :** chaque affirmation est sourcée, testée ou marquée NEEDS WORK.",
        "",
        "## Mission principale",
        "",
        spec.mission,
        "",
        "## Règles critiques",
        "",
    ]
    for i, rule in enumerate(spec.rules, start=1):
        lines.append(f"{i}. {rule}")
    lines += [
        "",
        "## Protocoles universels",
        "",
    ]
    for i, protocol in enumerate(UNIVERSAL_PROTOCOLS, start=1):
        lines.append(f"{i}. {protocol}")
    lines += [
        "",
        "## Entrées / sorties",
        "",
        f"- **Entrées :** {spec.inputs}",
        f"- **Sorties :** {spec.outputs} — artefacts : {', '.join(f'`{a}`' for a in spec.artifacts)}.",
        "",
        "## Quand mobiliser",
        "",
        spec.when,
        "",
        "## Bord de croissance",
        "",
        spec.edge,
        "",
    ]
    return "\n".join(lines)


def render_toml_entry(spec: AgentSpec) -> str:
    def array(values: tuple[str, ...]) -> str:
        return "[" + ", ".join(json.dumps(v, ensure_ascii=False) for v in values) + "]"

    lines = [
        "[[agents]]",
        f"id = {json.dumps(spec.id, ensure_ascii=False)}",
        f"name = {json.dumps(spec.name, ensure_ascii=False)}",
        f"file = {json.dumps(f'specialized/specialized-{spec.id}-agent.md', ensure_ascii=False)}",
        f"squad = {json.dumps(spec.squad, ensure_ascii=False)}",
        f"domains = {array(spec.domains)}",
        f"keywords = {array(spec.keywords)}",
        f"artifacts = {array(spec.artifacts)}",
        f"emoji = {json.dumps(spec.emoji, ensure_ascii=False)}",
        f"risk = {'true' if spec.risk else 'false'}",
        "",
    ]
    return "\n".join(lines)


def main(check_only: bool) -> int:
    specs = all_specs()
    errors = validate_specs(specs)
    print(f"spécifications chargées : {len(specs)} agents")
    by_squad: dict[str, int] = {}
    for spec in specs:
        by_squad[spec.squad] = by_squad.get(spec.squad, 0) + 1
    for squad, count in sorted(by_squad.items()):
        print(f"  - {squad:<22} {count} agents")
    risk = sum(1 for s in specs if s.risk)
    print(f"agents à risque : {risk}")

    if errors:
        print("\nERREURS :", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    if check_only:
        print("\n--check : aucune anomalie")
        return 0
    if len(specs) != EXPECTED_SPECS:
        print(f"ERREUR : {EXPECTED_SPECS} agents attendus, {len(specs)} trouvés", file=sys.stderr)
        return 1

    specialized = ROOT / "specialized"
    for spec in specs:
        target = specialized / f"specialized-{spec.id}-agent.md"
        target.write_text(render_markdown(spec), encoding="utf-8")

    catalog_dir = ROOT / "catalog"
    catalog_dir.mkdir(exist_ok=True)
    toml = [
        f"# Catalogue des {len(specs)} agents spécialisés — GÉNÉRÉ par tools/generate_agents.py.",
        "# Ne pas éditer à la main : modifier tools/catalog_*.py puis régénérer.",
        "",
    ]
    for spec in specs:
        toml.append(render_toml_entry(spec))
    (catalog_dir / "catalog-100.toml").write_text("\n".join(toml), encoding="utf-8")
    print(f"\n{len(specs)} fiches écrites dans specialized/ et catalog/catalog-100.toml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(check_only="--check" in sys.argv))
