"""Adaptateur OmniBrain versionné (v1), sécurisé et compatible avec le contrat
réel inspecté dans `blassana280-ux/omni-agents-framework` :

- `OMNIBRAIN.md` : orchestrateur, 6 gates, arbitrage, READY sans provider réel
  impossible, actions dangereuses refusées sans confirmation humaine ;
- `registry/agents.json` : id, title, specialties, skills, provenance,
  boundaries, brief_template ;
- `cf100/bridges/omnibrain.py` : messages {skill, task, context} ->
  {agent, ok, result, evidence_hash} ;
- `cf100/bridges/omni_queue.py` : fichiers JSONL omni-inbox / cf100-outbox /
  omni-done, accusés append-only.

Ce module ne modifie AUCUN dépôt OmniBrain : l'intégration est entièrement
côté OMNI-RESEARCH 100.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, Request

from ..agents.registry import (DANGEROUS_ACTIONS, OMNIBRAIN_DANGEROUS_ACTIONS,
                               OMNIBRAIN_GATES)
from ..core.db import Mission, ReportRow, Source, Task
from ..core.errors import (AuthenticationError, NotFoundError, ValidationError)
from ..core.logging_conf import log_event
from ..core.schemas import Mode, OmnibrainSubmit
from .deps import Actor, audit, require, runtime_of

CONTRACT_VERSION = "1.0"
CONTRACT_SOURCES = [
    "blassana280-ux/omni-agents-framework:OMNIBRAIN.md",
    "blassana280-ux/omni-agents-framework:AGENTS.md",
    "blassana280-ux/omni-agents-framework:registry/permissions.json",
    "blassana280-ux/omni-agents-framework:cyber-force-100/cf100/bridges/omnibrain.py",
    "blassana280-ux/omni-agents-framework:cyber-force-100/cf100/bridges/omni_queue.py",
    "blassana280-ux/omni-agents-framework:cyber-force-100/docs/OMNIBRAIN-INTEGRATION.md",
    "blassana280-ux/skills-collection:AGENTS.md",
]

_SKILL_DIVISIONS: dict[str, list[str]] = {
    "research": ["WEB", "DEEP", "SYN"],
    "web": ["WEB"], "deep-research": ["DEEP"], "news": ["NEWS"],
    "science": ["SCI"], "technology": ["TECH"], "osint": ["OSINT"],
    "social": ["SOC"], "fact-check": ["FACT"], "data": ["DATA"],
    "synthesis": ["SYN"], "security": ["FACT", "OSINT"],
}

router = APIRouter(prefix="/api/omnibrain/v1", tags=["omnibrain"])


def _contract_guard(x_omnibrain_contract: str | None = Header(default=None)) -> None:
    if x_omnibrain_contract and x_omnibrain_contract != CONTRACT_VERSION:
        raise ValidationError(
            f"Version de contrat non prise en charge : {x_omnibrain_contract}",
            supported=CONTRACT_VERSION)


def _mode(value: Any) -> Mode:
    try:
        return Mode(str(value or "deep").lower())
    except ValueError as exc:
        raise ValidationError(f"Mode inconnu : {value}") from exc


def _evidence_hash(rt: Any, mission_id: str) -> str:
    rows = rt.store.filter(Source, mission_id=mission_id)
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda r: r.id):
        digest.update(f"{row.id}|{row.content_hash}|{row.url}\n".encode())
    report = rt.store.get(ReportRow, f"report-{mission_id}")
    if report is not None:
        digest.update(report.markdown.encode("utf-8", errors="replace"))
    return digest.hexdigest()


def _mission(rt: Any, mission_id: str) -> Any:
    mission = rt.store.get(Mission, mission_id)
    if mission is None:
        raise NotFoundError(f"Mission inconnue : {mission_id}")
    return mission


class OmniQueueAdapter:
    """Compatible `omni_queue.py` : inbox / outbox / done en JSONL append-only."""

    def __init__(self, directory: str) -> None:
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.inbox = self.dir / "omni-inbox.jsonl"
        self.outbox = self.dir / "cf100-outbox.jsonl"
        self.done = self.dir / "omni-done.jsonl"

    @staticmethod
    def _read(path: Path) -> list[dict[str, Any]]:
        if not path.is_file():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    @staticmethod
    def _append(path: Path, message: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message, ensure_ascii=False) + "\n")

    def poll(self) -> list[dict[str, Any]]:
        acked = {m.get("id") for m in self._read(self.done)}
        return [m for m in self._read(self.inbox) if m.get("id") not in acked]

    def ack(self, message_id: str) -> None:
        self._append(self.done, {"id": message_id, "acked_at": time.time()})

    def reply(self, message: dict[str, Any]) -> None:
        self._append(self.outbox, message)

    def status(self) -> dict[str, Any]:
        return {"queue_dir": str(self.dir), "pending": len(self.poll()),
                "replies": len(self._read(self.outbox)),
                "acked": len(self._read(self.done))}


def queue_of(rt: Any) -> OmniQueueAdapter:
    return OmniQueueAdapter(rt.settings.omnibrain_queue_dir)


@router.get("/contract")
def contract(actor: Actor = Depends(require("agents:read")),
             rt=Depends(runtime_of)) -> dict[str, Any]:
    export = rt.registry.export_for_omnibrain()
    return {
        "contract_version": CONTRACT_VERSION,
        "source_of_truth": CONTRACT_SOURCES,
        "protocol": {
            "omnibrain_to_or100": {"skill": "string", "task": "object",
                                   "context": "object", "request": "string"},
            "or100_to_omnibrain": {"agent": "string", "ok": "boolean",
                                   "result": "object", "evidence_hash": "sha256"},
            "queue": {"inbox": "omni-inbox.jsonl", "outbox": "cf100-outbox.jsonl",
                      "done": "omni-done.jsonl",
                      "reply": {"in_response_to": "id", "agent": "...", "ok": "bool",
                                "status": "...", "result": "{}", "replied_at": "ts"}},
        },
        "capabilities": ["submit_mission", "choose_mode", "track_progress",
                         "cancel_mission", "get_results", "get_report",
                         "get_evidence_and_citations"],
        "gates": list(OMNIBRAIN_GATES),
        "dangerous_actions_denied": list(DANGEROUS_ACTIONS),
        "alignment": rt.registry.dangerous_action_alignment(),
        "agents_exported": len(export["agents"]),
        "registry_export": export,
        "no_modification_of_omnibrain_repos": True,
        "callback_posting": "disabled by default (SSRF policy; results via GET)",
    }


@router.get("/modes")
def modes(actor: Actor = Depends(require("omnibrain:submit")),
          rt=Depends(runtime_of)) -> dict[str, Any]:
    return {"contract_version": CONTRACT_VERSION,
            "modes": rt.status()["modes"],
            "default": "deep"}


@router.post("/missions", status_code=202,
             dependencies=[Depends(_contract_guard)])
async def submit(payload: OmnibrainSubmit,
                 actor: Actor = Depends(require("omnibrain:submit")),
                 rt=Depends(runtime_of)) -> dict[str, Any]:
    mode = _mode(payload.mode or payload.task.get("mode")
                 or payload.context.get("mode"))
    divisions = _SKILL_DIVISIONS.get(payload.skill.lower(), [])
    options: dict[str, Any] = {
        "language": str(payload.context.get("language", "fr")),
        "omnibrain_skill": payload.skill,
        "omnibrain_contract": CONTRACT_VERSION,
    }
    if divisions:
        options["divisions"] = divisions
    if payload.task.get("max_sources"):
        options["max_sources"] = int(payload.task["max_sources"])
    mission_id, _task = await rt.pipeline.submit(
        payload.request, mode, actor.subject, options
    )
    audit(rt, actor, "omnibrain_submit", mission_id, skill=payload.skill,
          mode=mode.value)
    return {
        "contract_version": CONTRACT_VERSION, "accepted": True,
        "mission_id": mission_id, "status": "queued", "skill": payload.skill,
        "mode": mode.value, "agent": "omni-research-100",
        "links": {
            "status": f"/api/omnibrain/v1/missions/{mission_id}",
            "results": f"/api/omnibrain/v1/missions/{mission_id}/results",
            "report": f"/api/omnibrain/v1/missions/{mission_id}/report",
            "evidence": f"/api/omnibrain/v1/missions/{mission_id}/evidence",
        },
    }


@router.get("/missions/{mission_id}")
def status(mission_id: str,
           actor: Actor = Depends(require("missions:read")),
           rt=Depends(runtime_of)) -> dict[str, Any]:
    mission = _mission(rt, mission_id)
    view = rt.commander.view(mission_id) or {}
    return {
        "contract_version": CONTRACT_VERSION,
        "mission_id": mission_id, "agent": "omni-research-100",
        "ok": mission.status not in {"failed", "cancelled"},
        "status": mission.status, "verdict": mission.verdict,
        "stage": mission.stage, "progress": mission.progress,
        "task_summary": view.get("task_summary", {}),
        "agents_active": [t["agent_id"] for t in view.get("tasks", [])
                          if t["status"] == "running"][:20],
        "evidence_hash": _evidence_hash(rt, mission_id),
        "result": {"mode": mission.mode, "query": mission.query,
                   "created_at": mission.created_at,
                   "updated_at": mission.updated_at},
        "error": mission.error,
    }


@router.delete("/missions/{mission_id}")
def cancel(mission_id: str,
           actor: Actor = Depends(require("missions:cancel")),
           rt=Depends(runtime_of)) -> dict[str, Any]:
    _mission(rt, mission_id)
    ok = rt.commander.cancel(mission_id)
    task = rt.tasks.get(mission_id)
    if task is not None and ok:
        task.cancel()
    audit(rt, actor, "omnibrain_cancel", mission_id, cancelled=ok)
    return {"contract_version": CONTRACT_VERSION, "mission_id": mission_id,
            "cancelled": ok, "agent": "omni-research-100", "ok": ok,
            "result": {"status": "cancelled" if ok else "not_cancellable"}}


@router.get("/missions/{mission_id}/results")
def results(mission_id: str,
            actor: Actor = Depends(require("missions:read")),
            rt=Depends(runtime_of)) -> dict[str, Any]:
    mission = _mission(rt, mission_id)
    report = rt.store.get(ReportRow, f"report-{mission_id}")
    tasks = rt.store.filter(Task, mission_id=mission_id)
    return {
        "contract_version": CONTRACT_VERSION,
        "mission_id": mission_id, "agent": "omni-research-100",
        "ok": report is not None,
        "status": mission.status, "verdict": mission.verdict,
        "result": (report.payload if report is not None else
                   {"claims": [], "contradictions": [], "citations": [],
                    "coverage": {}, "gates": {}}),
        "agent_outputs": [{"agent": t.agent_id, "status": t.status,
                           "wave": t.wave, "duration_ms": t.duration_ms,
                           "findings": len((t.output or {}).get("findings", []))}
                          for t in tasks],
        "evidence_hash": _evidence_hash(rt, mission_id),
    }


@router.get("/missions/{mission_id}/report")
def report(mission_id: str,
           actor: Actor = Depends(require("reports:read")),
           rt=Depends(runtime_of)) -> dict[str, Any]:
    _mission(rt, mission_id)
    row = rt.store.get(ReportRow, f"report-{mission_id}")
    if row is None:
        return {"contract_version": CONTRACT_VERSION, "mission_id": mission_id,
                "available": False, "markdown": "", "citations": []}
    payload = row.payload or {}
    return {
        "contract_version": CONTRACT_VERSION, "mission_id": mission_id,
        "available": True, "markdown": row.markdown,
        "verdict": row.verdict, "citations": payload.get("citations", []),
        "gates": payload.get("gates", {}),
        "evidence_hash": _evidence_hash(rt, mission_id),
        "agent": "omni-research-100", "ok": True,
        "result": payload,
    }


@router.get("/missions/{mission_id}/evidence")
def evidence(mission_id: str,
             actor: Actor = Depends(require("reports:read")),
             rt=Depends(runtime_of)) -> dict[str, Any]:
    _mission(rt, mission_id)
    rows = rt.store.filter(Source, mission_id=mission_id)
    report = rt.store.get(ReportRow, f"report-{mission_id}")
    citations = (report.payload or {}).get("citations", []) if report else []
    return {
        "contract_version": CONTRACT_VERSION, "mission_id": mission_id,
        "agent": "omni-research-100", "ok": True,
        "evidence_hash": _evidence_hash(rt, mission_id),
        "citations": citations,
        "sources": [{
            "id": r.id, "url": r.url, "title": r.title, "domain": r.domain,
            "provider": r.provider, "content_hash": r.content_hash,
            "verified": r.verified, "untrusted": True,
            "injection_flags": r.injection_flags,
        } for r in rows],
        "result": {"source_count": len(rows), "citation_count": len(citations)},
    }


@router.get("/queue/status")
def queue_status(actor: Actor = Depends(require("omnibrain:submit")),
                 rt=Depends(runtime_of)) -> dict[str, Any]:
    return {"contract_version": CONTRACT_VERSION, **queue_of(rt).status()}


@router.post("/queue/process")
async def queue_process(limit: int = 5,
                        actor: Actor = Depends(require("omnibrain:submit")),
                        rt=Depends(runtime_of)) -> dict[str, Any]:
    """Traite les demandes déposées par OmniBrain dans omni-inbox.jsonl et
    écrit les réponses au format cf100-outbox.jsonl, puis les accuse."""
    queue = queue_of(rt)
    replies: list[dict[str, Any]] = []
    for message in queue.poll()[: max(1, min(limit, 20))]:
        request = str(message.get("request", "")).strip()
        try:
            if len(request) < 3:
                raise ValidationError("requête trop courte")
            mode = _mode(message.get("task", {}).get("mode")
                         or message.get("mode") or "deep")
            mission_id, _task = await rt.pipeline.submit(
                request, mode, "omnibrain-queue",
                {"omnibrain_message_id": message.get("id")},
            )
            reply = {
                "in_response_to": message.get("id"),
                "agent": "omni-research-100", "ok": True,
                "status": "queued", "mission_id": mission_id,
                "result": {"skill": message.get("skill", "research"),
                           "mode": mode.value},
                "replied_at": time.time(),
            }
        except Exception as exc:
            reply = {
                "in_response_to": message.get("id"),
                "agent": "omni-research-100", "ok": False,
                "status": "rejected", "result": {"error": str(exc)[:300]},
                "replied_at": time.time(),
            }
        queue.reply(reply)
        queue.ack(str(message.get("id")))
        replies.append(reply)
    log_event("omnibrain", "queue_processed", processed=len(replies))
    return {"contract_version": CONTRACT_VERSION, "processed": len(replies),
            "replies": replies, "queue": queue.status()}
