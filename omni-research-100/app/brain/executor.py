"""Parallel Executor : concurrence réelle mesurée, limite stricte, reprises.

Le pic de concurrence est MESURé (compteur sous verrou), jamais supposé.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from ..agents.registry import AgentRegistry
from ..agents.runner import AgentRunner
from ..core.config import Settings
from ..core.db import Store, Task
from ..core.logging_conf import log_event
from ..core.schemas import AgentOutput, Claim, MissionPlan, Mode, SourceRecord
from .scheduler import TaskScheduler, Wave


@dataclass
class ExecutionReport:
    outputs: list[AgentOutput] = field(default_factory=list)
    wave_timings: list[dict[str, Any]] = field(default_factory=list)
    peak_concurrency: int = 0
    wall_s: float = 0.0
    executed: int = 0
    failed: int = 0
    retried: int = 0
    cancelled: bool = False
    queued: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "executed": self.executed, "failed": self.failed,
            "retried": self.retried, "queued": self.queued,
            "peak_concurrency_measured": self.peak_concurrency,
            "wall_s": round(self.wall_s, 4), "wave_timings": self.wave_timings,
            "cancelled": self.cancelled,
        }


class ParallelExecutor:
    def __init__(self, registry: AgentRegistry, runner: AgentRunner,
                 store: Store, settings: Settings,
                 scheduler: TaskScheduler | None = None) -> None:
        self.registry = registry
        self.runner = runner
        self.store = store
        self.settings = settings
        self.scheduler = scheduler or TaskScheduler()
        self._semaphore = asyncio.Semaphore(settings.max_parallel_agents)
        self._active = 0
        self._peak = 0
        self._lock = asyncio.Lock()

    async def _enter(self) -> None:
        async with self._lock:
            self._active += 1
            self._peak = max(self._peak, self._active)

    async def _leave(self) -> None:
        async with self._lock:
            self._active -= 1

    async def execute(self, mission_id: str, waves: list[Wave], *, query: str,
                      plan: MissionPlan, mode: Mode, evidence: list[SourceRecord],
                      claims: list[Claim] | None = None,
                      data_origin: str = "live",
                      is_cancelled=None) -> ExecutionReport:
        started = time.perf_counter()
        report = ExecutionReport(queued=max(0, sum(len(w.steps) for w in waves)
                                            - self.settings.max_parallel_agents))
        if is_cancelled and is_cancelled():
            report.cancelled = True
            return report

        for wave in waves:
            if is_cancelled and is_cancelled():
                report.cancelled = True
                break
            wave_start = time.perf_counter()
            self.store.add_event(mission_id, "wave_started", "analyzing",
                                 wave=wave.index, name=wave.name,
                                 planned=len(wave.steps),
                                 max_parallel=self.settings.max_parallel_agents)
            wave_outputs = await self._run_wave(mission_id, wave, query, mode,
                                                evidence, claims or [], data_origin,
                                                report, is_cancelled)
            report.outputs.extend(wave_outputs)
            report.wave_timings.append({
                "wave": wave.index, "name": wave.name,
                "tasks": len(wave.steps),
                "ok": sum(1 for o in wave_outputs if o.status == "ok"),
                "failed": sum(1 for o in wave_outputs if o.status != "ok"),
                "wall_s": round(time.perf_counter() - wave_start, 4),
            })
            # Les vagues suivantes voient les affirmations déjà produites.
            claims = (claims or []) + []
        report.wall_s = time.perf_counter() - started
        report.peak_concurrency = self._peak
        report.executed = sum(1 for o in report.outputs if o.status == "ok")
        report.failed = sum(1 for o in report.outputs if o.status != "ok")
        self.store.record_metric("peak_agent_concurrency", report.peak_concurrency,
                                 mission_id)
        self.store.record_metric("agent_wave_wall_seconds", report.wall_s, mission_id)
        return report

    async def _run_wave(self, mission_id: str, wave: Wave, query: str, mode: Mode,
                        evidence: list[SourceRecord], claims: list[Claim],
                        data_origin: str, report: ExecutionReport,
                        is_cancelled) -> list[AgentOutput]:
        async def one(step, attempt: int = 1):
            if is_cancelled and is_cancelled():
                return None
            async with self._semaphore:
                await self._enter()
                try:
                    return await self._run_task(mission_id, step, query, mode,
                                                evidence, claims, data_origin, attempt)
                finally:
                    await self._leave()

        results = await asyncio.gather(*(one(s) for s in wave.steps),
                                       return_exceptions=True)
        outputs: list[AgentOutput] = []
        retries: list[tuple[Any, AgentOutput]] = []
        for step, result in zip(wave.steps, results):
            if result is None:
                continue
            if isinstance(result, BaseException):
                out = AgentOutput(agent_id=step.agent_id, division=step.division,
                                  status="failed", wave=wave.index,
                                  error=f"{type(result).__name__}: {result}"[:400])
                outputs.append(out)
                retries.append((step, out))
                continue
            outputs.append(result)
            if result.status != "ok":
                retries.append((step, result))
        if retries and self.scheduler.retry_attempts and not (is_cancelled and is_cancelled()):
            for step, _ in retries[: self.settings.max_parallel_agents]:
                if is_cancelled and is_cancelled():
                    break
                report.retried += 1
                retry = await one(step, attempt=2)
                if retry is not None and not isinstance(retry, BaseException):
                    outputs = [o for o in outputs if o.agent_id != step.agent_id] + [retry]
                else:
                    self.scheduler.record_dead_letter(step.agent_id, mission_id,
                                                      "échec après reprise")
        # Reprises synchronisées avec les lignes de tâches persistées.
        for out in outputs:
            if out.status != "ok":
                self.scheduler.record_dead_letter(out.agent_id, mission_id, out.error)
        return outputs

    async def _run_task(self, mission_id: str, step, query: str, mode: Mode,
                        evidence: list[SourceRecord], claims: list[Claim],
                        data_origin: str, attempt: int) -> AgentOutput:
        spec = self.registry.get(step.agent_id)
        task_id = f"{mission_id}-{step.agent_id}"
        started = time.perf_counter()
        existing = self.store.get(Task, task_id)
        if existing is None:
            self.store.add(Task(
                id=task_id, mission_id=mission_id, agent_id=step.agent_id,
                division=step.division, wave=step.wave, status="running",
                attempt=attempt, started_at=time.time(),
            ))
        else:
            self.store.update(Task, task_id, status="running", attempt=attempt,
                              started_at=time.time(), error="")
        self.store.add_event(mission_id, "agent_dispatched", "analyzing",
                             agent=step.agent_id, division=step.division,
                             wave=step.wave, attempt=attempt,
                             objective=step.objective[:200])
        ctx = self.runner.build_context(
            spec, mission_id=mission_id, query=query, mode=mode,
            evidence=evidence, claims=claims, wave=step.wave,
            data_origin=data_origin,
            extra={"relevance": step.relevance},
        )
        output = await self.runner.run(spec, ctx)
        output.wave = step.wave
        self.store.add_event(mission_id, "agent_result", "analyzing",
                             agent=step.agent_id, status=output.status,
                             wave=step.wave, findings=len(output.findings),
                             duration_ms=round(output.duration_ms, 2),
                             error=output.error[:200])
        self.store.update(Task, task_id, status=output.status,
                          attempt=attempt, finished_at=time.time(),
                          duration_ms=output.duration_ms,
                          output=output.to_dict(), error=output.error[:1000])
        self.store.record_metric("agent_duration_ms", output.duration_ms, mission_id,
                                 agent=step.agent_id)
        if output.status != "ok":
            log_event("executor", "task_failed", level="WARNING",
                      mission_id=mission_id, agent=step.agent_id, error=output.error[:120])
        return output
