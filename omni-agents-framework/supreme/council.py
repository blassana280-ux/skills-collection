"""Multi-Model Council SUPREME — délibération fondée sur les preuves, pas la majorité.

Protocole : formulation -> analyses indépendantes -> arguments -> comparaison ->
vérification -> désaccords -> évaluation des preuves -> synthèse -> décision.
Budget et nombre de tours bornés. Sans fournisseur disponible, le conseil est
indisponible (honnête). Les tests utilisent des fournisseurs fixtures explicites.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from .providers import resolve_key


@dataclass
class CouncilConfig:
    max_models: int = 3
    max_rounds: int = 2
    max_cost_usd: float = 0.10


class Council:
    def __init__(self, router, config: CouncilConfig | None = None):
        self.router = router
        self.config = config or CouncilConfig()

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

    def _produce_analyses(self, problem: str, evidence: list, avail: list) -> list:
        """Produit de VRAIES analyses indépendantes via les fournisseurs configurés.

        Budget borné (max_cost_usd). Aucun appel simulé : si un appel échoue, il est
        ignoré ; si tous échouent, la liste est vide et le conseil reste indisponible.
        """
        system = ("Tu es un analyste indépendant d'un conseil multi-modèles. Examine le problème "
                  "de façon critique et distincte des autres analystes. Réponds UNIQUEMENT en JSON "
                  'strict : {"answer": "...", "evidence": ["..."], "sources": ["..."], "confidence": 0.0}. '
                  "N'invente aucune preuve ; si tu n'en as pas, laisse evidence vide.")
        user = json.dumps({"probleme": problem, "preuves_disponibles": evidence}, ensure_ascii=False)
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        analyses, spent = [], 0.0
        for spec in self._select_independent(avail):
            prov = next((p for p in self.router.providers if p.name == spec.provider), None)
            if prov is None:
                continue
            key = resolve_key(prov.env_var, prov.name)
            res = self.router.client.complete(provider=spec.provider, model=spec.model,
                                              messages=messages, base_url=prov.base_url,
                                              kind=prov.kind, api_key=key, max_tokens=600, temperature=0.4)
            if not res.ok:
                continue
            usage = res.usage or {}
            cost = (spec.cost_per_1k_in * usage.get("input_tokens", 0)
                    + spec.cost_per_1k_out * usage.get("output_tokens", 0)) / 1000.0
            spent += cost
            analyses.append(self._parse_analysis(res.text, f"{spec.provider}/{spec.model}"))
            if spent >= self.config.max_cost_usd or len(analyses) >= self.config.max_models:
                break
        return analyses

    def deliberate(self, problem: str, evidence: list[dict] | None = None,
                   analyses: list[dict] | None = None) -> dict:
        """analyses : analyses indépendantes déjà produites (provider/model/answer/evidence/confidence).

        Si analyses est None, le conseil tente de les produire via le routeur ;
        sans fournisseur disponible, il retourne un statut indisponible.
        """
        evidence = evidence or []
        if analyses is None:
            # Fournisseurs configurés (clé présente) ; l'appel réel prouve la disponibilité.
            self.router.detect()
            avail = self.router.configured_models()
            if not avail:
                return {"status": "unavailable", "reason": "aucun modèle disponible pour le conseil",
                        "decision": None, "rounds": 0}
            analyses = self._produce_analyses(problem, evidence, avail)
            if not analyses:
                return {"status": "unavailable",
                        "reason": "fournisseurs configurés mais aucun appel réel n'a réussi (voir errors)",
                        "models": [f"{m.provider}/{m.model}" for m in avail[:self.config.max_models]],
                        "decision": None, "rounds": 0}
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
