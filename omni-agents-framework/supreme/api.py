"""API Gateway SUPREME + tableau de bord — http.server stdlib, auth par jeton,
rôles, données 100% réelles. Bind 0.0.0.0 pour le preview. Aucun secret exposé.
"""
from __future__ import annotations

import json
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import DASHBOARD_DIR, VAR_DIR, ensure_dirs
from .evaluation import EvaluationEngine
from .orchestrator import OmniBrainCore
from .observability import ObservabilityEngine
from .reporting import ReportingEngine
from .skills_registry import SkillRegistry
from .backup import BackupManager
from .tools import TOOLS


def bootstrap(evaluate: bool = True) -> OmniBrainCore:
    core = OmniBrainCore()
    core.registry.sync_catalog()
    core.recover()
    if evaluate:
        registered = core.registry.status_counts().get("registered", 0)
        if registered:
            EvaluationEngine(core.conn, core.registry).evaluate_all(activate=True)
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
            return p.read_text().strip()
        tok = secrets.token_urlsafe(24)
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
                    return self._send(200, {"status": "ok", "version": "1.0.0"})
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
                if path.startswith("/api/agents/"):
                    a = c["registry"].get(path.split("/")[-1])
                    return self._send(200 if a else 404, a or {"error": "agent inconnu"})
                if path == "/api/divisions":
                    return self._send(200, {"divisions": c["registry"].divisions_summary()})
                if path == "/api/missions":
                    return self._send(200, {"missions": core.list_missions()})
                if path.startswith("/api/missions/"):
                    return self._send(200, core.status(path.split("/")[-1]))
                if path == "/api/models":
                    c["router"].detect()
                    return self._send(200, c["router"].status())
                if path == "/api/quotas":
                    return self._send(200, {"totals": c["budget"].totals(),
                                            "quotas": [dict(r) for r in c["conn"].execute("SELECT * FROM quotas")]})
                if path == "/api/memory/search":
                    return self._send(200, c["memory"].search("omnibrain-core", query=qs.get("q", [""])[0],
                                                              level=qs.get("level", [None])[0], limit=int(qs.get("limit", ["20"])[0])))
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
    print(f"Jeton admin : {state.admin_token}")
    print(f"Lecture anonyme : {'oui' if state.anon_read else 'non'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
