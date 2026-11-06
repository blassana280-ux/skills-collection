"""Tests fournisseurs SUPREME — catégories STRICTEMENT séparées.

- TestNoProviderMode        : local réel, AUCUN réseau, aucune clé -> indisponible honnête.
- TestProviderClientLocalStub : LOCAL RÉEL — vrai aller-retour HTTP vers un serveur stub
                              sur 127.0.0.1. Ce N'EST PAS un fournisseur IA réel : le stub
                              renvoie des réponses canoniques pour valider le client
                              (requête, auth, parsing, erreurs, fallback, budget).
- TestRouterCompleteLocalStub : routage + fallback + budget via stub local.
- TestCouncilLocalStub      : conseil produisant de vraies analyses via stub local.
- TestProviderSecurity      : résolution des clés, fichier 0600, expurgation, anti-fuite.

AUCUN test ne contacte un fournisseur IA réel (egress sandbox limité + aucune clé).
L'intégration réelle Mistral/Vide ne sera déclarée opérationnelle qu'après un appel
API réussi avec une clé fournie par l'utilisateur (hors dépôt).
"""
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from supreme import providers as P
from supreme.council import Council, CouncilConfig
from supreme.router import ModelRouter, ModelSpec, Provider
import supreme.router as router_mod
from supreme.orchestrator import OmniBrainCore
from tests._supreme_util import SupremeTestCase

PROVIDER_ENV_KEYS = ["MISTRAL_API_KEY", "GROQ_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY",
                     "OPENROUTER_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_HOST",
                     "SUPREME_OPENAI_COMPAT_API_KEY", "SUPREME_OPENAI_COMPAT_BASE_URL"]

STUB_CONTENT = '{"answer":"reponse-A","evidence":["preuve1"],"sources":["src1"],"confidence":0.9}'


def _clean_env():
    """Retire toute clé fournisseur de l'environnement (isolation des tests)."""
    return {k: v for k, v in os.environ.items() if k not in PROVIDER_ENV_KEYS}


class _StubHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.server.requests.append({"method": "GET", "path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}})
        self._send(200, {"data": [{"id": "stub-model"}]})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        self.server.requests.append({"method": "POST", "path": self.path,
                                     "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body})
        mode = self.server.mode
        if mode == "401":
            return self._send(401, {"error": {"message": "invalid key"}})
        if mode == "429":
            return self._send(429, {"error": {"message": "rate limited"}})
        if mode == "500":
            return self._send(500, {"error": {"message": "server error"}})
        if mode == "badjson":
            self.send_response(200)
            self.send_header("Content-Length", "7")
            self.end_headers()
            self.wfile.write(b"notjson")
            return
        content = self.server.content
        usage = {"prompt_tokens": 10, "completion_tokens": 20}
        if self.path.endswith("/chat/completions"):
            self._send(200, {"choices": [{"message": {"content": content}}], "usage": usage})
        elif self.path.endswith("/messages"):
            self._send(200, {"content": [{"type": "text", "text": content}],
                             "usage": {"input_tokens": 10, "output_tokens": 20}})
        elif ":generateContent" in self.path:
            self._send(200, {"candidates": [{"content": {"parts": [{"text": content}]}}],
                             "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20}})
        elif self.path.endswith("/api/chat"):
            self._send(200, {"message": {"content": content}, "prompt_eval_count": 10, "eval_count": 20})
        else:
            self._send(404, {"error": "unknown path"})


def start_stub(mode="ok", content=STUB_CONTENT):
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    server.mode = mode
    server.content = content
    server.requests = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    return server, thread, base


class TestNoProviderMode(unittest.TestCase):
    """Local réel, sans réseau ni clé : tout doit être honnêtement indisponible."""

    def test_no_provider_configured(self):
        with mock.patch.dict(os.environ, _clean_env(), clear=True):
            conf = P.configured_providers()
            self.assertTrue(all(not c["configured"] for c in conf))

    def test_router_complete_unavailable(self):
        with mock.patch.dict(os.environ, _clean_env(), clear=True):
            r = ModelRouter(allow_network=False)
            res = r.complete({"capabilities": ["general"]}, [{"role": "user", "content": "x"}])
            self.assertFalse(res["ok"])
            self.assertEqual(res["model"], None)
            self.assertIn("aucun fournisseur", res["error"])

    def test_council_unavailable(self):
        with mock.patch.dict(os.environ, _clean_env(), clear=True):
            r = ModelRouter(allow_network=False)
            res = Council(r).deliberate("problème complexe")
            self.assertEqual(res["status"], "unavailable")

    def test_client_network_disabled(self):
        c = P.ProviderClient(allow_network=False)
        res = c.complete(provider="mistral", model="m", messages=[], base_url="http://x",
                         api_key="k")
        self.assertFalse(res.ok)
        self.assertIn("réseau désactivé", res.error)


class TestProviderClientLocalStub(unittest.TestCase):
    """LOCAL RÉEL : vrai HTTP vers un stub. Valide le client, PAS un fournisseur IA réel."""

    def setUp(self):
        self.server, self.thread, self.base = start_stub()
        self.client = P.ProviderClient(timeout=10, allow_network=True)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_openai_request_and_parse(self):
        res = self.client.complete(provider="mistral", model="mistral-small-latest",
                                   messages=[{"role": "system", "content": "sys"},
                                             {"role": "user", "content": "bonjour"}],
                                   base_url=self.base, kind="openai", api_key="stub-secret-123")
        self.assertTrue(res.ok, res.error)
        self.assertEqual(res.usage["input_tokens"], 10)
        self.assertEqual(res.usage["output_tokens"], 20)
        req = self.server.requests[-1]
        self.assertEqual(req["path"], "/chat/completions")
        self.assertEqual(req["headers"].get("authorization"), "Bearer stub-secret-123")
        self.assertEqual(req["body"]["model"], "mistral-small-latest")
        self.assertIn("reponse-A", res.text)

    def test_anthropic_request_and_parse(self):
        res = self.client.complete(provider="anthropic", model="claude", messages=[
            {"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}],
            base_url=self.base, kind="anthropic", api_key="stub-secret-123")
        self.assertTrue(res.ok, res.error)
        req = self.server.requests[-1]
        self.assertEqual(req["path"], "/messages")
        self.assertEqual(req["headers"].get("x-api-key"), "stub-secret-123")
        self.assertEqual(req["body"]["system"], "sys")
        self.assertEqual(res.usage["output_tokens"], 20)

    def test_gemini_request_and_parse(self):
        res = self.client.complete(provider="gemini", model="gemini-1.5-flash",
                                   messages=[{"role": "user", "content": "hi"}],
                                   base_url=self.base, kind="gemini", api_key="stub-secret-123")
        self.assertTrue(res.ok, res.error)
        req = self.server.requests[-1]
        self.assertIn(":generateContent", req["path"])
        self.assertEqual(req["headers"].get("x-goog-api-key"), "stub-secret-123")
        # la clé ne doit JAMAIS être dans l'URL
        self.assertNotIn("stub-secret-123", req["path"])
        self.assertEqual(res.usage["input_tokens"], 10)

    def test_ollama_request_and_parse(self):
        res = self.client.complete(provider="ollama", model="llama3.1",
                                   messages=[{"role": "user", "content": "hi"}],
                                   base_url=self.base, kind="ollama")
        self.assertTrue(res.ok, res.error)
        self.assertEqual(self.server.requests[-1]["path"], "/api/chat")
        self.assertEqual(res.usage["output_tokens"], 20)

    def test_http_401_redacts_key(self):
        self.server.mode = "401"
        res = self.client.complete(provider="mistral", model="m", messages=[{"role": "user", "content": "x"}],
                                   base_url=self.base, kind="openai", api_key="stub-secret-123")
        self.assertFalse(res.ok)
        self.assertEqual(res.http_status, 401)
        self.assertNotIn("stub-secret-123", res.error)
        self.assertIn("401", res.error)

    def test_http_429_and_500(self):
        for code in ("429", "500"):
            self.server.mode = code
            res = self.client.complete(provider="x", model="m", messages=[{"role": "user", "content": "x"}],
                                       base_url=self.base, kind="openai", api_key="k")
            self.assertFalse(res.ok)
            self.assertEqual(res.http_status, int(code))

    def test_bad_json(self):
        self.server.mode = "badjson"
        res = self.client.complete(provider="x", model="m", messages=[{"role": "user", "content": "x"}],
                                   base_url=self.base, kind="openai", api_key="k")
        self.assertFalse(res.ok)
        self.assertIn("non JSON", res.error)

    def test_unreachable_host(self):
        res = self.client.complete(provider="x", model="m", messages=[{"role": "user", "content": "x"}],
                                   base_url="http://127.0.0.1:1", kind="openai", api_key="k")
        self.assertFalse(res.ok)
        self.assertIn("injoignable", res.error)


class TestRouterCompleteLocalStub(unittest.TestCase):
    """Routage + fallback + budget via stub local (local réel)."""

    def setUp(self):
        self.srv_ok, self.th_ok, self.base_ok = start_stub()
        self.srv_bad, self.th_bad, self.base_bad = start_stub(mode="500")

    def tearDown(self):
        for s in (self.srv_ok, self.srv_bad):
            s.shutdown()
            s.server_close()

    def _router(self, providers, budget=None):
        return ModelRouter(providers=providers, budget=budget, allow_network=True,
                           client=P.ProviderClient(timeout=10, allow_network=True))

    def test_complete_success_and_cost(self):
        p = Provider("mistral", "STUB_KEY", self.base_ok, [
            ModelSpec("mistral", "mistral-small-latest", ("general",), 0.001, 0.002, 8000, True, True)],
            kind="openai", priority=1)
        with mock.patch.dict(os.environ, {**_clean_env(), "STUB_KEY": "stub-secret-123"}, clear=True):
            r = self._router([p])
            res = r.complete({"capabilities": ["general"], "max_cost_usd": 1.0},
                             [{"role": "user", "content": "x"}], mission_id="mis-test")
        self.assertTrue(res["ok"], res["error"])
        self.assertEqual(res["provider"], "mistral")
        # coût = (0.001*10 + 0.002*20)/1000 = 0.00005
        self.assertAlmostEqual(res["cost_usd"], 0.00005, places=6)

    def test_fallback_first_fails_second_ok(self):
        bad = Provider("groq", "STUB_KEY_BAD", self.base_bad, [
            ModelSpec("groq", "llama-3.1-8b-instant", ("general",), 0.0001, 0.0001, 8000, True, True)],
            kind="openai", priority=1)
        good = Provider("mistral", "STUB_KEY_OK", self.base_ok, [
            ModelSpec("mistral", "mistral-small-latest", ("general",), 0.001, 0.001, 8000, True, True)],
            kind="openai", priority=2)
        with mock.patch.dict(os.environ, {**_clean_env(), "STUB_KEY_BAD": "k1", "STUB_KEY_OK": "k2"}, clear=True):
            r = self._router([bad, good])
            res = r.complete({"capabilities": ["general"], "max_cost_usd": 1.0},
                             [{"role": "user", "content": "x"}])
        self.assertTrue(res["ok"], res["error"])
        self.assertEqual(res["provider"], "mistral")  # fallback vers le second
        self.assertGreaterEqual(len(res["attempts"]), 2)
        self.assertFalse(res["attempts"][0]["ok"])

    def test_mistral_priority(self):
        # Deux fournisseurs à capacité/coût identiques : Mistral (priority 1) doit gagner.
        m = Provider("mistral", "STUB_KEY_M", self.base_ok, [
            ModelSpec("mistral", "mistral-small-latest", ("general",), 0.001, 0.001, 8000, True, True)],
            kind="openai", priority=1)
        g = Provider("groq", "STUB_KEY_G", self.base_ok, [
            ModelSpec("groq", "llama-3.1-8b-instant", ("general",), 0.001, 0.001, 8000, True, True)],
            kind="openai", priority=2)
        with mock.patch.dict(os.environ, {**_clean_env(), "STUB_KEY_M": "k1", "STUB_KEY_G": "k2"}, clear=True):
            r = self._router([g, m])
            route = r.route({"capabilities": ["general"], "max_cost_usd": 1.0})
        self.assertTrue(route["available"])
        self.assertEqual(route["model"], "mistral/mistral-small-latest")


class TestCouncilLocalStub(unittest.TestCase):
    """Conseil : vraies analyses indépendantes via stub local, décision par preuves."""

    def setUp(self):
        self.server, self.thread, self.base = start_stub(content=STUB_CONTENT)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_council_produces_real_analyses(self):
        p = Provider("mistral", "STUB_KEY", self.base, [
            ModelSpec("mistral", "mistral-small-latest", ("general",), 0.001, 0.001, 8000, True, True)],
            kind="openai", priority=1)
        with mock.patch.dict(os.environ, {**_clean_env(), "STUB_KEY": "stub-secret-123"}, clear=True):
            r = ModelRouter(providers=[p], allow_network=True,
                            client=P.ProviderClient(timeout=10, allow_network=True))
            res = Council(r, CouncilConfig(max_models=1)).deliberate(
                "quel choix ?", evidence=[{"task_id": "preuve1", "agent_id": "a1", "output": {"ok": True}}])
        self.assertEqual(res["status"], "decided")
        self.assertEqual(res["decision"]["answer"], "reponse-A")
        self.assertTrue(res["verified"])  # preuve présente
        # un vrai appel HTTP a été fait vers le stub
        self.assertTrue(any(req["method"] == "POST" for req in self.server.requests))


class TestProviderSecurity(unittest.TestCase):
    """Sécurité des secrets : résolution, fichier 0600, expurgation, anti-fuite."""

    def test_resolve_key_from_env(self):
        with mock.patch.dict(os.environ, {**_clean_env(), "MISTRAL_API_KEY": "env-secret"}, clear=True):
            self.assertEqual(P.resolve_key("MISTRAL_API_KEY", "mistral"), "env-secret")

    def test_resolve_key_absent(self):
        with mock.patch.dict(os.environ, _clean_env(), clear=True):
            self.assertEqual(P.resolve_key("MISTRAL_API_KEY", "mistral"), "")

    def test_redact(self):
        self.assertEqual(P.redact("erreur avec secret-abc-123 dedans", "secret-abc-123"),
                         "erreur avec [REDACTED] dedans")

    def test_secrets_template_empty_and_0600(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(P, "VAR_DIR", Path(tmp)):
                path = P.write_secrets_template()
                data = json.loads(Path(path).read_text())
                self.assertTrue(all(v == "" for v in data.values()))  # aucune clé réelle
                self.assertEqual(Path(path).stat().st_mode & 0o777, 0o600)

    def test_no_hardcoded_secret_in_source(self):
        """Aucune clé API en dur dans le code source SUPREME (anti-fuite)."""
        import re
        root = Path(__file__).resolve().parent.parent / "supreme"
        # Motifs de clés courantes (chaînes longues assignées à une variable de clé).
        pattern = re.compile(r"(?i)(api_key|apikey|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]")
        offenders = []
        for py in root.rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            for m in pattern.finditer(text):
                snippet = m.group(0)
                # ignore les noms de variables d'environnement et les placeholders vides
                if "environ" in snippet or "env_var" in snippet:
                    continue
                offenders.append(f"{py.name}: {snippet[:40]}")
        self.assertEqual(offenders, [], f"secrets potentiels en dur : {offenders}")


class TestLLMMissionLocalStub(SupremeTestCase):
    """BOUT-EN-BOUT LOCAL RÉEL : une mission LLM exécutée par un agent via un stub HTTP.

    Prouve que les agents LLM (960) peuvent réellement s'exécuter quand un fournisseur
    est configuré. Ce n'est PAS un fournisseur IA réel (stub local). Sans clé -> bloqué.
    """

    def setUp(self):
        super().setUp()
        self.server, self.thread, self.base = start_stub()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def test_llm_mission_executes_via_stub(self):
        stub = Provider("mistral", "STUB_KEY", self.base, [
            ModelSpec("mistral", "mistral-small-latest", ("general",), 0.001, 0.001, 8000, True, True)],
            kind="openai", priority=1)
        agent = self.llm_agent("D02")
        with mock.patch.object(router_mod, "DEFAULT_PROVIDERS", [stub]), \
             mock.patch.dict(os.environ, {**_clean_env(), "STUB_KEY": "stub-secret-123"}, clear=True):
            core = OmniBrainCore(conn=self.conn)
            sub = core.submit({"objective": "Analyser cette demande",
                               "tasks": [{"agent_id": agent["id"], "input": {"question": "quoi ?"}}]})
            res = core.run(sub["mission_id"])
            st = core.status(sub["mission_id"])
        self.assertEqual(res["state"], "completed", res)
        self.assertGreater(res["cost_usd"], 0.0)  # coût réel enregistré
        llm_task = next(t for t in st["tasks"] if not t["tool"])
        self.assertEqual(llm_task["state"], "done")
        self.assertIn("reponse-A", llm_task["result_json"] or "")
        # un vrai appel HTTP a été fait
        self.assertTrue(any(r["method"] == "POST" for r in self.server.requests))

    def test_llm_mission_blocked_without_provider(self):
        agent = self.llm_agent("D02")
        with mock.patch.dict(os.environ, _clean_env(), clear=True):
            core = OmniBrainCore(conn=self.conn, max_workers=2)
            core.router.allow_network = False
            sub = core.submit({"objective": "Analyser",
                               "tasks": [{"agent_id": agent["id"], "input": {"q": "x"}}]})
            res = core.run(sub["mission_id"])
        self.assertIn(res["state"], ("failed", "partial"))
        st = core.status(sub["mission_id"])
        llm_task = next(t for t in st["tasks"] if not t["tool"])
        self.assertEqual(llm_task["state"], "blocked")


if __name__ == "__main__":
    unittest.main()
