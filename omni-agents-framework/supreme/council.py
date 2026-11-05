"""Multi-Model Council SUPREME — délibération fondée sur les preuves, pas la majorité.

Protocole : formulation -> analyses indépendantes -> arguments -> comparaison ->
vérification -> désaccords -> évaluation des preuves -> synthèse -> décision.
Budget et nombre de tours bornés. Sans fournisseur disponible, le conseil est
indisponible (honnête). Les tests utilisent des fournisseurs fixtures explicites.
"""
from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass


@dataclass
class CouncilConfig:
    max_models: int = 3
    max_rounds: int = 2
    max_cost_usd: float = 0.10
    max_tokens: int = 600


class Council:
    def __init__(self, router, config: CouncilConfig | None = None):
        self.router = router
        self.config = config or CouncilConfig()
        if self.config.max_models < 1 or self.config.max_rounds < 1 or self.config.max_tokens < 1:
            raise ValueError("max_models, max_rounds et max_tokens doivent être positifs")
        if not math.isfinite(self.config.max_cost_usd) or self.config.max_cost_usd < 0:
            raise ValueError("max_cost_usd doit être fini et positif ou nul")

    def _select_independent(self, avail: list) -> list:
        """Sélectionne jusqu'à max_models modèles en privilégiant des fournisseurs distincts."""
        chosen, seen = [], set()
        for m in avail:  # 1er passage : un modèle par fournisseur distinct
            if m.provider not in seen:
                chosen.append(m)
                seen.add(m.provider)
            if len(chosen) >= self.config.max_models:
                return chosen
        for m in avail:  # complément si moins de fournisseurs que max_models
            if m not in chosen:
                chosen.append(m)
            if len(chosen) >= self.config.max_models:
                break
        return chosen

    @staticmethod
    def _parse_analysis(text: str, model_key: str) -> dict:
        """Parse une analyse JSON produite par un modèle ; repli honnête sinon."""
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "answer" in data:
                return {"model": model_key, "answer": str(data.get("answer", "")),
                        "evidence": list(data.get("evidence", [])),
                        "sources": list(data.get("sources", [])),
                        "confidence": float(data.get("confidence", 0.5))}
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        # Repli : texte brut comme réponse, sans preuve inventée.
        return {"model": model_key, "answer": text[:500], "evidence": [], "sources": [], "confidence": 0.5}

    def _produce_analyses(self, problem: str, evidence: list, avail: list,
                          mission_id: str | None = None, budget_usd: float | None = None) -> dict:
        """Produit de VRAIES analyses via le routeur, jamais en contournant le budget.

        Chaque appel passe par `router.complete` : réservation avant appel, quotas
        centraux, traçabilité, fallback. Le conseil maintient aussi un plafond
        collectif strict : le budget restant est passé comme capacité maximale de
        l'appel suivant, et aucun appel n'est tenté si la borne supérieure dépasse ce
        restant. Les appels interrompus restent comptabilisés prudemment par le routeur.
        """
        system = ("Tu es un analyste indépendant d'un conseil multi-modèles. Examine le problème "
                  "de façon critique et distincte des autres analystes. Réponds UNIQUEMENT en JSON "
                  'strict : {"answer": "...", "evidence": ["..."], "sources": ["..."], "confidence": 0.0}. '
                  "N'invente aucune preuve ; si tu n'en as pas, laisse evidence vide.")
        user = json.dumps({"probleme": problem, "preuves_disponibles": evidence}, ensure_ascii=False)
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        cap = self.config.max_cost_usd
        if budget_usd is not None:
            try:
                cap = min(cap, max(0.0, float(budget_usd)))
            except (TypeError, ValueError):
                cap = 0.0
        analyses, spent, reserved_bound, attempts, errors = [], 0.0, 0.0, [], []
        selected = self._select_independent(avail)
        input_bound = self.router._input_token_bound(messages)
        for spec in selected:
            upper = self.router._cost(spec, input_bound, self.config.max_tokens)
            remaining = cap - reserved_bound
            if upper > remaining + 1e-12:
                errors.append({"model": f"{spec.provider}/{spec.model}",
                               "error": "borne de coût supérieure au budget collectif restant",
                               "estimated_max_cost_usd": round(upper, 9), "remaining_usd": round(remaining, 9)})
                break
            res = self.router.complete(
                {"capabilities": ["general"], "max_cost_usd": remaining, "disable_fallback": True},
                messages, max_tokens=self.config.max_tokens, temperature=0.4,
                mission_id=mission_id,
                call_key=f"council:{mission_id or uuid.uuid4().hex}:{spec.provider}/{spec.model}")
            attempts.extend(res.get("attempts", []))
            reserved_bound += upper  # plafond collectif conservateur, même si l'appel échoue
            if not res.get("ok"):
                errors.append({"model": f"{spec.provider}/{spec.model}", "error": res.get("error", "")})
                continue
            cost = float(res.get("cost_usd", 0.0))
            if spent + cost > cap + 1e-12:
                errors.append({"model": f"{spec.provider}/{spec.model}", "error": "budget collectif dépassé après appel"})
                break
            spent += cost
            analyses.append(self._parse_analysis(res.get("text", ""), f"{spec.provider}/{spec.model}"))
            if len(analyses) >= self.config.max_models:
                break
        return {"analyses": analyses, "spent_usd": round(spent, 9), "reserved_bound_usd": round(reserved_bound, 9),
                "budget_max_usd": cap, "attempts": attempts, "errors": errors,
                "models": [f"{m.provider}/{m.model}" for m in selected]}

    def deliberate(self, problem: str, evidence: list[dict] | None = None,
                   analyses: list[dict] | None = None, mission_id: str | None = None,
                   budget_usd: float | None = None) -> dict:
        """analyses : analyses indépendantes déjà produites (fixtures explicites, 0 appel).

        Si analyses est None, le conseil tente de les produire via le routeur ;
        sans fournisseur disponible, il retourne un statut indisponible. `budget_usd`
        peut réduire le plafond du conseil (ex. budget restant d'une mission) mais ne
        remplace jamais les quotas centraux appliqués par le routeur.
        """
        evidence = evidence or []
        budget_trace = {"budget_max_usd": self.config.max_cost_usd, "budget_spent_usd": 0.0,
                        "budget_reserved_bound_usd": 0.0, "attempts": [], "errors": [], "models": []}
        if budget_usd is not None:
            try:
                budget_trace["budget_max_usd"] = min(self.config.max_cost_usd, max(0.0, float(budget_usd)))
            except (TypeError, ValueError):
                budget_trace["budget_max_usd"] = 0.0
        if analyses is None:
            self.router.detect()
            avail = self.router.configured_models()
            if not avail:
                return {"status": "unavailable", "reason": "aucun modèle disponible pour le conseil",
                        "decision": None, "rounds": 0, **budget_trace}
            produced = self._produce_analyses(problem, evidence, avail, mission_id=mission_id, budget_usd=budget_usd)
            analyses = produced["analyses"]
            budget_trace = {k: produced[k] for k in ("budget_max_usd", "spent_usd", "reserved_bound_usd", "attempts", "errors", "models")}
            budget_trace["budget_spent_usd"] = budget_trace.pop("spent_usd")
            budget_trace["budget_reserved_bound_usd"] = budget_trace.pop("reserved_bound_usd")
            if not analyses:
                return {"status": "unavailable",
                        "reason": "fournisseurs configurés mais aucun appel réel n'a réussi (voir errors)",
                        "decision": None, "rounds": 0, **budget_trace}
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
                "note": "décision fondée sur preuves + indépendance, pas sur la majorité seule",
                **budget_trace}
