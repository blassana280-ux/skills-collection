"""CLI OMNIBRAIN SUPREME 1000.

Usage : python3 -m supreme <commande>
  catalog [--check]      génère/vérifie le catalogue 1000 agents
  sync                   synchronise le registre SQLite
  evaluate [--activate]  évalue les profils, active sur preuve
  status                 état du système
  mission "objectif"     soumet et exécute une mission réelle
  serve [--port N]       démarre l'API + tableau de bord
  backup                 sauvegarde la base
  report                 rapport global
"""
from __future__ import annotations

import argparse
import json
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(prog="supreme")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("catalog").add_argument("--check", action="store_true")
    sub.add_parser("sync")
    ev = sub.add_parser("evaluate"); ev.add_argument("--activate", action="store_true")
    sub.add_parser("status")
    m = sub.add_parser("mission"); m.add_argument("objective"); m.add_argument("--no-run", action="store_true")
    sv = sub.add_parser("serve"); sv.add_argument("--port", type=int, default=8765); sv.add_argument("--host", default="0.0.0.0")
    sub.add_parser("backup")
    sub.add_parser("report")
    args = ap.parse_args(argv)

    if args.cmd == "catalog":
        from .catalog import generate, write_catalog
        if args.check:
            _, _, errors = generate()
            if errors:
                print("\n".join(errors)); return 1
            print("OK — 1000 spécialistes + 20 chefs, profils complets, aucun doublon"); return 0
        n, errors = write_catalog()
        if errors:
            print("\n".join(errors)); return 1
        print(f"Catalogue écrit : {n} profils"); return 0

    from .api import bootstrap
    from .evaluation import EvaluationEngine
    from .observability import ObservabilityEngine
    from .reporting import ReportingEngine
    from .backup import BackupManager

    core = bootstrap(evaluate=False)
    if args.cmd == "sync":
        print(json.dumps(core.registry.sync_catalog(), ensure_ascii=False)); return 0
    if args.cmd == "evaluate":
        counts = EvaluationEngine(core.conn, core.registry).evaluate_all(activate=args.activate)
        print(json.dumps(counts, ensure_ascii=False)); return 0
    if args.cmd == "status":
        obs = ObservabilityEngine(core.conn, core.registry, core.budget, core.router)
        print(json.dumps(obs.system_status(), ensure_ascii=False, indent=1)); return 0
    if args.cmd == "mission":
        sub = core.submit({"objective": args.objective})
        if args.no_run:
            print(json.dumps({"mission_id": sub["mission_id"]}, ensure_ascii=False)); return 0
        print(json.dumps(core.run(sub["mission_id"]), ensure_ascii=False, indent=1)); return 0
    if args.cmd == "backup":
        print(json.dumps(BackupManager().backup("cli"), ensure_ascii=False, indent=1)); return 0
    if args.cmd == "report":
        obs = ObservabilityEngine(core.conn, core.registry, core.budget, core.router)
        rep = ReportingEngine(core.conn, core.registry, obs).global_report()
        print(json.dumps(rep, ensure_ascii=False, indent=1)); return 0
    if args.cmd == "serve":
        from .api import serve
        server, state = serve(args.host, args.port, evaluate=True)
        print(f"API + dashboard sur http://{args.host}:{args.port}")
        print(f"Jeton admin : {state.admin_token}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
