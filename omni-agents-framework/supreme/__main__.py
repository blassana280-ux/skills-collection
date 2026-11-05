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
  rotate-token           régénère le jeton API (0600, jamais affiché) ; redémarrer serve ensuite
  providers [--check]    statut des fournisseurs IA (sans clés) ; --check = appel réel de disponibilité
  providers --init-secrets  crée un modèle de fichier de secrets vide (0600, gitignoré)
  worker [--once]        processus worker séparé, bail/heartbeat/fencing, arrêt propre (SIGINT/SIGTERM)
  audit                  audit exécutable : catalogue, sécurité, sauvegardes, KPIs, tests (Phase I)
  learn [--periodic]     apprentissage ponctuel ou périodique configurable, rapports persistés,
                         bail unique, arrêt propre, reprise après interruption ; --status pour inspecter
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import threading


def _stop_event_with_signals() -> threading.Event:
    stop = threading.Event()
    def _handle(signum, frame):
        stop.set()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle)
        except (ValueError, OSError):
            pass
    return stop


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
    sub.add_parser("rotate-token")
    pv = sub.add_parser("providers")
    pv.add_argument("--check", action="store_true")
    pv.add_argument("--init-secrets", action="store_true")
    wk = sub.add_parser("worker")
    wk.add_argument("--once", action="store_true")
    wk.add_argument("--interval", type=float, default=1.0)
    wk.add_argument("--max", type=int, default=None)
    wk.add_argument("--max-polls", type=int, default=None)
    wk.add_argument("--worker-id", default=None)
    wk.add_argument("--lease-seconds", type=float, default=30.0)
    wk.add_argument("--heartbeat-seconds", type=float, default=None)
    ad = sub.add_parser("audit")
    ad.add_argument("--no-save", action="store_true")
    ln = sub.add_parser("learn")
    ln.add_argument("--periodic", action="store_true")
    ln.add_argument("--interval", type=float, default=300.0)
    ln.add_argument("--max-cycles", type=int, default=None)
    ln.add_argument("--max-proposals", type=int, default=5)
    ln.add_argument("--scheduler-id", default="default")
    ln.add_argument("--lease-seconds", type=float, default=30.0)
    ln.add_argument("--heartbeat-seconds", type=float, default=None)
    ln.add_argument("--status", action="store_true")
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

    if args.cmd == "rotate-token":
        from .api import rotate_token
        meta = rotate_token()
        # N'affiche jamais le jeton : uniquement des métadonnées non sensibles.
        print(json.dumps({k: v for k, v in meta.items() if k != "fingerprint_sha256_12"},
                         ensure_ascii=False, indent=1))
        if meta["env_override"]:
            print("ATTENTION : SUPREME_API_TOKEN est défini dans l'environnement et "
                  "prend le pas sur le fichier ; retirez-le pour utiliser le nouveau jeton.")
        return 0

    if args.cmd == "providers":
        from .providers import configured_providers, write_secrets_template
        if args.init_secrets:
            path = write_secrets_template()
            print(json.dumps({"secrets_template": path, "permissions": "0600",
                              "note": "Fichier vide créé (gitignoré). Remplissez-le HORS dépôt, "
                                      "ou utilisez les variables d'environnement. Aucune clé n'est affichée."},
                             ensure_ascii=False, indent=1))
            return 0
        if args.check:
            from .router import ModelRouter
            r = ModelRouter(allow_network=True)
            results = r.check_availability()
            print(json.dumps({"availability": results,
                              "note": "available = appel HTTP réel réussi ; aucun fournisseur déclaré opérationnel sans preuve."},
                             ensure_ascii=False, indent=1))
            return 0
        conf = configured_providers()
        print(json.dumps({"providers": conf,
                          "configured_count": sum(1 for x in conf if x["configured"]),
                          "priority_order": [x["name"] for x in sorted(conf, key=lambda y: y["priority"])],
                          "secure_config": "Clés via env (MISTRAL_API_KEY, ...) ou var/supreme/providers.json (0600, gitignoré).",
                          "note": "Configuré != opérationnel. Seul un appel API réel réussi rend un fournisseur opérationnel."},
                         ensure_ascii=False, indent=1))
        return 0

    from .api import bootstrap
    from .evaluation import EvaluationEngine
    from .observability import ObservabilityEngine
    from .reporting import ReportingEngine
    from .backup import BackupManager

    if args.cmd == "audit":
        from .audit import run_audit
        report = run_audit(save=not args.no_save)
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return 0 if report.get("ok") else 1

    core = bootstrap(evaluate=False)
    if args.cmd == "worker":
        from .worker import run_worker
        stop = _stop_event_with_signals()
        print(json.dumps(run_worker(once=args.once, interval=args.interval,
                                    max_missions=args.max, core=core, max_polls=args.max_polls,
                                    worker_id=args.worker_id, lease_seconds=args.lease_seconds,
                                    heartbeat_interval=args.heartbeat_seconds,
                                    stop_event=stop), ensure_ascii=False, indent=1))
        return 0
    if args.cmd == "learn":
        from .learning import LearningEngine, LearningScheduler
        from .evaluation import EvaluationEngine
        ev = EvaluationEngine(core.conn, core.registry, router=core.router)
        le = LearningEngine(core.conn, core.registry, ev)
        if args.status:
            sched = LearningScheduler(core.conn, le, scheduler_id=args.scheduler_id,
                                      interval_seconds=args.interval, max_proposals=args.max_proposals,
                                      lease_seconds=args.lease_seconds, heartbeat_interval=args.heartbeat_seconds)
            print(json.dumps(sched.status(), ensure_ascii=False, indent=1))
            return 0
        if args.periodic:
            sched = LearningScheduler(core.conn, le, scheduler_id=args.scheduler_id,
                                      interval_seconds=args.interval, max_proposals=args.max_proposals,
                                      lease_seconds=args.lease_seconds, heartbeat_interval=args.heartbeat_seconds)
            stop = _stop_event_with_signals()
            print(json.dumps(sched.run(max_cycles=args.max_cycles, stop_event=stop), ensure_ascii=False, indent=1))
            return 0
        print(json.dumps(le.run_cycle(max_proposals=args.max_proposals, trigger="once",
                                      scheduler_id=args.scheduler_id, lease_seconds=args.lease_seconds),
                         ensure_ascii=False, indent=1))
        return 0
    if args.cmd == "sync":
        print(json.dumps(core.registry.sync_catalog(), ensure_ascii=False)); return 0
    if args.cmd == "evaluate":
        counts = EvaluationEngine(core.conn, core.registry, router=core.router).evaluate_all(activate=args.activate)
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
        from .config import VAR_DIR
        server, state = serve(args.host, args.port, evaluate=True)
        print(f"API + dashboard sur http://{args.host}:{args.port}")
        print(f"Jeton admin : stocké dans {VAR_DIR / 'api_token.txt'} (0600, jamais affiché)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
