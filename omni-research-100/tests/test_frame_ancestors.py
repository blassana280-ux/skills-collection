"""En-têtes d'embarquement : strict par défaut, preview explicitement autorisé.

Le preview Arena affiche l'application dans une iframe : `X-Frame-Options: DENY`
et `frame-ancestors 'none'` la rendaient blanche. La politique reste stricte en
production et pour toute valeur d'environnement malformée.
"""
from __future__ import annotations

import pytest

from app.main import frame_ancestors_for

STRICT_CSP = "frame-ancestors 'none'"


@pytest.mark.api
def test_ui_is_not_embeddable_by_default(client, monkeypatch):
    monkeypatch.delenv("OMNI_FRAME_ANCESTORS", raising=False)
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["X-Frame-Options"] == "DENY"
    assert STRICT_CSP in response.headers["Content-Security-Policy"]


@pytest.mark.api
def test_preview_can_be_embedded_with_explicit_env(client, monkeypatch):
    monkeypatch.setenv("OMNI_FRAME_ANCESTORS",
                       "https://*.e2b.app https://*.arena.ai")
    response = client.get("/")
    assert response.status_code == 200
    assert "X-Frame-Options" not in response.headers
    csp = response.headers["Content-Security-Policy"]
    assert "frame-ancestors https://*.e2b.app https://*.arena.ai" in csp
    assert "default-src 'self'" in csp and "connect-src 'self'" in csp
    # Cohérence sur les endpoints d'API, pas seulement sur la page HTML.
    health = client.get("/api/health")
    assert "X-Frame-Options" not in health.headers
    assert "frame-ancestors https://*.e2b.app" in health.headers["Content-Security-Policy"]


@pytest.mark.api
def test_invalid_frame_ancestors_cannot_inject_headers(client, monkeypatch):
    monkeypatch.setenv("OMNI_FRAME_ANCESTORS",
                       "https://evil.example; script-src *\r\nX-Injected: 1")
    response = client.get("/")
    assert response.headers["X-Frame-Options"] == "DENY"
    assert STRICT_CSP in response.headers["Content-Security-Policy"]
    assert "X-Injected" not in response.headers
    assert "script-src *" not in response.headers["Content-Security-Policy"]


@pytest.mark.api
def test_production_never_relaxes_clickjacking(monkeypatch):
    monkeypatch.setenv("OMNI_FRAME_ANCESTORS", "*")
    assert frame_ancestors_for("production") == ""
    assert frame_ancestors_for("development") == "*"
    assert frame_ancestors_for("development", "'none'") == ""
    assert frame_ancestors_for("development", "https://a.example; bad\n") == ""
