"""Tests API : authentification, permissions, cycle de vie, providers, réglages."""
from __future__ import annotations

import time

import pytest

TERMINAL = {"completed", "failed", "cancelled", "insufficient_evidence"}


def wait_mission(client, headers, mission_id, timeout=20.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/api/missions/{mission_id}", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        if data["status"] in TERMINAL:
            return data
        time.sleep(0.1)
    raise AssertionError("mission non terminée dans le délai imparti")


@pytest.mark.api
def test_health_is_public_and_secrets_are_absent(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in {"ok", "degraded"}
    assert data["agents"] == 100
    assert "auth_secret" not in r.text and "api_key" not in r.text


@pytest.mark.api
def test_authentication_is_required(client):
    assert client.get("/api/missions").status_code == 401
    assert client.get("/api/settings").status_code == 401
    assert client.post("/api/missions", json={"query": "test", "mode": "fast"}).status_code == 401
    bad = client.post("/api/auth/login", json={"username": "admin",
                                               "password": "wrong"})
    assert bad.status_code == 401


@pytest.mark.api
def test_login_permissions_and_role_denial(client, auth, settings):
    me = client.get("/api/auth/me", headers=auth)
    assert me.status_code == 200 and me.json()["role"] == "admin"
    perms = client.get("/api/auth/permissions", headers=auth)
    assert perms.status_code == 200 and "admin" in perms.json()["roles"]
    researcher = client.post("/api/auth/login", json={
        "username": "researcher", "password": settings.user_password})
    assert researcher.status_code == 200
    headers = {"Authorization": "Bearer " + researcher.json()["access_token"]}
    denied = client.patch("/api/settings", json={"max_parallel_agents": 2},
                          headers=headers)
    assert denied.status_code == 403
    assert client.get("/api/missions", headers=headers).status_code == 200


@pytest.mark.api
def test_full_mission_lifecycle_via_api(client, auth):
    created = client.post("/api/missions", headers=auth, json={
        "query": "Versions de l'API et étude 2025 ?", "mode": "deep",
        "max_sources": 12,
        "options": {"data_origin": "offline-fixture", "skip_extraction": True},
    })
    assert created.status_code == 202, created.text
    mid = created.json()["mission_id"]
    assert created.json()["mode"] == "deep"
    data = wait_mission(client, auth, mid)
    assert data["status"] == "completed", data
    assert data["verdict"] == "NEEDS_WORK"  # double de test hors ligne
    assert data["task_summary"]["total"] == 16

    assert client.get(f"/api/missions/{mid}/agents", headers=auth).status_code == 200
    agents = client.get(f"/api/missions/{mid}/agents", headers=auth).json()
    assert agents["count"] == 16
    sources = client.get(f"/api/missions/{mid}/sources", headers=auth).json()
    assert sources["count"] == 8 and sources["sources"][0]["untrusted"] is True
    claims = client.get(f"/api/missions/{mid}/claims", headers=auth).json()
    assert claims["count"] >= 0
    contra = client.get(f"/api/missions/{mid}/contradictions", headers=auth).json()
    assert contra["count"] >= 0
    report = client.get(f"/api/missions/{mid}/report", headers=auth).json()
    assert report["available"] is True and "Table des preuves" in report["markdown"]
    assert report["structured"]["gates"]["real_provider"] is False
    listing = client.get("/api/missions", headers=auth).json()
    assert any(m["id"] == mid for m in listing["missions"])
    history = client.get("/api/history", headers=auth).json()
    assert any(m["id"] == mid for m in history["missions"])
    assert client.get("/api/missions/does-not-exist", headers=auth).status_code == 404


@pytest.mark.api
def test_agents_providers_settings_and_metrics(client, auth):
    agents = client.get("/api/agents?limit=3", headers=auth)
    assert agents.status_code == 200 and agents.json()["total"] == 100
    assert len(agents.json()["agents"]) == 3
    divisions = client.get("/api/agents/divisions", headers=auth).json()
    assert len(divisions) == 10
    detail = client.get("/api/agents/WEB-01", headers=auth).json()
    assert detail["handler_callable"] is True
    validation = client.get("/api/agents/validation", headers=auth).json()
    assert validation["valid"] is True and validation["agents"] == 100

    providers = client.get("/api/providers", headers=auth).json()
    assert {"searxng", "tavily", "brave", "exa", "firecrawl", "fixture"} <= \
        set(p["name"] for p in providers["providers"])
    assert "tavily" in [p["name"] for p in providers["providers"]
                        if p["status"] == "not_configured"]
    tested = client.post("/api/providers/fixture/test", headers=auth,
                         json={"query": "open source intelligence"})
    assert tested.status_code == 200
    assert tested.json()["configured"] is True
    assert len(tested.json()["sources"]) == 3  # test borné à 3 sources
    assert tested.json()["real_results"] is False  # double de test déclaré
    not_configured = client.post("/api/providers/tavily/test", headers=auth,
                                 json={"query": "test"})
    assert not_configured.json()["status"] == "not_configured"
    assert not_configured.json()["sources"] == []

    toggled = client.patch("/api/providers/tavily?enabled=false", headers=auth)
    assert toggled.status_code == 200 and "tavily" in toggled.json()["disabled"]

    settings = client.get("/api/settings", headers=auth)
    assert settings.status_code == 200
    assert "max_parallel_agents" in settings.json()["settings"]
    assert "auth_secret" not in settings.text
    patched = client.patch("/api/settings", headers=auth,
                           json={"max_parallel_agents": 3})
    assert patched.status_code == 200
    assert patched.json()["applied"]["max_parallel_agents"] == 3
    assert client.get("/api/metrics", headers=auth).status_code == 200
    assert client.get("/api/audit", headers=auth).status_code == 200
    assert client.get("/api/providers/quota", headers=auth).status_code == 200


@pytest.mark.api
def test_rate_limit_and_destructive_purge_guard(client, auth, runtime):
    runtime.limiter._buckets.clear()
    runtime.limiter.capacity = 2
    ok = [client.post("/api/auth/login", json={"username": "admin",
                                               "password": runtime.settings.admin_password})
          for _ in range(2)]
    assert all(r.status_code == 200 for r in ok)
    limited = client.post("/api/auth/login", json={"username": "admin",
                                                   "password": runtime.settings.admin_password})
    assert limited.status_code == 429
    runtime.limiter.capacity = 60
    runtime.limiter._buckets.clear()
    refused = client.post("/api/retention/purge", headers=auth,
                          json={"older_than_days": 30, "confirm": "NO"})
    assert refused.status_code == 422


@pytest.mark.api
def test_sse_stream_replays_real_events(client, auth):
    created = client.post("/api/missions", headers=auth, json={
        "query": "test SSE", "mode": "fast",
        "options": {"data_origin": "offline-fixture", "skip_extraction": True}})
    mid = created.json()["mission_id"]
    wait_mission(client, auth, mid)
    response = client.get(f"/api/missions/{mid}/events?timeout=1", headers=auth)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "agent_result" in response.text
