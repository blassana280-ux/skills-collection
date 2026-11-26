"""Mémoire persistante, réutilisation, rétention, sauvegarde, journalisation."""
from __future__ import annotations

import time

import pytest

from app.core.db import (AuditLog, ErrorLog, Metric, Mission, ResearchCache,
                         Source)
from app.core.schemas import MissionStatus


@pytest.mark.unit
def test_memory_backends_are_reported_honestly(runtime):
    info = runtime.memory.describe()
    assert info["source_of_truth"] == "sqlite"
    assert "in-process" in info["task_queue"]
    assert "local" in info["vector_index"]
    assert info["retention_days"] == runtime.settings.retention_days


@pytest.mark.asyncio
@pytest.mark.unit
async def test_reusable_research_and_vector_index(runtime):
    key = await runtime.memory.remember("étude API 2025", "fast", "m1", {"ok": True})
    assert runtime.store.count(ResearchCache) == 1
    hit = await runtime.memory.find_reusable("étude API 2025", "fast")
    assert hit and hit["match"] == "exact" and hit["hits"] == 1
    similar = await runtime.vector_index.search("étude API 2025", limit=2)
    assert similar and similar[0]["score"] > 0.5
    assert key in [p["key"] for p in similar]


@pytest.mark.unit
def test_retention_requires_explicit_confirmation(runtime):
    old = time.time() - 20 * 86400
    runtime.store.add(Mission(id="old-mission", query="ancien", mode="fast",
                              status=MissionStatus.COMPLETED.value,
                              created_at=old, updated_at=old))
    runtime.store.add(Source(id="old-source", mission_id="old-mission",
                             url="https://example.org/old", fetched_at=old))
    with pytest.raises(ValueError):
        runtime.memory.purge_expired(1, confirm="NO")
    deleted = runtime.memory.purge_expired(1, confirm="PURGE")
    assert deleted["missions"] >= 1
    assert runtime.store.get(Mission, "old-mission") is None
    assert any(a.action == "retention_purge" for a in runtime.store.filter(AuditLog))


@pytest.mark.unit
def test_backup_and_error_metric_persistence(runtime, settings, tmp_path):
    runtime.store.record_error("test", "message de test", "m1", "warning")
    runtime.store.record_metric("agent_duration_ms", 12.5, "m1", agent="WEB-01")
    runtime.store.audit("tester", "test_action", "m1", detail="ok")
    assert runtime.store.filter(ErrorLog, mission_id="m1")
    assert runtime.store.filter(Metric, mission_id="m1")
    assert runtime.store.filter(AuditLog, actor="tester")
    path = tmp_path / "backup.db"
    assert runtime.store.backup(str(path)) == str(path)
    assert path.exists() and path.stat().st_size > 0


@pytest.mark.unit
def test_settings_persistence(runtime):
    runtime.store.set_setting("disabled_providers", ["tavily"])
    assert runtime.store.get_setting("disabled_providers") == ["tavily"]
    runtime.store.set_setting("quota_overrides", {"fixture": 3})
    assert runtime.store.get_setting("quota_overrides")["fixture"] == 3
