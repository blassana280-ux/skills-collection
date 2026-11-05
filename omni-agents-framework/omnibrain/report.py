"""Rendu du plan d'orchestration en Markdown ou JSON."""

from __future__ import annotations

import json

from .models import OrchestrationPlan


def render_markdown(plan: OrchestrationPlan) -> str:
    c = plan.classification
    lines: list[str] = []
    lines.append("# Plan d'orchestration OmniBrain")
    lines.append("")
    lines.append("## 1. Demande")
    lines.append("")
    lines.append(f"> {plan.task}")
    lines.append("")
    lines.append("## 2. Classification")
    lines.append("")
    lines.append(f"- **Niveau :** {c.level}")
    lines.append(f"- **Score :** {c.score}")
    lines.append(f"- **Domaines détectés :** {', '.join(c.domains) or 'aucun — cadrage par défaut'}")
    lines.append(f"- **Taille d'escouade :** {c.squad_size} agent(s)")
    lines.append("- **Signaux :**")
    for signal in c.signals:
        lines.append(f"  - {signal.label} (+{signal.weight}) — {signal.evidence}")
    lines.append("")
    lines.append("## 3. Escouade — une seule vague parallèle (wave 0)")
    lines.append("")
    lines.append("| Agent | Domaine(s) | Score | Risque | Artefacts |")
    lines.append("|---|---|---|---|---|")
    for agent in plan.decision.agents:
        lines.append(
            f"| {agent.emoji} `{agent.id}` — {agent.name} "
            f"| {', '.join(agent.domains)} | {plan.decision.scores.get(agent.id, 0)} "
            f"| {'oui' if agent.risk else 'non'} | {', '.join(agent.artifacts) or '—'} |"
        )
    lines.append("")
    for reason in plan.decision.reasons:
        lines.append(f"- _Routage :_ {reason}")
    lines.append("")
    lines.append("## 4. Contrats d'interface")
    lines.append("")
    if plan.decision.contracts:
        for contract in plan.decision.contracts:
            lines.append(
                f"- **`{contract.artifact}`** — producteur(s) : "
                f"{', '.join(contract.producers)} ; consommateur(s) : "
                f"{', '.join(contract.consumers)}"
                + (f" ; schéma : `{contract.schema_ref}`" if contract.schema_ref else "")
            )
    else:
        lines.append("_Aucun contrat d'interface requis pour cette escouade._")
    lines.append("")
    lines.append("## 5. Briefs autonomes (émis en parallèle)")
    lines.append("")
    for brief in plan.briefs:
        lines.append(f"### {brief.emoji} Brief — `{brief.agent_id}` ({brief.agent_name})")
        lines.append("")
        lines.append(f"- **Objectif :** {brief.objective}")
        lines.append(f"- **Périmètre de contexte :** {brief.context_scope}")
        lines.append("- **Entrées :**")
        for item in brief.inputs:
            lines.append(f"  - {item}")
        lines.append("- **Sorties attendues :**")
        for item in brief.expected_outputs:
            lines.append(f"  - {item}")
        lines.append("- **Obligations gates :**")
        for item in brief.gate_obligations:
            lines.append(f"  - {item}")
        lines.append(f"- **Budget tokens :** {brief.token_budget}")
        lines.append("")
    lines.append("## 6. Gates qualité (verdict par défaut : NEEDS WORK)")
    lines.append("")
    for gate in plan.gates_checklist:
        lines.append(f"- [ ] {gate}")
    lines.append("")
    lines.append("## 7. Assemblage")
    lines.append("")
    lines.append(
        "OmniBrain assemble les livrables en **un seul document cohérent**, "
        "vérifie chaque gate, puis livre le résultat et le rapport d'orchestration. "
        "La complexité du réseau reste invisible pour l'utilisateur."
    )
    if plan.warnings:
        lines.append("")
        lines.append("## ⚠️ Alertes")
        lines.append("")
        for warning in plan.warnings:
            lines.append(f"- {warning}")
    lines.append("")
    return "\n".join(lines)


def render_json(plan: OrchestrationPlan) -> str:
    return json.dumps(plan.as_dict(), ensure_ascii=False, indent=2)
