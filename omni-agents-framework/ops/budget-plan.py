#!/usr/bin/env python3
"""Plan de budget d'activation — calcul réel, AUCUN prix inventé.

Les prix doivent être relevés par l'humain sur la page officielle du fournisseur,
puis attestés via `providers --set-prices`. Cet outil ne fait qu'arithmétique :
il ne contacte aucun fournisseur et ne déclenche aucune inférence.

    python3 ops/budget-plan.py --input-per-million 0.10 --output-per-million 0.30
    python3 ops/budget-plan.py --from-attested mistral --model mistral-small-latest

Sortie : coût estimé par agent, par palier, et marge de sécurité conseillée.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MILESTONES = [5, 20, 60, 100, 200, 400, 600, 800, 960]


def per_call_usd(input_per_million: float, output_per_million: float,
                 input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000.0) * input_per_million + \
           (output_tokens / 1_000_000.0) * output_per_million


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-per-million", type=float, help="USD par million de jetons d'entrée (prix officiel)")
    ap.add_argument("--output-per-million", type=float, help="USD par million de jetons de sortie (prix officiel)")
    ap.add_argument("--from-attested", metavar="PROVIDER", help="lit les prix déjà attestés en base")
    ap.add_argument("--model", default="", help="modèle découvert (requis avec --from-attested)")
    ap.add_argument("--input-tokens", type=int, default=1200,
                    help="jetons d'entrée estimés par appel d'activation (défaut 1200)")
    ap.add_argument("--output-tokens", type=int, default=512,
                    help="jetons de sortie max par appel (défaut 512, plafond du probe)")
    ap.add_argument("--safety-margin", type=float, default=1.5,
                    help="marge multiplicatrice conseillée (défaut 1.5)")
    args = ap.parse_args()

    source = "argument humain (à attester)"
    if args.from_attested:
        from supreme.db import get_conn
        conn = get_conn()
        row = conn.execute("SELECT pricing_json FROM provider_controls WHERE provider=?",
                           (args.from_attested,)).fetchone()
        prices = json.loads((row["pricing_json"] if row else None) or "{}")
        entry = prices.get(args.model)
        if not entry:
            print(json.dumps({"error": "aucun prix attesté pour ce modèle",
                              "provider": args.from_attested, "model": args.model,
                              "modeles_tarifes": sorted(prices),
                              "action": "relever les prix officiels puis providers --set-prices"},
                             ensure_ascii=False, indent=1))
            return 1
        in_pm = float(entry["input_usd_per_million"])
        out_pm = float(entry["output_usd_per_million"])
        source = f"attesté : {entry.get('source_url')} ({entry.get('checked_at')})"
    else:
        if args.input_per_million is None or args.output_per_million is None:
            print(json.dumps({"error": "fournir --input-per-million et --output-per-million, "
                                       "ou --from-attested PROVIDER --model MODELE",
                              "note": "aucun prix par défaut : cet outil n'invente aucun tarif"},
                             ensure_ascii=False, indent=1))
            return 2
        in_pm, out_pm = args.input_per_million, args.output_per_million

    for value in (in_pm, out_pm, args.safety_margin):
        if not math.isfinite(value) or value < 0:
            print(json.dumps({"error": "valeurs finies et positives requises"}, ensure_ascii=False))
            return 2

    unit = per_call_usd(in_pm, out_pm, args.input_tokens, args.output_tokens)
    tiers = []
    previous = 0
    for target in MILESTONES:
        new_agents = target - previous
        raw = unit * new_agents
        tiers.append({"palier_cumulatif": target, "nouveaux_agents": new_agents,
                      "cout_estime_usd": round(raw, 6),
                      "budget_conseille_usd": round(raw * args.safety_margin, 6),
                      "per_agent_usd_conseille": round(unit * args.safety_margin, 6) or 0.000001})
        previous = target

    print(json.dumps({
        "source_des_prix": source,
        "prix_usd_par_million": {"entree": in_pm, "sortie": out_pm},
        "hypotheses_par_appel": {"jetons_entree": args.input_tokens, "jetons_sortie_max": args.output_tokens},
        "cout_estime_par_agent_usd": round(unit, 8),
        "marge_de_securite": args.safety_margin,
        "paliers": tiers,
        "cout_total_960_usd": round(unit * 960, 6),
        "avertissements": [
            "estimation arithmétique, pas un devis : la consommation réelle dépend du modèle et du prompt",
            "le coût réel facturé est enregistré dans budget_ledger après chaque appel",
            "aucune inférence n'est déclenchée par cet outil",
            "une autorisation humaine bornée reste obligatoire avant tout appel payant",
        ],
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
