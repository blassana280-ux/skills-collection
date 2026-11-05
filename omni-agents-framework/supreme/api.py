"""API Gateway SUPREME + tableau de bord — http.server stdlib, auth par jeton,
rôles, données 100% réelles. Bind 0.0.0.0 pour le preview. Aucun secret exposé.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from .config import DASHBOARD_DIR, VAR_DIR, ensure_dirs
from .evaluation import EvaluationEngine
from .leases import LeaseLostError
from .orchestrator import OmniBrainCore
from .observability import ObservabilityEngine
from .reporting import ReportingEngine
from .skills_registry import SkillRegistry
from .backup import BackupManager
from .tools import TOOLS

# ---------------------------------------------------------------- journal d'accès
# Journal d'accès HTTP expurgé : aucun jeton, en-tête ni corps n'est jamais écrit.
# Le paramètre d'URL ?token=… est remplacé par REDACTED. Fichier en 0600, gitignoré.
_access_lock = threading.Lock()


def _redact_path(path: str) -> str:
    u = urlparse(path)
    qs = parse_qs(u.query, keep_blank_values=True)
    if "token" in qs:
        qs["token"] = ["REDACTED"]
    q = urlencode(qs, doseq=True)
    return u.path + ("?" + q if q else "")


def _access_log(entry: dict) -> None:
    try:
        ensure_dirs()
        p = VAR_DIR / "access.log"
        line = json.dumps(entry, ensure_ascii=False) + "\n"
        with _access_lock:
            new = not p.exists()
            with open(p, "a", encoding="utf-8") as f:
                f.write(line)
            if new:
                try:
                    os.chmod(p, 0o600)
                except OSError:
                    pass
    except Exception:
        pass  # la journalisation ne doit jamais faire échouer une requête


def rotate_token() -> dict:
    """Génère un nouveau jeton aléatoire sûr (256 bits), l'écrit en 0600 (atomique).

    Ne renvoie JAMAIS le jeton en clair — uniquement des métadonnées non sensibles
    (chemin, longueur, empreinte SHA-256 tronquée). L'ancien jeton est révoqué sur
    disque ; redémarrer le serveur pour le révoquer aussi en mémoire.
    """
    ensure_dirs()
    p = VAR_DIR / "api_token.txt"
    tok = secrets.token_urlsafe(32)
    tmp = p.with_name("api_token.txt.tmp")
    tmp.write_text(tok)
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)
    return {
        "path": str(p),
        "length": len(tok),
        "permissions": "0600",
        "fingerprint_sha256_12": hashlib.sha256(tok.encode()).hexdigest()[:12],
        "env_override": bool(os.environ.get("SUPREME_API_TOKEN")),
        "note": "Redémarrer le serveur pour révoquer l'ancien jeton en mémoire.",
    }


def bootstrap(evaluate: bool = True) -> OmniBrainCore:
    core = OmniBrainCore()
    core.registry.sync_catalog()
    core.recover()
    if evaluate:
        registered = core.registry.status_counts().get("registered", 0)
        if registered:
            EvaluationEngine(core.conn, core.registry, router=core.router).evaluate_all(activate=True)
    return core


class APIState:
    def __init__(self, core: OmniBrainCore):
        self.core = core
        self.obs = ObservabilityEngine(core.conn, core.registry, core.budget, core.router)
        self.reporting = ReportingEngine(core.conn, core.registry, self.obs)
        self.skills = SkillRegistry()
        self.backup = BackupManager()
        self.admin_token = os.environ.get("SUPREME_API_TOKEN") or self._load_or_create_token()
        self.anon_read = os.environ.get("SUPREME_ALLOW_ANON_READ", "0") == "1"

    def _load_or_create_token(self) -> str:
        ensure_dirs()
        p = VAR_DIR / "api_token.txt"
        if p.is_file():
            try:
                os.chmod(p, 0o600)  # renforce les permissions à chaque chargement
            except OSError:
                pass
            return p.read_text().strip()
        tok = secrets.token_urlsafe(32)
        p.write_text(tok)
        try:
            os.chmod(p, 0o600)
        except OSError:
            pass
        return tok


def make_handler(state: APIState):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def log_request(self, code="-", size="-"):
            # Journal d'accès expurgé (méthode, chemin sans jeton, statut, IP).
            _access_log({
                "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "ip": self.client_address[0] if self.client_address else "-",
                "method": self.command,
                "path": _redact_path(self.path),
                "status": int(code) if str(code).isdigit() else code,
            })

        def _send(self, code: int, data, content_type="application/json"):
            body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", content_type + ("; charset=utf-8" if "json" in content_type or "html" in content_type else ""))
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _auth(self, write: bool = False) -> str | None:
            tok = self.headers.get("X-API-Token") or ""
            auth = self.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                tok = auth[7:]
            if not tok:
                tok = parse_qs(urlparse(self.path).query).get("token", [""])[0]
            if tok and secrets.compare_digest(tok, state.admin_token):
                return "admin"
            if not write and state.anon_read:
                return "viewer"
            return None

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length", 0))
            if not length:
                return {}
            try:
                return json.loads(self.rfile.read(length))
            except json.JSONDecodeError:
                return {}

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            qs = parse_qs(parsed.query)
            if path == "/":
                html = (DASHBOARD_DIR / "index.html").read_bytes()
                return self._send(200, html, "text/html")
            role = self._auth(write=False)
            if role is None:
                return self._send(401, {"error": "authentification requise"})
            core = state.core
            c = core._c()
            obs = ObservabilityEngine(c["conn"], c["registry"], c["budget"], c["router"])
            reporting = ReportingEngine(c["conn"], c["registry"], obs)
            try:
                if path == "/api/health":
                    from . import SUPREME_VERSION
                    return self._send(200, {"status": "ok", "version": SUPREME_VERSION})
                if path == "/api/status":
                    return self._send(200, obs.system_status())
                if path == "/api/kpis":
                    return self._send(200, obs.kpis())
                if path == "/api/agents":
                    agents = c["registry"].list(division=qs.get("division", [None])[0],
                                                kind=qs.get("kind", [None])[0], status=qs.get("status", [None])[0])
                    return self._send(200, {"count": len(agents), "agents": [
                        {k: a[k] for k in ("id", "name", "division", "kind", "status", "version")} |
                        {"objective": a["profile"]["objective"], "risk": a["profile"]["risk_level"]} for a in agents]})
                if path.startswith("/api/agents/") and path.endswith("/history"):
                    aid = path.split("/")[3]
                    a = c["registry"].get(aid)
                    if a is None:
                        return self._send(404, {"error": "agent inconnu"})
                    tasks = [dict(r) for r in c["conn"].execute(
                        "SELECT id, mission_id, tool, state, error, created_at, updated_at FROM tasks "
                        "WHERE agent_id=? ORDER BY created_at DESC LIMIT 50", (aid,))]
                    m = c["conn"].execute(
                        "SELECT AVG(value) s, COUNT(*) n FROM metrics WHERE name='task_success' AND agent_id=?",
                        (aid,)).fetchone()
                    evals = [dict(r) for r in c["conn"].execute(
                        "SELECT eval_id, mode, passed, deferred, evidence, at FROM eval_runs "
                        "WHERE agent_id=? ORDER BY id DESC LIMIT 7", (aid,))]
                    return self._send(200, {
                        "agent_id": aid, "status": a["status"],
                        "missions_history": tasks,
                        "kpis": {"task_success_rate": m["s"], "tasks_measured": m["n"]},
                        "latest_evaluations": evals,
                        "supervision": f"chef de division {a['profile']['division']} + télémétrie centrale"})
                if path.startswith("/api/agents/"):
                    a = c["registry"].get(path.split("/")[-1])
                    return self._send(200 if a else 404, a or {"error": "agent inconnu"})
                if path == "/api/divisions":
                    return self._send(200, {"divisions": c["registry"].divisions_summary()})
                if path == "/api/missions":
                    return self._send(200, {"missions": core.list_missions()})
                if path.startswith("/api/missions/"):
                    return self._send(200, core.status(path.split("/")[3]))
                if path.startswith("/api/missions/"):
                    return self._send(200, core.status(path.split("/")[-1]))
                if path == "/api/models":
                    c["router"].detect()
                    return self._send(200, c["router"].status())
                if path == "/api/providers":
                    from .providers import configured_providers
                    c["router"].detect()
                    conf = configured_providers()
                    # Statut vérifié (si check_availability déjà lancé) par fournisseur.
                    verified = {p.name: p.status for p in c["router"].providers}
                    for item in conf:
                        item["verified_status"] = verified.get(item["name"], "not_checked")
                    return self._send(200, {
                        "providers": conf,
                        "configured_count": sum(1 for x in conf if x["configured"]),
                        "priority_order": [x["name"] for x in sorted(conf, key=lambda y: y["priority"])],
                        "secure_config": "Clés via variables d'environnement ou var/supreme/providers.json (0600, gitignoré). Jamais dans le dépôt.",
                        "note": "Un fournisseur configuré n'est opérationnel qu'après un appel API réel réussi.",
                    })
                if path == "/api/quotas":
                    return self._send(200, {"totals": c["budget"].totals(),
                                            "quotas": [dict(r) for r in c["conn"].execute("SELECT * FROM quotas")]})
                if path == "/api/memory/search":
                    return self._send(200, c["memory"].search("omnibrain-core", query=qs.get("q", [""])[0],
                                                              level=qs.get("level", [None])[0], limit=int(qs.get("limit", ["20"])[0]),
                                                              mode=qs.get("mode", ["auto"])[0]))
                if path == "/api/approvals":
                    return self._send(200, {"pending": c["policy"].pending_approvals()})
                if path == "/api/tools":
                    return self._send(200, {"tools": [{"name": t.name, "description": t.description, "risk": t.risk,
                                                       "version": t.version, "executable": True} for t in TOOLS.values()]})
                if path == "/api/skills":
                    return self._send(200, state.skills.stats() | {"sample": state.skills.list(limit=20)})
                if path == "/api/bus":
                    return self._send(200, c["bus"].stats())
                if path == "/api/reports/global":
                    return self._send(200, reporting.global_report())
                if path == "/api/backups":
                    return self._send(200, {"backups": state.backup.list_backups()})
                if path == "/api/alerts":
                    from .security import redact
                    rows = c["conn"].execute(
                        "SELECT at,level,component,mission_id,message FROM events "
                        "WHERE level IN ('warning','error','critical') ORDER BY id DESC LIMIT 50").fetchall()
                    alerts = [{"at": c["at"], "level": c["level"], "component": c["component"],
                               "mission_id": c["mission_id"], "message": redact(c["message"])} for c in rows]
                    return self._send(200, {"alerts": alerts, "count": len(alerts)})
                if path == "/api/security":
                    from .security import redact
                    logp = VAR_DIR / "access.log"
                    tail = []
                    if logp.is_file():
                        lines = logp.read_text(encoding="utf-8", errors="ignore").splitlines()[-30:]
                        tail = [redact(ln) for ln in lines]
                    tokp = VAR_DIR / "api_token.txt"
                    perms = oct(tokp.stat().st_mode & 0o777) if tokp.is_file() else "absent"
                    return self._send(200, {
                        "access_log_tail": tail,
                        "token_file_permissions": perms,
                        "secrets_file_present": (VAR_DIR / "providers.json").is_file(),
                        "anon_read": state.anon_read,
                        "posture": "moindre privilège, anti-injection, ACL bus/mémoire, rédaction secrets, "
                                   "actions protégées sur approbation humaine, journal d'accès expurgé",
                        "note": "Aucun secret n'est exposé par cet endpoint.",
                    })
                if path.startswith("/api/trace/"):
                    return self._send(200, obs.mission_trace(path.split("/")[-1]))
                return self._send(404, {"error": "route inconnue"})
            except KeyError as e:
                return self._send(404, {"error": str(e)})
            except Exception as e:
                return self._send(500, {"error": str(e)})

        def do_POST(self):
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")
            role = self._auth(write=True)
            if role != "admin":
                return self._send(401, {"error": "jeton admin requis pour les écritures"})
            body = self._body()
            core = state.core
            c = core._c()
            try:
                if path == "/api/missions":
                    from .security import validate_mission_input
                    errs = validate_mission_input(body)
                    if errs:
                        return self._send(400, {"errors": errs})
                    sub = core.submit(body)
                    if body.get("run", True):
                        result = core.run(sub["mission_id"])
                        return self._send(201, {"submitted": sub, "result": result})
                    return self._send(201, sub)
                if path.startswith("/api/missions/") and path.endswith("/run"):
                    return self._send(200, core.run(path.split("/")[3]))
                if path.startswith("/api/missions/") and path.endswith("/cancel"):
                    return self._send(200, core.cancel(path.split("/")[3]))
                if path.startswith("/api/approvals/") and path.endswith("/decide"):
                    return self._send(200, c["policy"].decide(path.split("/")[3], bool(body.get("approved")), body.get("decided_by", "Lassana")))
                if path == "/api/approvals":
                    aid = c["policy"].request_approval(body.get("action", "deploy"), body.get("requested_by", "api"), body.get("context", {}))
                    return self._send(201, {"approval_id": aid})
                if path == "/api/backup":
                    return self._send(201, state.backup.backup(body.get("label", "")))
                if path == "/api/providers/check":
                    return self._send(200, {"results": c["router"].check_availability()})
                return self._send(404, {"error": "route inconnue"})
            except PermissionError as e:
                return self._send(403, {"error": str(e)})
            except LeaseLostError as e:
                return self._send(409, {"error": str(e)})
            except (KeyError, ValueError) as e:
                return self._send(400, {"error": str(e)})
            except Exception as e:
                return self._send(500, {"error": str(e)})

    return Handler


def serve(host: str = "0.0.0.0", port: int = 8765, evaluate: bool = True) -> tuple[ThreadingHTTPServer, APIState]:
    core = bootstrap(evaluate=evaluate)
    state = APIState(core)
    server = ThreadingHTTPServer((host, port), make_handler(state))
    return server, state


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--no-eval", action="store_true")
    args = ap.parse_args()
    server, state = serve(args.host, args.port, evaluate=not args.no_eval)
    print(f"OMNIBRAIN SUPREME API sur http://{args.host}:{args.port}")
    print(f"Jeton admin : stocké dans {VAR_DIR / 'api_token.txt'} (0600, jamais affiché)")
    print(f"Lecture anonyme : {'oui' if state.anon_read else 'non'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
