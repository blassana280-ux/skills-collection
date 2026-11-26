#!/usr/bin/env python3
"""Healthcheck d'exploitation — sans secret, sans écriture, code retour exploitable.

    python3 ops/healthcheck.py [--url http://127.0.0.1:8765] [--require-guardian]

0 = sain ; 1 = dégradé/échec. Utilisable par systemd, Docker HEALTHCHECK ou cron.
Le jeton admin n'est jamais nécessaire : seuls les endpoints de lecture sont utilisés,
et uniquement si la lecture anonyme est activée ; sinon `/api/health` suffit.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8765")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--require-guardian", action="store_true")
    args = ap.parse_args()
    base = args.url.rstrip("/")
    report: dict = {"url": base, "checks": {}}

    def get(path):
        with urllib.request.urlopen(base + path, timeout=args.timeout) as response:
            return response.status, json.loads(response.read())

    try:
        status, health = get("/api/health")
        report["checks"]["health"] = {"http": status, "status": health.get("status"),
                                      "version": health.get("version")}
        healthy = status == 200 and health.get("status") == "ok"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        report["checks"]["health"] = {"error": type(exc).__name__}
        report["ok"] = False
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return 1

    if args.require_guardian:
        try:
            status, guardian = get("/api/guardian")
            report["checks"]["guardian"] = {"http": status, "ready": guardian.get("ready"),
                                            "blocking_findings": guardian.get("blocking_findings")}
            healthy = healthy and status == 200 and guardian.get("blocking_findings") == 0
        except urllib.error.HTTPError as exc:
            # Lecture anonyme désactivée : non bloquant, mais signalé honnêtement.
            report["checks"]["guardian"] = {"http": exc.code, "note": "authentification requise"}
        except (urllib.error.URLError, OSError, ValueError) as exc:
            report["checks"]["guardian"] = {"error": type(exc).__name__}
            healthy = False

    report["ok"] = bool(healthy)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())
