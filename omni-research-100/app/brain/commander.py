"""Research Commander : cycle de vie, états, progression, annulation et
limite globale de concurrence entre missions.
"""
from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any

from ..core.config import Settings
from ..core.db import Mission, Store, Task
from ..core.logging_conf import log_event
from ..core.schemas import MissionStatus, Mode, new_id


class ResearchCommander:
    def __init__(self, store: Store, settings: Settings) -> None:
        self.store = store
        self.settings = settings
        self._cancel: dict[str, asyncio.Event] = {}
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_missions)
        self.active: set[str] = set()

    @asynccontextmanager
    async def slot(self, mission_id: str):
        async with self._semaphore:
            self.active.add(mission_id)
            try:
                yield
            finally:
                self.active.discard(mission_id)
                self._cancel.pop(mission_id, None)

    def create(self, query: str, mode: Mode, owner: str = "system",
               options: dict[str, Any] | None = None) -> str:
        options = options or {}
        mission_id = new_id("mission")
        self.store.add(Mission(
            id=mission_id, query=query, mode=mode.value,
            status=MissionStatus.QUEUED.value, verdict="NEEDS_WORK",
            owner=owner, progress=0.0, stage="queued",
            created_at=time.time(), updated_at=time.time(),
            data_origin=str(options.get("data_origin", "live")),
            meta={"options": options, "created_by": owner},
        ))
        self._cancel[mission_id] = asyncio.Event()
        self.emit(mission_id, "mission_created", "queued",
                  query=query[:200], mode=mode.value, owner=owner)
        self.store.audit(owner, "mission_created", mission_id, mode=mode.value)
        log_event("commander", "mission_created", mission_id=mission_id, mode=mode.value)
        return mission_id

    def emit(self, mission_id: str, kind: str, stage: str = "", **payload: Any) -> None:
        self.store.add_event(mission_id, kind, stage, **payload)

    def stage(self, mission_id: str, status: MissionStatus, stage: str,
              progress: float, **payload: Any) -> None:
        self.store.update(Mission, mission_id, status=status.value, stage=stage,
                          progress=round(progress, 3), updated_at=time.time())
        self.emit(mission_id, "stage_changed", stage, status=status.value,
                  progress=round(progress, 3), **payload)

    def cancel(self, mission_id: str) -> bool:
        mission = self.store.get(Mission, mission_id)
        if mission is None or mission.status in {
            MissionStatus.COMPLETED.value, MissionStatus.FAILED.value,
            MissionStatus.CANCELLED.value, MissionStatus.INSUFFICIENT_EVIDENCE.value,
        }:
            return False
        event = self._cancel.setdefault(mission_id, asyncio.Event())
        event.set()
        self.store.update(Mission, mission_id, status=MissionStatus.CANCELLED.value,
                          stage="cancelled", updated_at=time.time(),
                          finished_at=time.time())
        self.emit(mission_id, "mission_cancelled", "cancelled")
        self.store.audit("system", "mission_cancelled", mission_id)
        return True

    def cancelled(self, mission_id: str) -> bool:
        event = self._cancel.get(mission_id)
        return bool(event and event.is_set())

    def fail(self, mission_id: str, error: str) -> None:
        self.store.update(Mission, mission_id, status=MissionStatus.FAILED.value,
                          stage="failed", error=error[:1000], updated_at=time.time(),
                          finished_at=time.time())
        self.store.record_error("commander", error, mission_id)
        self.emit(mission_id, "mission_failed", "failed", error=error[:400])

    def complete(self, mission_id: str, status: MissionStatus, verdict: str,
                 progress: float = 1.0) -> None:
        self.store.update(Mission, mission_id, status=status.value, stage=status.value,
                          verdict=verdict, progress=progress, updated_at=time.time(),
                          finished_at=time.time())
        self.emit(mission_id, "mission_completed", status.value,
                  verdict=verdict, status=status.value)

    def view(self, mission_id: str) -> dict[str, Any] | None:
        mission = self.store.get(Mission, mission_id)
        if mission is None:
            return None
        tasks = self.store.filter(Task, mission_id=mission_id)
        events = self.store.events_after(mission_id, 0, limit=2000)
        return {
            "id": mission.id, "query": mission.query, "mode": mission.mode,
            "status": mission.status, "verdict": mission.verdict,
            "stage": mission.stage, "progress": mission.progress,
            "owner": mission.owner, "created_at": mission.created_at,
            "updated_at": mission.updated_at, "finished_at": mission.finished_at,
            "error": mission.error, "plan": mission.plan or {},
            "data_origin": mission.data_origin,
            "active_missions": sorted(self.active),
            "tasks": [{
                "id": t.id, "agent_id": t.agent_id, "division": t.division,
                "wave": t.wave, "status": t.status, "attempt": t.attempt,
                "duration_ms": t.duration_ms,
                "findings": len((t.output or {}).get("findings", [])),
                "error": t.error[:200],
            } for t in tasks],
            "task_summary": {
                "total": len(tasks),
                "ok": sum(1 for t in tasks if t.status == "ok"),
                "running": sum(1 for t in tasks if t.status == "running"),
                "queued": sum(1 for t in tasks if t.status == "queued"),
                "failed": sum(1 for t in tasks if t.status == "failed"),
            },
            "events": events[-120:],
            "event_count": len(events),
        }
