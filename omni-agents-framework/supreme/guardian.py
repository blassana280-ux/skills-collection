"""Guardian SUPREME — protection continue et autoprotection vérifiable.

Le Guardian observe, détecte et alerte. Il ne modifie ni les permissions, ni les
politiques, ni le noyau, et ne « répare » jamais silencieusement une règle de
sécurité : toute remédiation sensible reste une action humaine tracée.

Contrôles exécutés (tous locaux, sans réseau par défaut) :
- secrets exposés dans les fichiers suivis par Git ;
- permissions/propriétaire des fichiers secrets runtime ;
- intégrité des fichiers cœur (baseline d'empreintes, détection de modification) ;
- dépendances non stdlib introduites dans la couche SUPREME ;
- actions d'agents refusées et tentatives d'injection dans les données stockées ;
- anomalies budgétaires (quotas dépassés, solde supérieur à la borne, réservations incertaines) ;
- doubles exécutions et hygiene des baux ;
- protection des sauvegardes (intégrité et fraîcheur) ;
- quarantaines en attente de revue ;
- dérive des contrôles fournisseurs (autorisation expirée, prix périmés) ;
- permissions GitHub (optionnel, uniquement si explicitement autorisé et `gh` disponible).

Chaque constat est dédupliqué par empreinte, horodaté, compté et conservé en base.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import uuid
from pathlib import Path

from .config import FRAMEWORK_ROOT, SUPREME_ROOT, VAR_DIR
from .db import epoch, get_conn, log_event, now, transaction
from .leases import new_worker_id, register_worker
from .security import redact, scan_injection

SEVERITIES = ("info", "low", "medium", "high", "critical")
BLOCKING_SEVERITIES = ("high", "critical")
SECRET_FILE_GLOBS = ("api_token.txt", "providers.json", "secrets/*.key", "activation/*.json",
                     "learning/*.json", "guardian/*.json")
CORE_GLOBS = ("supreme/*.py", "supreme/dashboard/index.html", "supreme/catalog/agents.json")
MAX_SCAN_BYTES = 512_000
_AGE_BACKUP_HOURS = 48

# Motifs haute confiance alignés sur tests/test_supreme_security_audit.py : une
# valeur de clé réelle, jamais un identifiant de variable ou un nom de champ.
HIGH_CONFIDENCE_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"),
)
KNOWN_NON_SECRET = {
    "AKIAIOSFODNN7EXAMPLE",
    "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123",
    "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _finding(code: str, severity: str, component: str, detail: str, evidence: dict | None = None) -> dict:
    if severity not in SEVERITIES:
        raise ValueError(f"sévérité invalide : {severity}")
    return {"code": code, "severity": severity, "component": component,
            "detail": redact(detail)[:500], "evidence": evidence or {}}


RESOLVE_CONFIRM = "REVUE HUMAINE EFFECTUEE"


class GuardianEngine:
    def __init__(self, conn: sqlite3.Connection, registry=None, budget=None,
                 repo_root: Path | None = None, var_dir: Path | None = None,
                 allow_github: bool = False):
        self.conn = conn
        self.registry = registry
        self.budget = budget
        self.repo_root = Path(repo_root) if repo_root else FRAMEWORK_ROOT.parent
        self.var_dir = Path(var_dir) if var_dir else VAR_DIR
        self.allow_github = bool(allow_github)

    # ------------------------------------------------------------ checks
    def _git(self, *args: str) -> tuple[bool, str]:
        try:
            r = subprocess.run(["git", *args], cwd=str(self.repo_root), capture_output=True,
                               text=True, timeout=30)
            return r.returncode == 0, r.stdout
        except (OSError, subprocess.SubprocessError):
            return False, ""

    def check_repo_secrets(self) -> list[dict]:
        """Détecte une valeur secrète versionnée, pas un nom de variable.

        Réutilise les motifs haute confiance du test anti-fuite (clés AWS/GitHub/
        Slack/OpenAI, clés privées) et exclut la documentation, les fixtures et les
        bibliothèques upstream. Un nom comme `MISTRAL_API_KEY` n'est pas une fuite.
        """
        ok, out = self._git("ls-files", "-z")
        if not ok:
            return [_finding("repo_unavailable", "info", "git", "dépôt Git non inspectable ici", {})]
        findings = []
        for rel in out.split("\0"):
            if not rel or rel.startswith(("omni-agents-framework/var/", "skills/", "data/")):
                continue
            path = self.repo_root / rel
            if not path.is_file() or path.stat().st_size > MAX_SCAN_BYTES:
                continue
            # Littéraux de détection, fixtures de test et documentation ne sont pas des fuites.
            if (path.name in {"security.py", "guardian.py"} or "/tests/" in rel
                    or rel.startswith("tests/") or path.suffix in {".md", ".json"}):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for pat in HIGH_CONFIDENCE_SECRET_PATTERNS:
                hit = next((m for m in pat.finditer(text) if m.group(0) not in KNOWN_NON_SECRET), None)
                if hit:
                    findings.append(_finding("secret_in_repo", "critical", "git",
                                             f"valeur secrète détectée dans un fichier suivi : {rel}",
                                             {"path": rel, "line": text[:hit.start()].count("\n") + 1}))
                    break
        return findings

    def check_secret_permissions(self) -> list[dict]:
        findings = []
        for pattern in SECRET_FILE_GLOBS:
            for path in sorted(self.var_dir.glob(pattern)):
                try:
                    st = path.lstat()
                except OSError:
                    continue
                mode = st.st_mode & 0o777
                if path.is_symlink():
                    findings.append(_finding("secret_symlink", "high", "filesystem",
                                             f"fichier secret symbolique : {path.name}", {"file": path.name}))
                elif mode & 0o077:
                    findings.append(_finding("secret_permissions", "high", "filesystem",
                                             f"permissions trop larges sur {path.name} : {oct(mode)}",
                                             {"file": path.name, "mode": oct(mode)}))
                elif st.st_uid != os.getuid():
                    findings.append(_finding("secret_owner", "high", "filesystem",
                                             f"propriétaire inattendu pour {path.name}", {"file": path.name}))
        secrets_dir = self.var_dir / "secrets"
        if secrets_dir.is_dir() and (secrets_dir.stat().st_mode & 0o777) & 0o077:
            findings.append(_finding("secret_dir_permissions", "high", "filesystem",
                                     "répertoire de secrets accessible aux autres",
                                     {"mode": oct(secrets_dir.stat().st_mode & 0o777)}))
        return findings

    def check_core_integrity(self) -> list[dict]:
        """Première passe : enregistre la baseline. Ensuite : signale toute modification."""
        paths = sorted(p for pattern in CORE_GLOBS for p in SUPREME_ROOT.parent.glob(pattern) if p.is_file())
        known = {r["path"]: dict(r) for r in self.conn.execute("SELECT * FROM integrity_baseline")}
        findings = []
        seen = set()
        with transaction(self.conn, immediate=True):
            for path in paths:
                rel = str(path.relative_to(FRAMEWORK_ROOT))
                seen.add(rel)
                digest = _sha256(path)
                row = known.get(rel)
                if row is None:
                    self.conn.execute(
                        "INSERT INTO integrity_baseline(path,sha256,size_bytes,recorded_at) VALUES(?,?,?,?)",
                        (rel, digest, path.stat().st_size, now()))
                elif row["sha256"] != digest:
                    findings.append(_finding("core_file_modified", "high", "integrity",
                                             f"fichier cœur modifié depuis la baseline : {rel}",
                                             {"path": rel, "expected_sha256": row["sha256"][:16],
                                              "actual_sha256": digest[:16], "baseline_at": row["recorded_at"]}))
            for rel in set(known) - seen:
                findings.append(_finding("core_file_missing", "high", "integrity",
                                         f"fichier cœur disparu depuis la baseline : {rel}", {"path": rel}))
        return findings

    def rebaseline_core(self, *, confirm: str, approved_by: str, reason: str,
                        evidence: str) -> dict:
        """Ré-enregistre la baseline après un changement LÉGITIME revu par un humain.

        Ne s'exécute jamais automatiquement : exige confirmation explicite, auteur,
        motif et référence de preuve (commit/PR/revue). L'ancienne baseline est
        journalisée dans `events` avant remplacement : aucune perte d'historique.
        """
        if confirm != RESOLVE_CONFIRM:
            raise PermissionError(f"re-baseline refusée : --confirm '{RESOLVE_CONFIRM}' requis")
        if not approved_by.strip() or not reason.strip() or not evidence.strip():
            raise PermissionError("re-baseline refusée : --approved-by, --reason et --evidence requis")
        paths = sorted(p for pattern in CORE_GLOBS for p in FRAMEWORK_ROOT.glob(pattern) if p.is_file())
        previous = [dict(r) for r in self.conn.execute("SELECT * FROM integrity_baseline ORDER BY path")]
        changed = []
        with transaction(self.conn, immediate=True):
            for path in paths:
                rel = str(path.relative_to(FRAMEWORK_ROOT))
                digest = _sha256(path)
                old = self.conn.execute("SELECT sha256 FROM integrity_baseline WHERE path=?", (rel,)).fetchone()
                if old and old["sha256"] != digest:
                    changed.append({"path": rel, "previous_sha256": old["sha256"], "new_sha256": digest})
                self.conn.execute(
                    """INSERT INTO integrity_baseline(path,sha256,size_bytes,recorded_at) VALUES(?,?,?,?)
                       ON CONFLICT(path) DO UPDATE SET sha256=excluded.sha256,
                         size_bytes=excluded.size_bytes, recorded_at=excluded.recorded_at""",
                    (rel, digest, path.stat().st_size, now()))
            self.conn.execute(
                """INSERT INTO events(at,level,component,message,data_json) VALUES(?,?,?,?,?)""",
                (now(), "warning", "guardian",
                 f"baseline noyau ré-enregistrée par {approved_by} : {reason}",
                 json.dumps({"approved_by": approved_by, "reason": reason, "evidence": evidence,
                             "changed": changed, "previous_count": len(previous)}, ensure_ascii=False)))
        # Les constats d'intégrité désormais caducs sont clos avec la même preuve.
        closed = 0
        for row in self.conn.execute(
                "SELECT id FROM security_findings WHERE component='integrity' AND status='open'").fetchall():
            self.conn.execute(
                """UPDATE security_findings SET status='resolved', resolved_at=?, resolution=?
                   WHERE id=?""",
                (now(), f"re-baseline approuvée par {approved_by} — {reason} (preuve : {evidence})", row["id"]))
            closed += 1
        self.conn.commit()
        return {"rebaselined": len(paths), "changed": changed, "findings_closed": closed,
                "approved_by": approved_by, "evidence": evidence, "at": now()}

    def check_dependencies(self) -> list[dict]:
        """SUPREME doit rester stdlib : toute dépendance externe est signalée."""
        stdlib = getattr(sys, "stdlib_module_names", frozenset())
        local = {p.stem for p in SUPREME_ROOT.glob("*.py")} | {"supreme", "omni", "omnibrain"}
        findings = []
        for path in sorted(SUPREME_ROOT.glob("*.py")):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for mod in re.findall(r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)", text, re.M):
                if mod in stdlib or mod in local or mod == "__future__":
                    continue
                findings.append(_finding("external_dependency", "medium", "dependencies",
                                         f"import non stdlib dans la couche SUPREME : {mod} ({path.name})",
                                         {"module": mod, "file": path.name}))
        return findings

    def check_agent_actions(self) -> list[dict]:
        findings = []
        denials = self.conn.execute(
            "SELECT COUNT(*) c FROM events WHERE level IN ('warning','error','critical') "
            "AND (message LIKE '%refus%' OR message LIKE '%interdit%' OR message LIKE '%usurpation%')").fetchone()["c"]
        if denials:
            findings.append(_finding("agent_action_denied", "medium", "agents",
                                     f"{denials} action(s) d'agent refusée(s) ou signalée(s) dans le journal",
                                     {"count": int(denials)}))
        injections = 0
        for row in self.conn.execute("SELECT content FROM memory_items WHERE deleted=0 ORDER BY rowid DESC LIMIT 500"):
            if scan_injection(row["content"]):
                injections += 1
        if injections:
            findings.append(_finding("injection_in_memory", "high", "injection",
                                     f"{injections} contenu(s) mémorisé(s) contenant une tentative d'injection",
                                     {"count": injections}))
        return findings

    def check_budget_anomalies(self) -> list[dict]:
        findings = []
        over = self.conn.execute(
            "SELECT COUNT(*) c FROM budget_reservations WHERE status='settled' AND actual_cost_usd > amount_usd + 1e-12").fetchone()["c"]
        if over:
            findings.append(_finding("settled_over_bound", "critical", "budget",
                                     f"{over} règlement(s) au-dessus de la borne réservée", {"count": int(over)}))
        stale = self.conn.execute(
            "SELECT COUNT(*) c FROM budget_reservations WHERE status IN ('reserved','interrupted')").fetchone()["c"]
        if stale:
            findings.append(_finding("uncertain_exposure", "medium", "budget",
                                     f"{stale} réservation(s) ouverte(s)/incertaine(s) à réconcilier",
                                     {"count": int(stale)}))
        if self.budget is not None:
            for q in self.conn.execute("SELECT scope, scope_id, limit_usd FROM quotas"):
                exposure = self.budget.exposure(q["scope"], q["scope_id"])
                if exposure > float(q["limit_usd"]) + 1e-9:
                    findings.append(_finding("quota_exceeded", "critical", "budget",
                                             f"quota dépassé : {q['scope']}/{q['scope_id']}",
                                             {"limit_usd": q["limit_usd"], "exposure_usd": round(exposure, 9)}))
        return findings

    def check_execution_hygiene(self) -> list[dict]:
        findings = []
        dup = self.conn.execute(
            "SELECT COUNT(*) c FROM (SELECT task_id FROM task_executions GROUP BY task_id HAVING COUNT(*) > 1)").fetchone()["c"]
        if dup:
            findings.append(_finding("double_execution", "critical", "runtime",
                                     f"{dup} tâche(s) avec plusieurs exécutions commitées", {"count": int(dup)}))
        orphan = self.conn.execute(
            """SELECT COUNT(*) c FROM tasks t JOIN missions m ON m.id=t.mission_id
               WHERE m.state='planned' AND t.state IN ('assigned','running','validating')""").fetchone()["c"]
        if orphan:
            findings.append(_finding("orphan_active_tasks", "high", "runtime",
                                     f"{orphan} tâche(s) active(s) dans une mission replanifiée", {"count": int(orphan)}))
        stale = self.conn.execute(
            """SELECT COUNT(*) c FROM missions m LEFT JOIN workers w ON w.worker_id=m.owner_worker_id
               WHERE m.state='running' AND m.lease_expires_at <= ?
                 AND (w.state='stopped' OR w.last_heartbeat IS NULL OR w.last_heartbeat <= m.lease_expires_at)""",
            (epoch(),)).fetchone()["c"]
        if stale:
            findings.append(_finding("abandoned_missions", "medium", "runtime",
                                     f"{stale} mission(s) abandonnée(s) récupérable(s) par un worker",
                                     {"count": int(stale)}))
        return findings

    def check_backups(self) -> list[dict]:
        from .backup import BackupManager
        manager = BackupManager()
        backups = manager.list_backups()
        if not backups:
            return [_finding("no_backup", "high", "backup", "aucune sauvegarde disponible", {})]
        latest = max(backups, key=lambda b: b.get("created_at", ""))
        findings = []
        path = Path(latest.get("db", ""))
        if not path.is_file():
            findings.append(_finding("backup_missing_file", "critical", "backup",
                                     "fichier de la dernière sauvegarde introuvable", {"backup_id": latest.get("id")}))
        else:
            integrity = manager._integrity(path)
            if integrity != "ok":
                findings.append(_finding("backup_corrupted", "critical", "backup",
                                         "dernière sauvegarde corrompue", {"backup_id": latest.get("id")}))
            mode = path.stat().st_mode & 0o777
            if mode & 0o077:
                findings.append(_finding("backup_permissions", "medium", "backup",
                                         f"sauvegarde lisible par d'autres : {oct(mode)}",
                                         {"backup_id": latest.get("id"), "mode": oct(mode)}))
        try:
            from datetime import datetime, timezone
            age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(latest["created_at"])).total_seconds() / 3600
            if age_h > _AGE_BACKUP_HOURS:
                findings.append(_finding("backup_stale", "medium", "backup",
                                         f"dernière sauvegarde ancienne : {age_h:.1f} h",
                                         {"backup_id": latest.get("id"), "age_hours": round(age_h, 2)}))
        except (KeyError, TypeError, ValueError):
            pass
        return findings

    def check_quarantine(self) -> list[dict]:
        rows = self.conn.execute("SELECT agent_id, reason FROM agent_quarantine WHERE review_required=1").fetchall()
        if not rows:
            return []
        return [_finding("quarantine_pending_review", "medium", "activation",
                         f"{len(rows)} agent(s) en quarantaine en attente de revue humaine",
                         {"agents": [r["agent_id"] for r in rows][:20]})]

    def check_provider_drift(self) -> list[dict]:
        findings = []
        for row in self.conn.execute("SELECT * FROM provider_controls"):
            if row["inference_enabled"] and float(row["expires_at"]) <= epoch():
                findings.append(_finding("authorization_expired", "low", "providers",
                                         f"autorisation d'inférence expirée encore marquée active : {row['provider']}",
                                         {"provider": row["provider"]}))
            prices = json.loads(row["pricing_json"] or "{}")
            from .provider_control import PRICE_MAX_AGE_DAYS
            from datetime import datetime, timezone
            for model, entry in prices.items():
                try:
                    age = (datetime.now(timezone.utc) - datetime.fromisoformat(entry["checked_at"])).total_seconds()
                except (KeyError, TypeError, ValueError):
                    continue
                if age > PRICE_MAX_AGE_DAYS * 86400:
                    findings.append(_finding("price_stale", "low", "providers",
                                             f"prix périmé : {row['provider']}/{model}",
                                             {"provider": row["provider"], "model": model}))
        return findings

    def check_github_permissions(self) -> list[dict]:
        """Optionnel : jamais de réseau sans opt-in explicite de l'opérateur."""
        if not self.allow_github:
            return [_finding("github_check_skipped", "info", "github",
                             "contrôle GitHub non exécuté (opt-in requis : --allow-github)", {})]
        try:
            r = subprocess.run(["gh", "api", "repos/{owner}/{repo}", "--jq", ".permissions"],
                               cwd=str(self.repo_root), capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return [_finding("github_unavailable", "info", "github", "gh indisponible dans cet environnement", {})]
        if r.returncode != 0:
            return [_finding("github_unavailable", "info", "github", "accès GitHub non vérifiable ici", {})]
        try:
            perms = json.loads(r.stdout or "{}")
        except json.JSONDecodeError:
            return []
        if perms.get("admin"):
            return [_finding("github_admin_token", "medium", "github",
                             "le jeton courant dispose d'un droit admin sur le dépôt", {"permissions": perms})]
        return []

    CHECKS = ("repo_secrets", "secret_permissions", "core_integrity", "dependencies", "agent_actions",
              "budget_anomalies", "execution_hygiene", "backups", "quarantine", "provider_drift",
              "github_permissions")

    def scan(self, *, trigger: str = "once", stop_event=None, lease_seconds: float = 30.0,
             worker_id: str | None = None) -> dict:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds doit être positif")
        worker = worker_id or new_worker_id("guardian")
        register_worker(self.conn, worker)
        run_id = f"grd-{uuid.uuid4().hex[:12]}"
        token = uuid.uuid4().hex
        with transaction(self.conn, immediate=True):
            running = self.conn.execute("SELECT id FROM guardian_runs WHERE status='running'").fetchone()
            if running:
                return {"status": "skipped", "reason": "un scan Guardian est déjà en cours", "run_id": running["id"]}
            self.conn.execute(
                """INSERT INTO guardian_runs(id,trigger,status,started_at,owner_worker_id,lease_token,
                     lease_expires_at,heartbeat_at) VALUES(?,?,'running',?,?,?,?,?)""",
                (run_id, trigger, now(), worker, token, epoch() + lease_seconds, epoch()))
        checks, findings, errors = {}, [], {}
        try:
            for name in self.CHECKS:
                if stop_event is not None and stop_event.is_set():
                    raise InterruptedError("arrêt propre demandé")
                try:
                    result = getattr(self, f"check_{name}")()
                    checks[name] = len(result)
                    findings.extend(result)
                except Exception as exc:  # un contrôle en échec ne masque pas les autres
                    errors[name] = redact(str(exc))[:300]
                    checks[name] = None
                with transaction(self.conn, immediate=True):
                    cur = self.conn.execute(
                        """UPDATE guardian_runs SET heartbeat_at=?,lease_expires_at=?
                           WHERE id=? AND status='running' AND lease_token=?""",
                        (epoch(), epoch() + lease_seconds, run_id, token))
                    if cur.rowcount != 1:
                        raise RuntimeError("bail Guardian perdu")
            persisted = self._persist(findings)
            critical = sum(1 for f in findings if f["severity"] == "critical")
            high = sum(1 for f in findings if f["severity"] == "high")
            status = "completed"
        except InterruptedError as exc:
            persisted, critical, high, status = 0, 0, 0, "interrupted"
            errors["scan"] = str(exc)
        except Exception as exc:
            persisted, critical, high, status = 0, 0, 0, "failed"
            errors["scan"] = redact(str(exc))[:300]
        report = {"run_id": run_id, "status": status, "trigger": trigger, "checks": checks,
                  "findings": len(findings), "new_or_updated": persisted, "critical": critical, "high": high,
                  "errors": errors, "ok": status == "completed" and critical == 0 and high == 0 and not errors,
                  "details": findings, "worker_id": worker, "finished_at": now()}
        with transaction(self.conn, immediate=True):
            self.conn.execute(
                """UPDATE guardian_runs SET status=?,finished_at=?,checks_json=?,findings=?,critical=?,
                     lease_expires_at=0,error=? WHERE id=? AND lease_token=?""",
                (status, now(), json.dumps({"checks": checks, "errors": errors}, ensure_ascii=False),
                 len(findings), critical, json.dumps(errors, ensure_ascii=False)[:500], run_id, token))
        level = "critical" if critical else "warning" if high else "info"
        log_event(self.conn, level, "guardian",
                  f"scan {status} : {len(findings)} constat(s), {critical} critique(s), {high} élevé(s)",
                  data={"run_id": run_id, "checks": checks})
        return report

    def _persist(self, findings: list[dict]) -> int:
        count = 0
        with transaction(self.conn, immediate=True):
            for f in findings:
                key = json.dumps({"code": f["code"], "component": f["component"],
                                  "evidence": f["evidence"]}, sort_keys=True, ensure_ascii=False)
                fingerprint = hashlib.sha256(key.encode()).hexdigest()
                row = self.conn.execute("SELECT id, status FROM security_findings WHERE fingerprint=?",
                                        (fingerprint,)).fetchone()
                if row:
                    self.conn.execute(
                        """UPDATE security_findings SET last_seen_at=?,occurrences=occurrences+1,
                             detail=?,severity=?,status=CASE WHEN status='resolved' THEN 'open' ELSE status END,
                             resolved_at=CASE WHEN status='resolved' THEN NULL ELSE resolved_at END
                           WHERE fingerprint=?""", (now(), f["detail"], f["severity"], fingerprint))
                else:
                    self.conn.execute(
                        """INSERT INTO security_findings(id,fingerprint,code,severity,component,detail,
                             evidence_json,status,first_seen_at,last_seen_at) VALUES(?,?,?,?,?,?,?,'open',?,?)""",
                        (f"fnd-{uuid.uuid4().hex[:12]}", fingerprint, f["code"], f["severity"],
                         f["component"], f["detail"], json.dumps(f["evidence"], ensure_ascii=False), now(), now()))
                count += 1
        return count

    def resolve(self, finding_id: str, *, resolution: str, acknowledged_by: str, confirm: str) -> dict:
        """Clôture un constat : uniquement sur action humaine documentée, jamais automatique."""
        if confirm != RESOLVE_CONFIRM or not resolution.strip() or not acknowledged_by.strip():
            raise PermissionError("revue humaine documentée requise pour clore un constat de sécurité")
        with transaction(self.conn, immediate=True):
            cur = self.conn.execute(
                """UPDATE security_findings SET status='resolved',resolved_at=?,resolution=?,acknowledged_by=?
                   WHERE id=? AND status<>'resolved'""",
                (now(), redact(resolution)[:500], acknowledged_by.strip()[:120], finding_id))
            if cur.rowcount != 1:
                raise KeyError("constat inconnu ou déjà clos")
        log_event(self.conn, "info", "guardian", f"constat clos par revue humaine : {finding_id}",
                  data={"acknowledged_by": acknowledged_by})
        return {"id": finding_id, "status": "resolved"}

    def findings(self, status: str | None = "open", limit: int = 100) -> list[dict]:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM security_findings WHERE status=? ORDER BY "
                "CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 "
                "WHEN 'low' THEN 3 ELSE 4 END, last_seen_at DESC LIMIT ?", (status, int(limit)))
        else:
            rows = self.conn.execute("SELECT * FROM security_findings ORDER BY last_seen_at DESC LIMIT ?", (int(limit),))
        out = []
        for r in rows:
            item = dict(r)
            item["evidence"] = json.loads(item.pop("evidence_json") or "{}")
            out.append(item)
        return out

    def status(self) -> dict:
        runs = [dict(r) for r in self.conn.execute(
            "SELECT id,trigger,status,started_at,finished_at,findings,critical,error FROM guardian_runs "
            "ORDER BY started_at DESC, id DESC LIMIT 10")]
        counts = {r["severity"]: r["c"] for r in self.conn.execute(
            "SELECT severity, COUNT(*) c FROM security_findings WHERE status='open' GROUP BY severity")}
        blocking = sum(counts.get(s, 0) for s in BLOCKING_SEVERITIES)
        # Un constat ouvert peut avoir été corrigé dans les faits sans être clos :
        # la clôture reste humaine. On signale donc ceux que le dernier scan
        # terminé n'a pas reproduits, pour guider la revue sans lever le blocage.
        last_done = self.conn.execute(
            "SELECT finished_at FROM guardian_runs WHERE status='completed' AND finished_at IS NOT NULL "
            "ORDER BY finished_at DESC, id DESC LIMIT 1").fetchone()
        stale = []
        if last_done:
            stale = [dict(r) for r in self.conn.execute(
                """SELECT id,code,severity,component,last_seen_at FROM security_findings
                   WHERE status='open' AND last_seen_at < ? ORDER BY severity DESC, code""",
                (last_done["finished_at"],))]
        return {"recent_runs": runs, "open_by_severity": counts, "blocking_findings": blocking,
                "ready": blocking == 0, "checks": list(self.CHECKS),
                "not_reproduced_by_last_scan": stale,
                "review_hint": ("ces constats ne sont plus reproduits : vérifier puis clore avec "
                                "`guardian --resolve ID --confirm 'REVUE HUMAINE EFFECTUEE'" if stale else None),
                "note": "Le Guardian détecte et alerte ; il ne modifie jamais permissions, politiques ni noyau."}


class GuardianScheduler:
    """Ordonnanceur periodic à bail unique, heartbeat et arrêt propre (même contrat que l'apprentissage)."""

    def __init__(self, conn: sqlite3.Connection, engine: GuardianEngine, scheduler_id: str = "default",
                 interval_seconds: float = 900.0, lease_seconds: float = 60.0,
                 heartbeat_interval: float | None = None, worker_id: str | None = None):
        if interval_seconds <= 0 or lease_seconds <= 0:
            raise ValueError("interval_seconds/lease_seconds doivent être positifs")
        self.conn = conn
        self.engine = engine
        self.scheduler_id = scheduler_id
        self.interval_seconds = float(interval_seconds)
        self.lease_seconds = float(lease_seconds)
        self.heartbeat_interval = float(heartbeat_interval if heartbeat_interval is not None
                                        else max(0.05, min(lease_seconds / 3.0, 5.0)))
        if not 0 < self.heartbeat_interval < self.lease_seconds:
            raise ValueError("heartbeat_interval doit être positif et inférieur au bail")
        self.worker_id = worker_id or new_worker_id("guardian-sched")
        row = conn.execute("PRAGMA database_list").fetchone()
        self.db_path = Path(row[2]) if row and row[2] else None

    def _claim(self) -> str | None:
        register_worker(self.conn, self.worker_id)
        t = epoch()
        token = uuid.uuid4().hex
        with transaction(self.conn, immediate=True):
            row = self.conn.execute("SELECT * FROM guardian_schedulers WHERE id=?", (self.scheduler_id,)).fetchone()
            if row is None:
                self.conn.execute(
                    """INSERT INTO guardian_schedulers(id,interval_seconds,owner_worker_id,lease_token,
                         lease_expires_at,heartbeat_at,next_run_at,state,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,0.0,'active',?,?)""",
                    (self.scheduler_id, self.interval_seconds, self.worker_id, token,
                     t + self.lease_seconds, t, now(), now()))
                return token
            if row["owner_worker_id"] and row["owner_worker_id"] != self.worker_id and float(row["lease_expires_at"]) > t:
                return None
            self.conn.execute(
                """UPDATE guardian_schedulers SET interval_seconds=?,owner_worker_id=?,lease_token=?,
                     lease_expires_at=?,heartbeat_at=?,state='active',updated_at=? WHERE id=?""",
                (self.interval_seconds, self.worker_id, token, t + self.lease_seconds, t, now(), self.scheduler_id))
            return token

    def _renew(self, token: str) -> bool:
        t = epoch()
        with transaction(self.conn, immediate=True):
            cur = self.conn.execute(
                """UPDATE guardian_schedulers SET lease_expires_at=?,heartbeat_at=?,updated_at=?
                   WHERE id=? AND owner_worker_id=? AND lease_token=? AND state='active' AND lease_expires_at > ?""",
                (t + self.lease_seconds, t, now(), self.scheduler_id, self.worker_id, token, t))
            return cur.rowcount == 1

    def _release(self, token: str) -> None:
        with transaction(self.conn, immediate=True):
            self.conn.execute(
                """UPDATE guardian_schedulers SET owner_worker_id=NULL,lease_token=NULL,lease_expires_at=0,
                     state='stopped',updated_at=? WHERE id=? AND lease_token=?""",
                (now(), self.scheduler_id, token))

    def status(self) -> dict:
        row = self.conn.execute("SELECT * FROM guardian_schedulers WHERE id=?", (self.scheduler_id,)).fetchone()
        return {"scheduler": dict(row) if row else None, "worker_id": self.worker_id,
                "guardian": self.engine.status()}

    def run(self, max_cycles: int | None = None, stop_event: threading.Event | None = None) -> dict:
        stop_event = stop_event or threading.Event()
        token = self._claim()
        if token is None:
            return {"status": "skipped", "reason": "ordonnanceur Guardian déjà actif", "scheduler_id": self.scheduler_id}
        hb_stop, lost = threading.Event(), threading.Event()

        def heartbeat():
            while not hb_stop.wait(self.heartbeat_interval):
                try:
                    if not self._renew(token):
                        lost.set(); stop_event.set(); return
                except Exception:
                    lost.set(); stop_event.set(); return

        hb = threading.Thread(target=heartbeat, name=f"guardian-sched-{self.scheduler_id}", daemon=True)
        hb.start()
        cycles, results = 0, []
        try:
            while not stop_event.is_set():
                row = self.conn.execute("SELECT next_run_at FROM guardian_schedulers WHERE id=?",
                                        (self.scheduler_id,)).fetchone()
                delay = max(0.0, float(row["next_run_at"] or 0.0) - epoch()) if row else 0.0
                if delay > 0 and stop_event.wait(min(delay, self.interval_seconds)):
                    break
                if stop_event.is_set() or lost.is_set():
                    break
                res = self.engine.scan(trigger="periodic", stop_event=stop_event,
                                       lease_seconds=self.lease_seconds, worker_id=self.worker_id)
                results.append({"run_id": res.get("run_id"), "status": res.get("status"),
                                "critical": res.get("critical", 0)})
                with transaction(self.conn, immediate=True):
                    self.conn.execute(
                        """UPDATE guardian_schedulers SET next_run_at=?,cycles=cycles+1,last_error=?,updated_at=?
                           WHERE id=? AND lease_token=?""",
                        (epoch() + self.interval_seconds, json.dumps(res.get("errors", {}), ensure_ascii=False)[:300],
                         now(), self.scheduler_id, token))
                if res.get("status") != "skipped":
                    cycles += 1
                if max_cycles is not None and cycles >= max_cycles:
                    break
                if stop_event.wait(self.interval_seconds):
                    break
        finally:
            hb_stop.set()
            hb.join(timeout=2.0)
            self._release(token)
        return {"status": "stopped", "cycles": cycles, "runs": results,
                "scheduler_id": self.scheduler_id, "lease_lost": lost.is_set(), "worker_id": self.worker_id}
