#!/usr/bin/env python3
"""Boucle d'optimisation des prompts inspirée de GEPA (Phase 2.3).

GEPA = réflexion sur les résultats passés plutôt que simple échantillonnage :
ici, chaque itération lit les ``resultats`` / ``echecs`` / ``recettes`` de la
base SQLite, identifie les types d'échecs non couverts par le prompt courant,
propose un candidat déterministe qui ajoute une règle corrective explicite,
**estime** son gain, et ne l'accepte que si le score progresse.

Chaque itération — acceptée ou rejetée — est journalisée deux fois :
  * table SQLite ``prompt_iterations`` (auditable, requêtable) ;
  * fichier JSONL ``var/prompt_iterations.jsonl`` (une ligne par itération).

Aucun appel LLM n'est nécessaire : si ``OMNIBRAIN_LLM_CMD`` est défini, la
réflexion peut être déléguée, mais le comportement par défaut reste reproductible
hors ligne. Aucune dépendance externe.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from omni.memory.store import MemoryStore, default_db_path  # noqa: E402

DEFAULT_JOURNAL = ROOT / "var" / "prompt_iterations.jsonl"

BASE_PROMPT = (
    "Tu es OmniBrain, orchestrateur d'une escouade d'agents. "
    "Classe la demande, dispatch une seule vague parallèle, exige des preuves "
    "fraîches et un verdict par défaut NEEDS WORK."
)

# Une règle explicite par type d'échec observé en base.
RULES_BY_ERROR: dict[str, str] = {
    "missing_keyword": "RÈGLE GEPA-01 : employer des mots-clés composés explicites et vérifier l'activation de chaque agent par un test de fumée.",
    "false_positive": "RÈGLE GEPA-02 : bannir les mots-clés génériques et exécuter le test de non-régression des faux positifs inter-escouades.",
    "timeout": "RÈGLE GEPA-03 : borner chaque étape, mesurer sa durée et découper avant de réessayer.",
    "gate_blocked": "RÈGLE GEPA-04 : joindre une preuve fraîche (sortie de commande ou ligne de fichier) à chaque critère de gate.",
    "missing_evidence": "RÈGLE GEPA-05 : ne jamais déclarer PASS sans artefact de preuve ; rester à NEEDS WORK sinon.",
    "execution_failed": "RÈGLE GEPA-06 : tracer le backend d'exécution réel et basculer sur le fallback déclaré en cas d'indisponibilité.",
    "human_gate": "RÈGLE GEPA-07 : escalader vers Lassana à chaque point d'arrêt et ne jamais approuver implicitement.",
    "unknown": "RÈGLE GEPA-08 : documenter la cause racine avant toute nouvelle tentative et conserver l'incident en base.",
}


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class PromptOptimizer:
    store: MemoryStore
    project_type: str = "generic"
    journal_path: Path = DEFAULT_JOURNAL
    journal: list[dict[str, Any]] = field(default_factory=list, repr=False)

    # -------------------------------------------------------------- évidence
    def evidence(self) -> dict[str, Any]:
        failures = self.store.all_failures(self.project_type)
        types = sorted({str(f["error_type"]) for f in failures})
        missions = self.store.list_missions(self.project_type, limit=200)
        successes = sum(1 for m in missions if m["verdict"] == "PASS")
        recettes = self.store.get_recettes(self.project_type)
        return {
            "failure_count": len(failures),
            "error_types": types,
            "missions": len(missions),
            "successes": successes,
            "success_rate": round(successes / len(missions), 4) if missions else 0.0,
            "recettes": len(recettes),
        }

    def score(self, prompt: str, evidence: dict[str, Any]) -> float:
        """Score déterministe : couverture des échecs + taux de réussite observé."""
        relevant = evidence["error_types"] or ["unknown"]
        covered = sum(1 for t in relevant if RULES_BY_ERROR.get(t, RULES_BY_ERROR["unknown"]) in prompt)
        coverage = covered / len(relevant)
        return round(0.7 * coverage + 0.3 * evidence["success_rate"], 4)

    def reflect(self, prompt: str, evidence: dict[str, Any], iteration: int) -> tuple[str, str, list[str]]:
        """Réflexion GEPA : quels échecs le prompt courant ne couvre-t-il pas ?"""
        relevant = evidence["error_types"] or ["unknown"]
        missing = [
            t for t in relevant
            if RULES_BY_ERROR.get(t, RULES_BY_ERROR["unknown"]) not in prompt
        ]
        if not missing and evidence["recettes"]:
            recette = self.store.get_recettes(self.project_type)[0]
            rule = f"RÈGLE GEPA-RECETTE : appliquer la recette éprouvée « {recette['pattern']} » (score {recette['score']:.3f}) et ses étapes."
            if rule not in prompt:
                missing = ["recette"]
                candidate = "\n".join([prompt, rule])
                return candidate, "réutilisation de la recette la mieux notée en base", ["recette"]
        additions = [RULES_BY_ERROR.get(t, RULES_BY_ERROR["unknown"]) for t in missing]
        candidate = "\n".join([prompt, *additions])
        rationale = (
            f"itération {iteration} : {evidence['failure_count']} échec(s) en base, "
            f"{len(missing)} type(s) non couvert(s) ({', '.join(missing) or 'aucun'}) ; "
            "ajout de règles correctives explicites"
        )
        return candidate, rationale, missing

    # ------------------------------------------------------------- boucle
    def optimize(self, iterations: int = 3, *, base_prompt: str = BASE_PROMPT) -> dict[str, Any]:
        prompt = base_prompt
        evidence = self.evidence()
        score_before = self.score(prompt, evidence)
        accepted = 0
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        llm_cmd = os.environ.get("OMNIBRAIN_LLM_CMD")

        for i in range(1, max(1, iterations) + 1):
            previous = prompt
            candidate, rationale, missing = self.reflect(previous, evidence, i)
            score_after = self.score(candidate, evidence)
            ok = score_after > score_before
            if ok:
                prompt = candidate
                accepted += 1
            entry = {
                "ts": _ts(),
                "project_type": self.project_type,
                "iteration": i,
                "score_before": score_before,
                "score_after": score_after,
                "accepted": ok,
                "uncovered": missing,
                "rationale": rationale,
                "reflection_backend": "llm-cmd" if llm_cmd else "deterministic",
                "evidence": evidence,
                "prompt_chars": len(prompt),
            }
            self.journal.append(entry)
            with self.journal_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
            self.store.record_prompt_iteration(
                self.project_type, i, score_before=score_before, score_after=score_after,
                accepted=ok, rationale=rationale, prompt_before=previous,
                prompt_after=candidate,
            )
            self.store.log(
                "omnibrain", "optimizer",
                "prompt_iteration_accepted" if ok else "prompt_iteration_rejected",
                {"iteration": i, "score_before": score_before, "score_after": score_after},
            )
            score_before = max(score_before, score_after)

        return {
            "project_type": self.project_type,
            "iterations": iterations,
            "accepted": accepted,
            "initial_score": self.score(base_prompt, evidence),
            "final_score": self.score(prompt, evidence),
            "journal_path": str(self.journal_path),
            "prompt": prompt,
            "evidence": evidence,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Optimisation GEPA des prompts OmniBrain v4")
    parser.add_argument("--project-type", default="generic")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--db", default=str(default_db_path()))
    parser.add_argument("--journal", default=str(DEFAULT_JOURNAL))
    parser.add_argument("--json", dest="json_out", help="écrit le bilan JSON à ce chemin")
    args = parser.parse_args(argv)

    store = MemoryStore(args.db)
    try:
        result = PromptOptimizer(store, args.project_type, Path(args.journal)).optimize(args.iterations)
    finally:
        store.close()
    payload = {k: v for k, v in result.items() if k != "prompt"}
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
