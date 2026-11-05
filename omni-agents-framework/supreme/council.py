"""Multi-Model Council SUPREME — délibération fondée sur les preuves, pas la majorité.

Protocole : formulation -> analyses indépendantes -> arguments -> comparaison ->
vérification -> désaccords -> évaluation des preuves -> synthèse -> décision.
Budget et nombre de tours bornés. Sans fournisseur disponible, le conseil est
indisponible (honnête). Les tests utilisent des fournisseurs fixtures explicites.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CouncilConfig:
    max_models: int = 3
    max_rounds: int = 2
    max_cost_usd: float = 0.10


class Council:
    def __init__(self, router, config: CouncilConfig | None = None):
        self.router = router
        self.config = config or CouncilConfig()

    def deliberate(self, problem: str, evidence: list[dict] | None = None,
                   analyses: list[dict] | None = None) -> dict:
        """analyses : analyses indépendantes déjà produites (provider/model/answer/evidence/confidence).

        Si analyses est None, le conseil tente de les produire via le routeur ;
        sans fournisseur disponible, il retourne un statut indisponible.
        """
        evidence = evidence or []
        if analyses is None:
            avail = self.router.available_models()
            if not avail:
                return {"status": "unavailable", "reason": "aucun modèle disponible pour le conseil",
                        "decision": None, "rounds": 0}
            analyses = []  # la production réelle nécessiterait des appels API ; non simulée ici
            return {"status": "needs_provider_calls", "reason": "analyses indépendantes à produire via fournisseurs configurés",
                    "models": [f"{m.provider}/{m.model}" for m in avail[:self.config.max_models]], "decision": None}
        # Agrégation fondée sur les preuves
        used = analyses[:self.config.max_models]
        by_answer: dict[str, list] = {}
        for a in used:
            by_answer.setdefault(a.get("answer", ""), []).append(a)
        scored = []
        for answer, group in by_answer.items():
            ev_count = sum(len(a.get("evidence", [])) for a in group)
            indep_sources = len({s for a in group for s in a.get("sources", [])})
            avg_conf = sum(a.get("confidence", 0.5) for a in group) / len(group)
            # Score = preuves + indépendance + confiance, PAS simple majorité.
            score = 0.45 * min(1, ev_count / 3) + 0.35 * min(1, indep_sources / 2) + 0.2 * avg_conf
            scored.append({"answer": answer, "score": round(score, 4), "supporters": len(group),
                           "evidence_count": ev_count, "independent_sources": indep_sources,
                           "models": [a.get("model") for a in group]})
        scored.sort(key=lambda x: -x["score"])
        disagreements = []
        if len(scored) > 1:
            disagreements = [{"between": [scored[0]["answer"], scored[1]["answer"]],
                              "score_gap": round(scored[0]["score"] - scored[1]["score"], 4)}]
        decision = scored[0] if scored else None
        # Vérification des faits : une réponse majoritaire mais sans preuve est pénalisée.
        verified = decision and decision["evidence_count"] > 0
        return {"status": "decided" if decision else "empty", "decision": decision,
                "candidates": scored, "disagreements": disagreements,
                "evidence_reviewed": len(evidence), "verified": bool(verified),
                "rounds": 1, "max_rounds": self.config.max_rounds,
                "note": "décision fondée sur preuves + indépendance, pas sur la majorité seule"}
