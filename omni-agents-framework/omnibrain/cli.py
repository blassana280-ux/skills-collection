"""CLI omnibrain — zéro dépendance, pur argparse.

Sous-commandes :
    classify   classer une demande
    route      afficher l'escouade routée
    plan       plan d'orchestration complet (Markdown ou JSON)
    list       lister les agents du registre
    validate   valider agents, matrice et contrats
    gates      évaluer les 4 gates sur un livrable
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .classifier import Classifier
from .config import find_repo_root, load_matrix
from .dispatcher import Dispatcher
from .gates import GateEngine
from .registry import Registry
from .report import render_json, render_markdown
from .router import Router


def _read_task(path: str | None) -> str:
    if path is None or path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _task_from_args(args: argparse.Namespace) -> str:
    """Texte direct, fichier, ou '-' pour stdin."""
    text = getattr(args, "text", None)
    if text and text != "-":
        return text
    return _read_task(getattr(args, "file", None))


def _build_dispatcher() -> Dispatcher:
    root = find_repo_root()
    return Dispatcher(root=root, matrix=load_matrix(root))


def cmd_classify(args: argparse.Namespace) -> int:
    dispatcher = _build_dispatcher()
    task = _task_from_args(args)
    result = dispatcher.classifier.classify(task)
    if args.json:
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"niveau={result.level} score={result.score} escouade={result.squad_size}")
        for signal in result.signals:
            print(f"  - {signal.label} (+{signal.weight}) {signal.evidence}")
    return 0


def cmd_route(args: argparse.Namespace) -> int:
    dispatcher = _build_dispatcher()
    task = _task_from_args(args)
    classification = dispatcher.classifier.classify(task)
    decision = dispatcher.router.route(task, classification)
    payload = {
        "level": classification.level,
        "squad": [a.as_dict() for a in decision.agents],
        "scores": decision.scores,
        "contracts": [c.artifact for c in decision.contracts],
        "reasons": decision.reasons,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Escouade ({classification.level}) :")
        for agent in decision.agents:
            print(f"  {agent.emoji} {agent.id:<22} {agent.name}")
        if decision.contracts:
            print("Contrats :", ", ".join(c.artifact for c in decision.contracts))
        for reason in decision.reasons:
            print(f"  -> {reason}")
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    dispatcher = _build_dispatcher()
    task = _read_task(args.file)
    plan = dispatcher.plan(task)
    output = render_json(plan) if args.format == "json" else render_markdown(plan)
    if args.out:
        Path(args.out).write_text(output + "\n", encoding="utf-8")
        print(f"plan écrit dans {args.out}")
    else:
        print(output)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    root = find_repo_root()
    registry = Registry(root=root, matrix=load_matrix(root))
    for agent in registry.agents():
        if args.squad and agent.squad != args.squad:
            continue
        role = "orchestrateur" if agent.orchestrator else "agent"
        risk = " [RISQUE]" if agent.risk else ""
        print(f"{agent.emoji} {agent.id:<24} {role:<14} [{agent.squad}] {', '.join(agent.domains)}{risk}")
        if not args.terse and agent.description:
            print(f"    {agent.description[:110]}")
    return 0


def cmd_squads(_args: argparse.Namespace) -> int:
    root = find_repo_root()
    registry = Registry(root=root, matrix=load_matrix(root))
    summary: dict[str, dict[str, int]] = {}
    for agent in registry.agents():
        bucket = summary.setdefault(agent.squad, {"agents": 0, "risk": 0})
        bucket["agents"] += 1
        if agent.risk:
            bucket["risk"] += 1
    print(f"{'ESCOUADE':<24} {'AGENTS':>7} {'À RISQUE':>9}")
    for squad in sorted(summary):
        print(f"{squad:<24} {summary[squad]['agents']:>7} {summary[squad]['risk']:>9}")
    print(f"{'TOTAL':<24} {len(registry.agents()):>7}")
    return 0


def cmd_validate(_args: argparse.Namespace) -> int:
    root = find_repo_root()
    registry = Registry(root=root, matrix=load_matrix(root))
    errors = registry.validate()
    if errors:
        for error in errors:
            print(f"ERREUR : {error}", file=sys.stderr)
        print(f"\n{len(errors)} anomalie(s) — réseau INVALIDE", file=sys.stderr)
        return 1
    print(f"OK — {len(registry.agents())} agents et {len(registry.contracts())} contrats validés")
    return 0


def cmd_gates(args: argparse.Namespace) -> int:
    deliverable = Path(args.file).read_text(encoding="utf-8")
    expected = [item.strip() for item in args.expect.split(",")] if args.expect else []
    report = GateEngine().evaluate(deliverable, expected)
    if args.json:
        print(json.dumps(
            {"verdict": report.verdict, "results": [g.__dict__ for g in report.results]},
            ensure_ascii=False, indent=2,
        ))
    else:
        for gate in report.results:
            print(f"[{gate.status}] {gate.gate}")
            for evidence in gate.evidence:
                print(f"    - {evidence}")
        print(f"\nVerdict global : {report.verdict}")
    return 0 if report.passed else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="omnibrain", description="Orchestrateur multi-agents OmniBrain")
    parser.add_argument("--version", action="version", version=f"omnibrain {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_classify = sub.add_parser("classify", help="classer une demande")
    p_classify.add_argument("text", nargs="?")
    p_classify.add_argument("--file", "-f")
    p_classify.add_argument("--json", action="store_true")
    p_classify.set_defaults(func=cmd_classify)

    p_route = sub.add_parser("route", help="router vers l'escouade")
    p_route.add_argument("text", nargs="?")
    p_route.add_argument("--file", "-f")
    p_route.add_argument("--json", action="store_true")
    p_route.set_defaults(func=cmd_route)

    p_plan = sub.add_parser("plan", help="générer le plan d'orchestration complet")
    p_plan.add_argument("file", nargs="?", default="-", help="fichier Markdown de la demande ('-' pour stdin)")
    p_plan.add_argument("--format", choices=["md", "json"], default="md")
    p_plan.add_argument("--out", "-o")
    p_plan.set_defaults(func=cmd_plan)

    p_list = sub.add_parser("list", help="lister les agents enregistrés")
    p_list.add_argument("--squad", help="filtrer par escouade")
    p_list.add_argument("--terse", action="store_true", help="une ligne par agent (sans description)")
    p_list.set_defaults(func=cmd_list)

    p_squads = sub.add_parser("squads", help="afficher le bilan par escouade")
    p_squads.set_defaults(func=cmd_squads)

    p_validate = sub.add_parser("validate", help="valider le réseau (agents, matrice, contrats)")
    p_validate.set_defaults(func=cmd_validate)

    p_gates = sub.add_parser("gates", help="évaluer les gates qualité d'un livrable")
    p_gates.add_argument("file")
    p_gates.add_argument("--expect", help="ids d'agents attendus, séparés par des virgules")
    p_gates.add_argument("--json", action="store_true")
    p_gates.set_defaults(func=cmd_gates)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        parser.exit(1, f"erreur : {exc}\n")
    except BrokenPipeError:
        # Sortie redirigée vers un outil (head, grep...) qui ferme le flux.
        try:
            sys.stdout.close()
        except BrokenPipeError:
            pass
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
