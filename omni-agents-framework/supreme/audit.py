"""Audit exécutable SUPREME (Phase I) — produit des preuves vérifiables, pas un récit.

`python3 -m supreme audit` contrôle : catalogue (1020 profils, 20×50, 0 doublon),
registre, fournisseurs (sans clés), sécurité (permissions jeton, fichiers gitignorés,
aucun affichage de secret), sauvegardes, KPIs réels, nombre de tests découverts.
Le rapport JSON est horodaté et archivé dans var/supreme/ (gitignoré).
"""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from .config import SUPREME_ROOT, VAR_DIR, ensure_dirs
from .db import now

FRAMEWORK_ROOT = SUPREME_ROOT.parent


def _catalog_audit() -> dict:
    from .profiles import validate_catalog
    from .tools import TOOLS
    agents = json.loads((SUPREME_ROOT / "catalog" / "agents.json").read_text(encoding="utf-8"))
    specialists = [a for a in agents if a["kind"] == "specialist"]
    managers = [a for a in agents if a["kind"] == "manager"]
    errors = validate_catalog(specialists, managers, set(TOOLS))
    by_div: dict[str, int] = {}
    for a in specialists:
        by_div[a["division"]] = by_div.get(a["division"], 0) + 1
    return {"total_profiles": len(agents), "specialists": len(specialists), "managers": len(managers),
            "divisions": len(by_div), "per_division_ok": all(v == 50 for v in by_div.values()),
            "validation_errors": errors, "ok": not errors and len(specialists) == 1000 and len(managers) == 20}


def _security_audit() -> dict:
    tok = VAR_DIR / "api_token.txt"
    files_ignored = {}
    for rel in ("var/supreme/api_token.txt", "var/supreme/providers.json", "var/supreme/access.log"):
        r = subprocess.run(["git", "check-ignore", "-q", f"omni-agents-framework/{rel}"],
                           cwd=FRAMEWORK_ROOT.parent, capture_output=True)
        files_ignored[rel] = r.returncode == 0
    prints_secret = False
    for py in SUPREME_ROOT.glob("*.py"):
        if py.name == "audit.py":
            continue  # ce module contient les littéraux de détection, pas un affichage
        text = py.read_text(encoding="utf-8")
        if "print" in text and "admin_token" in text:
            for line in text.splitlines():
                if "print" in line and "admin_token" in line and "jamais affiché" not in line:
                    prints_secret = True
    return {"token_file_present": tok.is_file(),
            "token_permissions": oct(tok.stat().st_mode & 0o777) if tok.is_file() else None,
            "secret_files_gitignored": files_ignored,
            "code_prints_token": prints_secret,
            "ok": (not prints_secret) and all(files_ignored.values())
                  and (not tok.is_file() or (tok.stat().st_mode & 0o777) == 0o600)}


def _tests_count() -> int:
    suite = unittest.TestLoader().discover(str(FRAMEWORK_ROOT / "tests"))
    return suite.countTestCases()


def run_audit(save: bool = True, conn=None) -> dict:
    from .backup import BackupManager
    from .providers import configured_providers
    from .registry import Registry
    from .observability import ObservabilityEngine
    from .budget import BudgetController
    from .router import ModelRouter
    from .db import get_conn

    own = conn is None
    conn = conn or get_conn()
    registry = Registry(conn)
    obs = ObservabilityEngine(conn, registry, BudgetController(conn), ModelRouter(conn))
    backups = BackupManager().list_backups()
    conf = configured_providers()
    report = {
        "audited_at": now(),
        "catalog": _catalog_audit(),
        "registry": {"status_counts": registry.status_counts()},
        "providers": {"configured_count": sum(1 for p in conf if p["configured"]),
                      "priority_order": [p["name"] for p in sorted(conf, key=lambda x: x["priority"])],
                      "note": "configuré != opérationnel ; 0 appel réel réussi = 0 connecté"},
        "security": _security_audit(),
        "backups": {"count": len(backups),
                    "latest": backups[-1]["id"] if backups else None,
                    "latest_integrity": backups[-1].get("integrity") if backups else None},
        "kpis": obs.kpis(),
        "tests_discovered": _tests_count(),
        "distinctions": ["enregistré != opérationnel", "connecteur écrit != fournisseur connecté",
                         "serveur local != déploiement cloud", "test simulé != intégration réelle"],
    }
    report["ok"] = report["catalog"]["ok"] and report["security"]["ok"]
    if save:
        ensure_dirs()
        p = VAR_DIR / f"audit-{now().replace(':', '').replace('-', '')[:15]}.json"
        p.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        report["saved_to"] = str(p)
    return report
