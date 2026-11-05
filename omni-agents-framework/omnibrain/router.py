"""Routage : sélection de l'escouade à partir de la matrice et de la demande."""

from __future__ import annotations

import unicodedata

from .classifier import Classifier, _normalize, keyword_present
from .models import AgentDef, RoutingDecision


class Router:
    def __init__(self, registry, classifier: Classifier | None = None):
        self.registry = registry
        self.matrix = registry.matrix
        self.classifier = classifier or Classifier(self.matrix)
        self.risk_domains = set(self.matrix["classification"].get("risk_domains", []))

    def _score_agents(self, norm: str) -> dict[str, int]:
        scores: dict[str, int] = {}
        for entry in self.matrix["agents"]:
            if entry.get("orchestrator"):
                continue  # OmniBrain orchestre, il n'est jamais membre d'une escouade
            score = 0
            for kw in entry.get("keywords", []):
                if keyword_present(kw, norm):
                    score += 1
            scores[entry["id"]] = score
        return scores

    def route(self, task: str, classification=None) -> RoutingDecision:
        norm = _normalize(task)
        classification = classification or self.classifier.classify(task)
        raw_scores = self._score_agents(norm)
        reasons: list[str] = []

        ranked = sorted(
            ((agent_id, score) for agent_id, score in raw_scores.items() if score > 0),
            key=lambda item: (-item[1], item[0]),
        )
        if not ranked:
            # Filet de sécurité : aucune correspondance -> cadrage produit + recherche.
            ranked = [("product-delivery", 1), ("research-intel", 1)]
            reasons.append("aucun mot-clé métier détecté : escouade de cadrage par défaut")

        selected_ids = [agent_id for agent_id, _ in ranked[: classification.squad_size]]

        # ---- Renforts obligatoires selon le contexte ----------------------
        # Une demande simple reste mono-agent : les renforts ne s'appliquent
        # qu'aux niveaux moyenne/complexe, conformément au manifeste.
        mandatory: list[str] = []

        def ensure(agent_id: str, why: str) -> None:
            if agent_id not in selected_ids and agent_id not in mandatory:
                mandatory.append(agent_id)
                reasons.append(why)

        if classification.level != "simple":
            domains = set(classification.domains)
            code_domains = {"ui", "frontend", "backend", "data", "ai"}
            if domains & code_domains:
                ensure("qa-test", "toucher du code rend QA obligatoire")
            if classification.level == "complexe":
                ensure("adversarial-reviewer", "revue adverse obligatoire pour une demande complexe")
            if domains & self.risk_domains:
                if "security" in domains:
                    ensure("security", "domaine sécurité à risque : expert dédié")
                if "devops" in domains:
                    ensure("devops-sre", "domaine devops à risque : expert dédié")
                if "finance-ohada" in domains:
                    ensure("ohada-finance", "domaine OHADA à risque : expert dédié")

        # Les renforts obligatoires ne peuvent pas être évincés par le plafond :
        # on ajoute d'abord les obligatoires, puis on libère de la place en
        # retirant les candidats les moins bien scorés et non obligatoires.
        selected_ids.extend(mandatory)
        score_of = dict(ranked)
        while len(selected_ids) > self.classifier.max_squad:
            evictable = [
                agent_id for agent_id in selected_ids
                if agent_id not in mandatory and agent_id in score_of
            ]
            if not evictable:
                break  # que des obligatoires : on garde le tout, même au-delà du plafond
            victim = min(evictable, key=lambda agent_id: (score_of[agent_id], agent_id))
            selected_ids.remove(victim)
            reasons.append(f"plafond d'escouade atteint : {victim} non retenu (score faible)")

        agents = [self.registry.by_id(agent_id) for agent_id in selected_ids]
        scores = {agent.id: raw_scores.get(agent.id, 0) for agent in agents}
        for agent_id, score in ranked:
            if agent_id in scores and score:
                scores.setdefault(agent_id, score)
        reasons.insert(0, f"{len(agents)} agent(s) retenu(s) sur {len(ranked)} candidats matchés")

        contracts = self._contracts_for(selected_ids)
        return RoutingDecision(
            agents=agents,
            scores=scores,
            reasons=reasons,
            contracts=contracts,
            wave=0,
        )

    def _contracts_for(self, squad_ids: list[str]):
        members = set(squad_ids)
        active = []
        for contract in self.registry.contracts():
            involved = set(contract.producers) | set(contract.consumers)
            # Un contrat n'est émis que si producteur ET au moins un consommateur
            # sont dans l'escouade : sinon personne ne peut l'honorer.
            if members.intersection(contract.producers) and members.intersection(contract.consumers):
                active.append(contract)
        return active
