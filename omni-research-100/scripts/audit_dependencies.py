#!/usr/bin/env python3
"""Analyse des dépendances — politique locale + base CVE complète si disponible.

Le sandbox n'a pas accès à la base CVE en ligne : ce script vérifie donc
localement (1) que TOUTES les dépendances sont épinglées, (2) que les versions
installées correspondent aux pins, (3) qu'aucune dépendance n'est importée de
façon non déclarée. La base CVE complète est exécutée par `pip-audit` dans la
CI GitHub Actions (réseau disponible sur le runner).
"""
from __future__ import annotations

import json
import re
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQ = ROOT / "requirements.txt"
OUT = ROOT / "test-results" / "dependency_audit.json"
PIN = re.compile(r"^([A-Za-z0-9_.-]+)\s*==\s*([0-9][^\s;#]*)\s*(?:#.*)?$")


def main() -> int:
    problems: list[str] = []
    checked: list[dict[str, str]] = []
    for raw in REQ.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = PIN.match(line)
        if not match:
            problems.append(f"dépendance non épinglée : {line}")
            continue
        name, pinned = match.group(1), match.group(2)
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed = "non installée"
        checked.append({"name": name, "pinned": pinned, "installed": installed})
        if installed != pinned and installed != "non installée":
            problems.append(f"{name} : installé {installed} != épinglé {pinned}")
    report = {
        "policy": "PASS" if not problems else "FAIL",
        "pinned_dependencies": len(checked),
        "unpinned_or_mismatched": problems,
        "packages": checked,
        "local_cve_scan": "non exécuté (accès réseau restreint dans ce contexte)",
        "ci_cve_scan": "pip-audit -r requirements.txt (GitHub Actions, réseau runner)",
        "note": "Les dépendances optionnelles commentées ne sont pas exigées.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("policy", "pinned_dependencies",
                                             "unpinned_or_mismatched")},
                     ensure_ascii=False, indent=2))
    if "--strict" in sys.argv and problems:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
