"""Tests API : auth, lecture anonyme, écritures protégées, données réelles, sécurité."""
import json
import threading
import urllib.request
import urllib.error
from pathlib import Path
from unittest import mock

import supreme.api as api_mod
from supreme.api import APIState, make_handler
from http.server import ThreadingHTTPServer
from tests._supreme_util import SupremeTestCase


class TestAPI(SupremeTestCase):
    def setUp(self):
        super().setUp()
        # Isole le stockage (jeton + journal d'accès) dans un répertoire temporaire.
        self._var = Path(self._tmp.name) / "var"
        self._var.mkdir(parents=True, exist_ok=True)
        self._var_patch = mock.patch.object(api_mod, "VAR_DIR", self._var)
        self._var_patch.start()
        self.state = APIState(self.core)
        self.state.admin_token = "test-token"
        self.state.anon_read = True
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.state))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self._var_patch.stop()
        super().tearDown()

    def _get(self, path, token=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}")
        if token:
            req.add_header("X-API-Token", token)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def _post(self, path, body, token=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}",
                                     data=json.dumps(body).encode(), method="POST")
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("X-API-Token", token)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_health(self):
        code, data = self._get("/api/health")
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "ok")

    def test_anon_read_status(self):
        code, data = self._get("/api/status")
        self.assertEqual(code, 200)
        self.assertEqual(sum(data["agents"].values()), 1020)

    def test_write_requires_token(self):
        code, data = self._post("/api/missions", {"objective": "test"})
        self.assertEqual(code, 401)

    def test_submit_mission_with_token(self):
        code, data = self._post("/api/missions", {"objective": "Vérifier Python et JSON"}, token="test-token")
        self.assertEqual(code, 201)
        self.assertEqual(data["result"]["state"], "completed")

    def test_agents_endpoint_real(self):
        code, data = self._get("/api/agents?division=D02&kind=specialist")
        self.assertEqual(code, 200)
        self.assertEqual(data["count"], 50)

    def test_models_honest(self):
        code, data = self._get("/api/models")
        self.assertEqual(code, 200)
        self.assertEqual(data["available_count"], 0)

    def test_invalid_mission_rejected(self):
        code, data = self._post("/api/missions", {"objective": ""}, token="test-token")
        self.assertEqual(code, 400)

    def test_dashboard_served(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/")
        with urllib.request.urlopen(req, timeout=10) as r:
            self.assertEqual(r.status, 200)
            self.assertIn(b"OMNIBRAIN", r.read())


if __name__ == "__main__":
    import unittest
    unittest.main()


class TestApiConcurrency(TestAPI):
    def test_concurrent_reads_and_mission(self):
        import concurrent.futures

        def get_status(_):
            code, data = self._get("/api/status")
            return code

        def submit_mission(i):
            code, data = self._post("/api/missions",
                                    {"objective": f"Vérifier Python JSON secrets {i}"},
                                    token="test-token")
            return code, data.get("result", {}).get("state")

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
            reads = list(ex.map(get_status, range(10)))
            missions = list(ex.map(submit_mission, range(4)))
        self.assertTrue(all(c == 200 for c in reads), reads)
        self.assertTrue(all(c == 201 and s == "completed" for c, s in missions), missions)


class TestApiSecurity(TestAPI):
    def test_access_log_written_and_token_redacted(self):
        secret = "SUPERSECRETVALUE123"
        # GET avec jeton dans l'URL (lecture anonyme) + POST avec jeton en en-tête.
        self._get(f"/api/status?token={secret}")
        self._post("/api/missions", {"objective": "Vérifier Python JSON"}, token="test-token")
        log = (self._var / "access.log").read_text(encoding="utf-8")
        self.assertIn("/api/status", log)
        self.assertIn("/api/missions", log)
        self.assertIn("REDACTED", log)
        # Aucun secret ne doit jamais apparaître dans le journal.
        self.assertNotIn(secret, log)
        self.assertNotIn("test-token", log)
        # Chaque ligne est un JSON valide avec les champs attendus.
        for line in log.strip().splitlines():
            entry = json.loads(line)
            self.assertIn("method", entry)
            self.assertIn("path", entry)
            self.assertIn("status", entry)
            self.assertNotIn("token", entry)  # pas de champ jeton

    def test_access_log_permissions(self):
        self._get("/api/health")
        p = self._var / "access.log"
        self.assertTrue(p.exists())
        self.assertEqual(p.stat().st_mode & 0o777, 0o600)

    def test_rotate_token_returns_no_secret(self):
        meta = api_mod.rotate_token()
        # Le jeton en clair ne doit JAMAIS être renvoyé.
        tok = (self._var / "api_token.txt").read_text().strip()
        self.assertNotIn(tok, json.dumps(meta))
        self.assertEqual(meta["length"], len(tok))
        self.assertEqual(meta["permissions"], "0600")
        self.assertEqual(len(meta["fingerprint_sha256_12"]), 12)
        self.assertEqual((self._var / "api_token.txt").stat().st_mode & 0o777, 0o600)

    def test_rotate_token_changes_and_revokes_old(self):
        before = (self._var / "api_token.txt").read_text().strip()
        m1 = api_mod.rotate_token()
        after = (self._var / "api_token.txt").read_text().strip()
        self.assertNotEqual(before, after)  # ancien jeton révoqué sur disque
        m2 = api_mod.rotate_token()
        self.assertNotEqual(m1["fingerprint_sha256_12"], m2["fingerprint_sha256_12"])

    def test_token_file_permissions_on_load(self):
        self.assertEqual((self._var / "api_token.txt").stat().st_mode & 0o777, 0o600)


class TestApiObservability(TestAPI):
    def test_providers_endpoint_no_secret(self):
        code, data = self._get("/api/providers")
        self.assertEqual(code, 200)
        self.assertIn("providers", data)
        self.assertIn("configured_count", data)
        self.assertEqual(data["priority_order"][0], "mistral")  # Vide prioritaire
        # Aucune VALEUR secrète exposée. Le nom de variable d'env (env_var) est public et utile.
        for p in data["providers"]:
            self.assertNotIn("secret", p)
            self.assertNotIn("key_value", p)
            self.assertNotIn("api_key", p)  # pas de champ valeur de clé
            # env_var ne contient qu'un NOM de variable (majuscules), jamais une valeur
            self.assertEqual(p["env_var"], p["env_var"].upper())

    def test_alerts_endpoint(self):
        code, data = self._get("/api/alerts")
        self.assertEqual(code, 200)
        self.assertIn("alerts", data)
        self.assertIsInstance(data["alerts"], list)

    def test_security_endpoint_no_secret(self):
        code, data = self._get("/api/security")
        self.assertEqual(code, 200)
        self.assertIn("posture", data)
        self.assertIn("token_file_permissions", data)
        # le jeton de test ne doit jamais apparaître
        self.assertNotIn("test-token", json.dumps(data))

    def test_dashboard_serves_new_tabs(self):
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/", timeout=10) as r:
            html = r.read().decode()
        self.assertIn("tab-quotas", html)
        self.assertIn("tab-security", html)
        self.assertIn("loadQuotas", html)
        self.assertIn("loadSecurity", html)
        self.assertIn("memMode", html)  # sélecteur TF-IDF

    def test_memory_search_tfidf_mode_via_api(self):
        self.core.memory.add("omnibrain-core", "collective", "collective", "semantic",
                             "latence réseau à optimiser", source="t", confidence=0.8)
        code, data = self._get("/api/memory/search?q=latence&mode=tfidf")
        self.assertEqual(code, 200)
        self.assertEqual(data["mode"], "tfidf")
        self.assertTrue(data["tfidf_available"])
