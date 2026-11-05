"""Dispatcher : construit les briefs autonomes et le plan d'orchestration.

Tous les briefs sont émis en UNE seule vague (wave 0), avec contextes isolés
et contrats d'interface : jamais d'exécution séquentielle entre agents.
"""

from __future__ import annotations

from pathlib import Path

from .classifier import Classifier
from .models import Brief, OrchestrationPlan
from .registry import Registry
from .router import Router

GATE_CHECKLIST = [
    "G1 — Complétude : chaque livrable de brief est présent, aucun marqueur placeholder (TODO/FIXME/TBD).",
    "G2 — Preuve fraîche : toute affirmation factuelle est sourcée et datée ; les faits temporels sont re-vérifiés.",
    "G3 — Revue adverse : l'Adversarial Reviewer a déposé ses conclusions avec sévérité et verdict.",
    "G4 — Intégration : les contrats d'interface sont respectés et le livrable unique est cohérent.",
]

TOKEN_BUDGETS = {
    "simple": "contexte minimal : la demande + le contrat d'interface uniquement",
    "moyenne": "demande + contrats + sections de référence strictement nécessaires",
    "complexe": "demande + brief + contrats ; lecture paresseuse des références, pas de code non requis",
}


class Dispatcher:
    def __init__(self, root: Path | None = None, matrix: dict | None = None):
        self.registry = Registry(root=root, matrix=matrix)
        self.classifier = Classifier(self.registry.matrix)
        self.router = Router(self.registry, self.classifier)

    def plan(self, task: str) -> OrchestrationPlan:
        classification = self.classifier.classify(task)
        decision = self.router.route(task, classification)
        warnings: list[str] = []

        briefs = [self._brief(task, agent, classification.level) for agent in decision.agents]
        if classification.level == "complexe" and not any(
            a.id == "adversarial-reviewer" for a in decision.agents
        ):
            warnings.append("demande complexe sans Adversarial Reviewer : la G3 ne peut pas être satisfaite")

        return OrchestrationPlan(
            task=task.strip(),
            classification=classification,
            decision=decision,
            briefs=briefs,
            gates_checklist=list(GATE_CHECKLIST),
            warnings=warnings,
        )

    # --------------------------------------------------------------- internes

    def _brief(self, task: str, agent, level: str) -> Brief:
        inputs = ["La demande utilisateur (section « Mission »)", "Les contrats d'interface listés dans le plan"]
        if agent.risk:
            inputs.append("La réglementation / norme applicable dans sa version à jour (à vérifier, ne pas supposer)")
        outputs = [f"Livrables propres à {agent.name} au format Markdown"]
        if agent.artifacts:
            outputs = [f"`{artifact}`" for artifact in agent.artifacts] + outputs
        obligations = [
            "Ne produire que les livrables du brief ; ne pas empiéter sur les autres agents.",
            "Signaler toute affirmation non vérifiée par « NEEDS WORK » plutôt que d'affirmer.",
            "Cause racine avant tout correctif ; preuve d'exécution (commande, trace, source datée).",
            "Économie de tokens : contexte ciblé, aucune lecture hors périmètre.",
        ]
        return Brief(
            agent_id=agent.id,
            agent_name=agent.name,
            emoji=agent.emoji,
            objective=f"({agent.domains[0] if agent.domains else 'expertise'}) traiter la partie de la demande relevant de {agent.name}.",
            context_scope=f"Contexte isolé. Périmètre : {', '.join(agent.domains)}. "
            f"Mots-clés d'activation : {', '.join(agent.keywords[:6])}.",
            inputs=inputs,
            expected_outputs=outputs,
            gate_obligations=obligations,
            token_budget=TOKEN_BUDGETS[level],
        )
