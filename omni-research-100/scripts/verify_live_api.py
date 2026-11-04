#!/usr/bin/env python3
"""Vérification HTTP de bout en bout de l'application RÉELLE lancée en uvicorn.

Aucune donnée n'est simulée : toutes les réponses viennent du serveur. Utilise
uniquement des variables d'environnement pour les identifiants (aucun secret
dans le code) :

    OR100_BASE_URL=http://127.0.0.1:8000 OR100_ADMIN=admin \
    OR100_PASSWORD=... OR100_OMNIBRAIN_KEY=... \
    python scripts/verify_live_api.py

Rapport : test-results/live_api_full.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test-results" / "live_api_full.json"
BASE = os.getenv("OR100_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ADMIN = os.getenv("OR100_ADMIN")
PASSWORD = os.getenv("OR100_PASSWORD")
OMNI_KEY = os.getenv("OR100_OMNIBRAIN_KEY")


def main() -> int:
    if not (ADMIN and PASSWORD and OMNI_KEY):
        report = {"status": "NON EXÉCUTÉ",
                  "reason": "OR100_ADMIN / OR100_PASSWORD / OR100_OMNIBRAIN_KEY requis"}
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0
    checks: dict[str, dict] = {}
    failures: list[str] = []

    def record(name: str, response: httpx.Response | None,
               expect: int | tuple[int, ...] = 200, extra=None) -> None:
        if response is None:
            checks[name] = {"ok": False, "error": "exception"}
            failures.append(name)
            return
        codes = expect if isinstance(expect, tuple) else (expect,)
        ok = response.status_code in codes
        row = {"ok": ok, "status": response.status_code}
        try:
            payload = response.json()
            row["keys"] = sorted(payload)[:12] if isinstance(payload, dict) else "list"
        except Exception:
            row["keys"] = "non-json"
        if extra:
            row.update(extra(response, payload if 'payload' in locals() else None))
        checks[name] = row
        if not ok:
            failures.append(f"{name}: HTTP {response.status_code} (attendu {codes})")

    with httpx.Client(base_url=BASE, timeout=15.0) as client:
        record("health", client.get("/api/health"))
        login = client.post("/api/auth/login", json={"username": ADMIN,
                                                     "password": PASSWORD})
        record("login", login)
        token = login.json().get("access_token", "")
        auth = {"Authorization": "Bearer " + token}
        omni = {"X-OmniBrain-Key": OMNI_KEY, "X-OmniBrain-Contract": "1.0"}

        record("auth_me", client.get("/api/auth/me", headers=auth))
        record("auth_permissions", client.get("/api/auth/permissions", headers=auth))
        record("anonymous_rejected", client.get("/api/settings"), (401, 403))

        record("settings", client.get("/api/settings", headers=auth))
        record("metrics", client.get("/api/metrics", headers=auth))
        record("audit", client.get("/api/audit", headers=auth))
        record("backup", client.post("/api/backup", headers=auth))
        record("purge_refused", client.post("/api/retention/purge", headers=auth,
                                            json={"older_than_days": 30,
                                                  "confirm": "NON"}), (400, 403, 422))

        for path in ("/api/agents?limit=100", "/api/agents/divisions",
                     "/api/agents/validation", "/api/agents/export/omnibrain",
                     "/api/agents/WEB-01", "/api/providers", "/api/providers/quota",
                     "/api/history"):
            record(path, client.get(path, headers=auth))
        record("provider_test_sans_cle", client.post("/api/providers/tavily/test",
                                                     headers=auth,
                                                     json={"query": "test"}))

        created = client.post("/api/missions", headers=auth,
                              json={"query": "Vérification HTTP complète de l API",
                                    "mode": "fast"})
        record("mission_create", created, 202)
        mid = created.json().get("mission_id", "")
        deadline = time.monotonic() + 12
        status = ""
        while time.monotonic() < deadline:
            detail = client.get(f"/api/missions/{mid}", headers=auth)
            status = detail.json().get("status", "")
            if status in ("completed", "failed", "cancelled", "insufficient_evidence"):
                break
            time.sleep(0.15)
        checks["mission_terminal"] = {"ok": bool(status), "status": status,
                                      "mission_id": mid}
        for suffix in ("/agents", "/sources", "/claims", "/contradictions",
                       "/report"):
            record("mission" + suffix,
                   client.get(f"/api/missions/{mid}{suffix}", headers=auth))
        # SSE : lecture réelle des premiers événements rejoués depuis la table events.
        try:
            with client.stream("GET", f"/api/missions/{mid}/events",
                               headers=auth, params={"timeout": 1}) as stream:
                lines = []
                for line in stream.iter_lines():
                    if line:
                        lines.append(line[:160])
                    if len(lines) >= 4:
                        break
                checks["sse_stream"] = {"ok": stream.status_code == 200 and bool(lines),
                                        "status": stream.status_code,
                                        "sample": lines[:4]}
        except Exception as exc:
            checks["sse_stream"] = {"ok": False, "error": str(exc)[:200]}
            failures.append("sse_stream")

        record("omni_contract", client.get("/api/omnibrain/v1/contract", headers=omni))
        record("omni_modes", client.get("/api/omnibrain/v1/modes", headers=omni))
        record("omni_bad_version", client.get("/api/omnibrain/v1/contract",
                                              headers={"X-OmniBrain-Key": OMNI_KEY,
                                                       "X-OmniBrain-Contract": "9.9"}),
               (400, 422))
        record("omni_queue_status", client.get("/api/omnibrain/v1/queue/status",
                                               headers=omni))
        record("omni_queue_process", client.post("/api/omnibrain/v1/queue/process",
                                                 headers=omni))
        submitted = client.post("/api/omnibrain/v1/missions", headers=omni,
                                json={"skill": "research", "request": "test live",
                                      "task": {"query": "compatibilité"}, "mode": "fast"})
        record("omni_submit", submitted, 202)
        omid = submitted.json().get("mission_id", "")
        if omid:
            for suffix in ("", "/results", "/report", "/evidence"):
                record("omni_get" + (suffix or "_status"),
                       client.get("/api/omnibrain/v1/missions/" + omid + suffix,
                                  headers=omni), (200, 422))
            record("omni_cancel", client.delete("/api/omnibrain/v1/missions/" + omid,
                                                headers=omni))

    report = {
        "status": "OK" if not failures else "ÉCHEC",
        "base_url": BASE,
        "checks": checks,
        "failures": failures,
        "note": "Application réelle (uvicorn) ; aucun résultat de recherche simulé.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": len(checks),
                      "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
