"""Configuration pytest : base SQLite temporaire, runtime complet, double HTTP.

Aucun test n'accède au réseau public. Les recherches de test passent par un
double de test déclaré (`test_double=True`) avec transport httpx simulé.
"""
from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.runtime import build_runtime
from tests.fixtures.provider_responses import FixtureProvider, make_mock_client


@pytest.fixture
def settings(tmp_path):
    return replace(
        Settings.from_env(),
        env="test",
        database_url=f"sqlite:///{tmp_path}/or100-test.db",
        omnibrain_queue_dir=str(tmp_path / "omnibrain-queue"),
        searxng_enabled=False,
        searxng_url="https://searxng.local",
        dns_ssrf_check=False,
        llm_provider="extractive",
        auth_secret="test-secret-au-moins-32-octets-pour-jwt-local",
        admin_password="admin-test-password",
        user_password="user-test-password",
        omnibrain_api_key="test-omnibrain-api-key",
        max_parallel_agents=4,
        max_concurrent_missions=2,
        max_sources_per_mission=30,
        max_extractions_per_mission=4,
        retention_days=30,
        tavily_api_key="", brave_api_key="", exa_api_key="", firecrawl_api_key="",
        openai_api_key="", anthropic_api_key="",
        redis_url="", qdrant_url="",
        http_timeout_seconds=5,
    )


@pytest.fixture
def fixture_provider(settings) -> FixtureProvider:
    return FixtureProvider(settings)


@pytest.fixture
def runtime(settings, fixture_provider):
    rt = build_runtime(
        settings,
        extra_providers=[fixture_provider],
        client_factory=make_mock_client,
        provider_plugins=False,
    )
    yield rt
    rt.close()


@pytest.fixture
def app(runtime, settings):
    return create_app(runtime=runtime, settings=settings)


@pytest.fixture
def client(app):
    # Le gestionnaire de cycle de vie garde UNE boucle d'événements : les
    # missions lancées en tâche de fond peuvent réellement se terminer.
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth(client, settings):
    response = client.post("/api/auth/login",
                           json={"username": "admin",
                                 "password": settings.admin_password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def omnibrain_auth(settings):
    return {"X-OmniBrain-Key": settings.omnibrain_api_key,
            "X-OmniBrain-Contract": "1.0"}


@pytest.fixture
def offline_options():
    return {"data_origin": "offline-fixture", "skip_extraction": True}


@pytest.fixture
def corpus_docs():
    from app.core.schemas import SourceRecord
    from app.providers.base import content_hash, canonicalize_url, domain_of
    from tests.fixtures.corpus import CORPUS
    docs = []
    for i, row in enumerate(CORPUS):
        canonical = canonicalize_url(row["url"])
        docs.append(SourceRecord(
            url=row["url"], title=row["title"], snippet=row["content"],
            text=row["content"], provider="fixture", domain=domain_of(canonical),
            canonical_url=canonical,
            content_hash=content_hash(canonical, row["title"], row["content"]),
            published_at=row["published"], verified=(i % 2 == 0),
            source_id=f"src-{i}",
        ))
    return docs
