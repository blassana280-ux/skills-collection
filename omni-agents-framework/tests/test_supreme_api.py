"""Tests API : auth, lecture anonyme, écritures protégées, données réelles."""
import json
import threading
import urllib.request
import urllib.error

from supreme.api import APIState, make_handler
from http.server import ThreadingHTTPServer
from tests._supreme_util import SupremeTestCase


class TestAPI(SupremeTestCase):
    def setUp(self):
        super().setUp()
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
