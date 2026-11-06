"""API des missions : création, suivi SSE, annulation, sources, preuves,
contradictions, rapport et historique. Toutes les données viennent de la base.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from ..core.db import (ClaimRow, ContradictionRow, Mission, ReportRow,
                       ResearchCache, Source, Task)
from ..core.errors import CapacityError, NotFoundError
from ..core.schemas import MissionCreate, MissionStatus, Mode
from .deps import Actor, audit, rate_limit, require, runtime_of

router = APIRouter(prefix="/api", tags=["missions"])


def _mission_or_404(rt: Any, mission_id: str) -> Any:
    mission = rt.store.get(Mission, mission_id)
    if mission is None:
        raise NotFoundError(f"Mission inconnue : {mission_id}")
    return mission


@router.post("/missions", status_code=202, dependencies=[Depends(rate_limit)])
async def create_mission(payload: MissionCreate, request: Request,
                         actor: Actor = Depends(require("missions:create")),
                         rt=Depends(runtime_of)) -> dict[str, Any]:
    if len(rt.commander.active) >= rt.settings.max_concurrent_missions:
        raise CapacityError("Nombre maximal de missions simultanées atteint")
    options = dict(payload.options)
    if "data_origin" in options and actor.role != "admin":
        options.pop("data_origin")
    options["max_sources"] = payload.max_sources
    options["language"] = payload.language
    mission_id, _task = await rt.pipeline.submit(
        payload.query, payload.mode, actor.subject, options
    )
    audit(rt, actor, "mission_submit", mission_id, mode=payload.mode.value,
          query=payload.query[:120])
    return {
        "mission_id": mission_id, "status": MissionStatus.QUEUED.value,
        "mode": payload.mode.value, "query": payload.query,
        "links": {
            "self": f"/api/missions/{mission_id}",
            "events": f"/api/missions/{mission_id}/events",
            "report": f"/api/missions/{mission_id}/report",
        },
    }


@router.get("/missions")
def list_missions(status: str | None = None, mode: str | None = None,
                  limit: int = Query(50, ge=1, le=200),
                  actor: Actor = Depends(require("missions:read")),
                  rt=Depends(runtime_of)) -> dict[str, Any]:
    criteria: dict[str, Any] = {}
    if status:
        criteria["status"] = status
    if mode:
        criteria["mode"] = mode
    rows = rt.store.filter(Mission, order_by=Mission.created_at.desc(),
                           limit=limit, **criteria)
    return {
        "missions": [{
            "id": m.id, "query": m.query, "mode": m.mode, "status": m.status,
            "verdict": m.verdict, "stage": m.stage, "progress": m.progress,
            "created_at": m.created_at, "finished_at": m.finished_at,
            "data_origin": m.data_origin, "owner": m.owner,
        } for m in rows],
        "count": len(rows),
    }


@router.get("/missions/{mission_id}")
def get_mission(mission_id: str,
                actor: Actor = Depends(require("missions:read")),
                rt=Depends(runtime_of)) -> dict[str, Any]:
    _mission_or_404(rt, mission_id)
    return rt.commander.view(mission_id) or {}


@router.delete("/missions/{mission_id}")
def cancel_mission(mission_id: str,
                   actor: Actor = Depends(require("missions:cancel")),
                   rt=Depends(runtime_of)) -> dict[str, Any]:
    _mission_or_404(rt, mission_id)
    ok = rt.commander.cancel(mission_id)
    audit(rt, actor, "mission_cancel", mission_id, cancelled=ok)
    task = rt.tasks.get(mission_id)
    if task is not None and ok:
        task.cancel()
    return {"mission_id": mission_id, "cancelled": ok}


@router.get("/missions/{mission_id}/events")
async def mission_events(mission_id: str, request: Request,
                         last_id: int = Query(0, ge=0),
                         timeout: float = Query(60, ge=1, le=300),
                         actor: Actor = Depends(require("missions:read")),
                         rt=Depends(runtime_of)) -> StreamingResponse:
    """SSE : rejoue la trace puis diffuse les nouveaux événements (base réelle)."""
    _mission_or_404(rt, mission_id)

    async def stream() -> AsyncIterator[str]:
        cursor = last_id
        started = time.monotonic()
        heartbeat = 0.0
        while time.monotonic() - started < timeout:
            if await request.is_disconnected():
                break
            events = await asyncio.to_thread(rt.store.events_after, mission_id,
                                             cursor, 100)
            for event in events:
                cursor = event["id"]
                yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
            if time.monotonic() - heartbeat > 10:
                heartbeat = time.monotonic()
                yield ": heartbeat\n\n"
            mission = rt.store.get(Mission, mission_id)
            if mission and mission.status in {"completed", "failed", "cancelled",
                                              "insufficient_evidence"} and not events:
                yield "event: done\ndata: " + json.dumps(
                    {"status": mission.status}) + "\n\n"
                break
            await asyncio.sleep(0.4)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no",
                                      "Connection": "keep-alive"})


@router.get("/missions/{mission_id}/agents")
def mission_agents(mission_id: str,
                   actor: Actor = Depends(require("agents:read")),
                   rt=Depends(runtime_of)) -> dict[str, Any]:
    _mission_or_404(rt, mission_id)
    tasks = rt.store.filter(Task, mission_id=mission_id,
                            order_by=Task.id.asc())
    return {
        "mission_id": mission_id,
        "tasks": [{
            "id": t.id, "agent_id": t.agent_id, "division": t.division,
            "wave": t.wave, "status": t.status, "attempt": t.attempt,
            "duration_ms": t.duration_ms,
            "findings": len((t.output or {}).get("findings", [])),
            "output": t.output or {}, "error": t.error,
        } for t in tasks],
        "count": len(tasks),
        "max_parallel_agents": rt.settings.max_parallel_agents,
    }


@router.get("/missions/{mission_id}/sources")
def mission_sources(mission_id: str,
                    actor: Actor = Depends(require("missions:read")),
                    rt=Depends(runtime_of)) -> dict[str, Any]:
    _mission_or_404(rt, mission_id)
    rows = rt.store.filter(Source, mission_id=mission_id)
    return {"mission_id": mission_id, "sources": [{
        "id": r.id, "url": r.url, "title": r.title, "domain": r.domain,
        "provider": r.provider, "verified": r.verified, "http_status": r.http_status,
        "content_hash": r.content_hash, "published_at": r.published_at,
        "snippet": r.snippet[:600], "untrusted": r.untrusted,
        "injection_flags": r.injection_flags,
    } for r in rows], "count": len(rows)}


@router.get("/missions/{mission_id}/claims")
def mission_claims(mission_id: str,
                   actor: Actor = Depends(require("reports:read")),
                   rt=Depends(runtime_of)) -> dict[str, Any]:
    _mission_or_404(rt, mission_id)
    rows = rt.store.filter(ClaimRow, mission_id=mission_id)
    return {"claims": [{
        "id": r.id, "text": r.text, "status": r.status,
        "confidence": r.confidence, "support_ids": r.support_ids,
        "independent_domains": r.independent_domains, "rationale": r.rationale,
    } for r in rows], "count": len(rows)}


@router.get("/missions/{mission_id}/contradictions")
def mission_contradictions(mission_id: str,
                           actor: Actor = Depends(require("reports:read")),
                           rt=Depends(runtime_of)) -> dict[str, Any]:
    _mission_or_404(rt, mission_id)
    rows = rt.store.filter(ContradictionRow, mission_id=mission_id)
    return {"contradictions": [{
        "id": r.id, "claim_id": r.claim_id, "statement_a": r.statement_a,
        "statement_b": r.statement_b, "resolution": r.resolution,
        "winner": r.winner, "rationale": r.rationale,
        "evidence_ids": r.evidence_ids,
    } for r in rows], "count": len(rows)}


@router.get("/missions/{mission_id}/report")
def mission_report(mission_id: str,
                   actor: Actor = Depends(require("reports:read")),
                   rt=Depends(runtime_of)) -> dict[str, Any]:
    _mission_or_404(rt, mission_id)
    report = rt.store.get(ReportRow, f"report-{mission_id}")
    if report is None:
        return {"mission_id": mission_id, "status": "no_report_yet",
                "markdown": "", "available": False}
    return {"mission_id": mission_id, "available": True,
            "verdict": report.verdict, "citation_count": report.citation_count,
            "created_at": report.created_at, "markdown": report.markdown,
            "structured": report.payload or {}}


@router.get("/history")
def history(limit: int = Query(50, ge=1, le=200),
            actor: Actor = Depends(require("missions:read")),
            rt=Depends(runtime_of)) -> dict[str, Any]:
    rows = rt.store.filter(Mission, order_by=Mission.created_at.desc(), limit=limit)
    cache = rt.store.filter(ResearchCache, limit=limit)
    return {
        "missions": [{
            "id": m.id, "query": m.query, "mode": m.mode, "status": m.status,
            "verdict": m.verdict, "created_at": m.created_at,
            "has_report": rt.store.get(ReportRow, f"report-{m.id}") is not None,
        } for m in rows],
        "reusable_researches": [{"id": c.id, "query": c.query,
                                 "hits": c.hits, "created_at": c.created_at}
                                for c in cache],
    }
