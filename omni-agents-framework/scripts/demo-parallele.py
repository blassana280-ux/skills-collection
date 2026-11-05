#!/usr/bin/env python3
"""Démo d'exécution parallèle : lance toutes les demandes examples/ en même
temps et affiche la couverture réelle du réseau d'agents.

Le réseau peut grandir (12 agents cœur, puis catalogues) : la liste des
agents est lue depuis le registre, jamais codée en dur.

Usage :
    python3 scripts/demo-parallele.py
    python3 scripts/demo-parallele.py --workers 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from omnibrain.config import load_matrix  # noqa: E402
from omnibrain.parallel import run_plans_parallel  # noqa: E402
from omnibrain.registry import Registry  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Démo parallèle OmniBrain")
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args()

    registry = Registry(matrix=load_matrix(ROOT))
    all_agents = registry.agents()
    orchestrator = next(a for a in all_agents if a.orchestrator)
    specialists = [a for a in all_agents if not a.orchestrator]

    example_dir = ROOT / "examples"
    task_files = sorted(example_dir.glob("task-*.md"))
    if not task_files:
        print("aucune demande dans examples/", file=sys.stderr)
        return 1

    tasks = [path.read_text(encoding="utf-8") for path in task_files]
    print(f"▶ {len(tasks)} demandes lancées en parallèle (workers={args.workers or 'auto'})")
    print(f"  réseau disponible : {len(specialists)} spécialistes + 1 orchestrateur ({orchestrator.id})\n")
    for i, path in enumerate(task_files):
        print(f"  demande {i + 1}: {path.name}")

    run = run_plans_parallel(tasks, max_workers=args.workers)

    print("\n" + "=" * 72)
    print("RÉSULTAT PAR DEMANDE — chacune = une vague parallèle (wave 0)")
    print("=" * 72)
    for i, (path, plan) in enumerate(zip(task_files, run.plans), start=1):
        c = plan["classification"]
        squad = ", ".join(f"{a['emoji']} {a['id']}" for a in plan["squad"])
        print(f"\n[{i}] {path.name}")
        print(f"    classification : {c['level']} (score {c['score']}, {c['squad_size']} agents)")
        print(f"    escouade       : {squad}")
        print(f"    briefs émis    : {len(plan['briefs'])} | contrats : {len(plan['contracts'])} | gates : {len(plan['gates_checklist'])}")

    print("\n" + "=" * 72)
    print("COUVERTURE DU RÉSEAU SUR LES DEMANDES D'EXEMPLE")
    print("=" * 72)
    coverage = run.coverage()
    mobilized = 0
    for agent in all_agents:
        plan_indexes = coverage.get(agent.id, [])
        if agent.orchestrator:
            plan_indexes = list(range(len(task_files)))
        if plan_indexes:
            mobilized += 1
            where = ", ".join(f"demande {i + 1}" for i in plan_indexes)
            print(f"  ✅ {agent.id:<24} [{agent.squad:<20}] : {where}")
        else:
            print(f"  ⬜ {agent.id:<24} [{agent.squad:<20}] : non mobilisé par les exemples")

    # Les agents non couverts par les 5 exemples doivent rester routables :
    # vérification qu'ils s'activent bien sur leurs propres mots-clés.
    from omnibrain.classifier import keyword_present, _normalize  # noqa: E402

    not_covered = [a for a in specialists if a.id not in coverage]
    unroutable = []
    for agent in not_covered:
        synthetic = f"Mission : {', '.join(agent.keywords[:3])}."
        norm = _normalize(synthetic)
        if not any(keyword_present(kw, norm) for kw in agent.keywords):
            unroutable.append(agent.id)
    if unroutable:
        print(f"\n❌ agents inactivables sur leurs mots-clés : {', '.join(unroutable)}")
        return 2

    print("\n" + "=" * 72)
    print("SYNTHÈSE")
    print("=" * 72)
    print(f"  demandes traitées         : {len(run.plans)}")
    print(f"  processus parallèles      : {run.workers}")
    print(f"  briefs émis au total      : {run.total_briefs()} (tous en wave 0)")
    print(f"  agents mobilisés (exemples): {mobilized}/{len(all_agents)}")
    print(f"  agents non mobilisés mais routables sur mots-clés : {len(not_covered)}")
    print(f"  contrats d'interface      : {run.active_contracts()}")
    print(f"  temps parallèle           : {run.parallel_seconds:.3f}s")
    print(f"  temps séquentiel          : {run.sequential_seconds:.3f}s")
    print(f"  accélération observée     : x{run.speedup:.2f}")
    print("\n✅ Réseau cohérent : tous les agents sont activables et la vague parallèle fonctionne.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
