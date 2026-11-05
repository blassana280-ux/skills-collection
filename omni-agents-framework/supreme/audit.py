"""Audit exécutable SUPREME (Phase I) — produit des preuves vérifiables, pas un récit.

`python3 -m supreme audit` contrôle : catalogue (1020 profils, 20×50, 0 doublon),
registre, fournisseurs (sans clés), sécurité (permissions jeton, fichiers gitignorés,
aucun affichage de secret), sauvegardes, KPIs réels, nombre de tests découverts.
Le rapport JSON est horodaté et archivé dans var/supreme/ (gitignoré).
"""
from __future__ import annotations

import json
import os
import subprocess
import unittest
import uuid
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
    for rel in ("var/supreme/api_token.txt", "var/supreme/providers.json", "var/supreme/access.log",
                "var/supreme/secrets/mistral.key", "var/supreme/activation/act-example.json"):
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
    from . import SUPREME_VERSION
    from .backup import BackupManager
    from .providers import configured_providers
    from .provider_control import ProviderControl
    from .activation import ActivationManager
    from .registry import Registry
    from .observability import ObservabilityEngine
    from .budget import BudgetController
    from .router import ModelRouter
    from .db import get_conn, epoch

    own = conn is None
    conn = conn or get_conn()
    registry = Registry(conn)
    budget = BudgetController(conn)
    obs = ObservabilityEngine(conn, registry, budget, ModelRouter(conn))
    backups = BackupManager().list_backups()
    conf = configured_providers()
    schema = conn.execute("SELECT value FROM schema_meta WHERE key='version'").fetchone()
    workers = {r["state"]: r["c"] for r in conn.execute("SELECT state, COUNT(*) c FROM workers GROUP BY state")}
    active_leases = conn.execute("SELECT COUNT(*) c FROM missions WHERE state='running' AND lease_expires_at > ?", (epoch(),)).fetchone()["c"]
    orphan_tasks = conn.execute(
        """SELECT COUNT(*) c FROM tasks t JOIN missions m ON m.id=t.mission_id
           WHERE m.state='planned' AND t.state IN ('assigned','running','validating')""").fetchone()["c"]
    learning_running = conn.execute("SELECT COUNT(*) c FROM learning_runs WHERE status='running'").fetchone()["c"]
    learning_errors = conn.execute("SELECT COUNT(*) c FROM learning_runs WHERE status IN ('failed','interrupted')").fetchone()["c"]
    quota_violations = []
    for q in conn.execute("SELECT scope, scope_id, limit_usd FROM quotas").fetchall():
        exposure = budget.exposure(q["scope"], q["scope_id"])
        if exposure > float(q["limit_usd"]) + 1e-9:
            quota_violations.append({"scope": q["scope"], "scope_id": q["scope_id"],
                                     "limit_usd": q["limit_usd"], "exposure_usd": exposure})
    over_settled = conn.execute(
        "SELECT COUNT(*) c FROM budget_reservations WHERE status='settled' AND actual_cost_usd > amount_usd + 1e-12").fetchone()["c"]
    activation_running = conn.execute("SELECT COUNT(*) c FROM activation_campaigns WHERE status='running'").fetchone()["c"]
    reliability = {"schema_version": int(schema["value"]) if schema else None,
                   "workers": workers, "active_leases": active_leases,
                   "orphan_active_tasks_in_planned_missions": orphan_tasks,
                   "learning_running": learning_running, "learning_error_runs": learning_errors,
                   "activation_campaigns_running": activation_running,
                   "ok": (schema and int(schema["value"]) >= 3 and orphan_tasks == 0 and learning_running <= 1 and activation_running <= 1)}
    budget_audit = {"reservations": {r["status"]: r["c"] for r in conn.execute(
                        "SELECT status, COUNT(*) c FROM budget_reservations GROUP BY status")},
                    "quota_violations": quota_violations, "settled_over_reservation": over_settled,
                    "ok": not quota_violations and over_settled == 0}
    report = {
        "audited_at": now(), "version": SUPREME_VERSION,
        "framework_root": str(FRAMEWORK_ROOT),
        "catalog": _catalog_audit(),
        "registry": {"status_counts": registry.status_counts()},
        "providers": {"configured_count": sum(1 for p in conf if p["configured"]),
                      "verification": ProviderControl(conn).summary(),
                      "priority_order": [p["name"] for p in sorted(conf, key=lambda x: x["priority"])],
                      "note": "configuré != connecté ; preuve external_api réussie requise ; inférence fermée par défaut"},
        "activation": {"external_llm_activated": len(ActivationManager(conn, registry, ModelRouter(conn)).activated_ids()),
                       "quarantined": conn.execute("SELECT COUNT(*) c FROM agent_quarantine WHERE review_required=1").fetchone()["c"],
                       "campaigns": {r["status"]: r["c"] for r in conn.execute("SELECT status, COUNT(*) c FROM activation_campaigns GROUP BY status")}},
        "security": _security_audit(),
        "reliability": reliability,
        "budget": budget_audit,
        "backups": {"count": len(backups),
                    "latest": backups[-1]["id"] if backups else None,
                    "latest_integrity": backups[-1].get("integrity") if backups else None},
        "kpis": obs.kpis(),
        "tests_discovered": _tests_count(),
        "distinctions": ["enregistré != opérationnel", "connecteur écrit != fournisseur connecté",
                         "serveur local != déploiement cloud", "test simulé != intégration réelle"],
    }
    report["ok"] = (report["catalog"]["ok"] and report["security"]["ok"]
                    and reliability["ok"] and budget_audit["ok"])
    if save:
        ensure_dirs()
        p = VAR_DIR / f"audit-{now().replace(':', '').replace('-', '')[:15]}-{uuid.uuid4().hex[:8]}.json"
        p.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        os.chmod(p, 0o600)
        report["saved_to"] = str(p)
    return report
