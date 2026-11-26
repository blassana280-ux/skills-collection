#!/usr/bin/env python3
"""Vérifie le dépôt privé livré (branches, PR, CI, protection, arbre).

À relancer après reconnexion GitHub dans cette session : le jeton d'installation
actuel est antérieur à la création du dépôt et renvoie 403. Le script consigne
honnêtement l'état accessible dans `test-results/delivery_repo_check.json` et ne
prétend jamais qu'une vérification impossible a eu lieu.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test-results" / "delivery_repo_check.json"
OWNER, REPO = "blassana280-ux", "omni-research-100"
FULL = f"{OWNER}/{REPO}"


def gh(*args: str) -> tuple[bool, str]:
    try:
        done = subprocess.run(["gh", *args], capture_output=True, text=True,
                              timeout=40)
        return done.returncode == 0, (done.stdout or done.stderr).strip()
    except Exception as exc:
        return False, str(exc)[:300]


def main() -> int:
    report: dict = {"repo": FULL, "checks": {}}
    ok, raw = gh("api", f"repos/{FULL}", "--jq", ".full_name")
    report["checks"]["repo_access"] = {"ok": ok, "detail": raw[:200]}
    if not ok:
        report["status"] = "BLOQUÉ"
        report["reason"] = ("Le jeton de cette session ne peut pas accéder au "
                            "dépôt privé (403 Resource not accessible by integration). "
                            "Reconnecter GitHub dans CETTE session, puis relancer.")
        report["unverified"] = ["branches", "PR #1..#4", "CI du dépôt autonome",
                                "protection de main", "nombre de fichiers",
                                "SHA de l'arbre git"]
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    ok, raw = gh("api", f"repos/{FULL}/branches", "--jq", ".[].name")
    report["checks"]["branches"] = {"ok": ok, "names": raw.splitlines()}
    ok, raw = gh("api", f"repos/{FULL}/branches/main/protection", "--jq",
                 "(.required_status_checks != null)")
    report["checks"]["main_protection"] = {"ok": ok, "detail": raw[:200]}
    ok, raw = gh("pr", "list", "--repo", FULL, "--state", "open", "--limit", "20",
                 "--json", "number,title,headRefName,baseRefName")
    try:
        prs = json.loads(raw) if ok else []
    except Exception:
        prs = []
    report["checks"]["open_prs"] = {"ok": ok, "count": len(prs), "prs": prs}
    ok, raw = gh("run", "list", "--repo", FULL, "--limit", "8", "--json",
                 "databaseId,conclusion,event")
    try:
        runs = json.loads(raw) if ok else []
    except Exception:
        runs = []
    report["checks"]["ci_runs"] = {"ok": ok, "count": len(runs), "runs": runs}
    ok, raw = gh("api", f"repos/{FULL}/git/trees/main?recursive=1", "--jq",
                 "{sha:.sha, paths: [.tree[].path] | length, truncated:.truncated}")
    report["checks"]["tree"] = {"ok": ok, "detail": raw[:300]}
    report["status"] = "VÉRIFIÉ" if all(v.get("ok") for v in report["checks"].values()) \
        else "PARTIEL"
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2)[:1500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
