"""Pipeline complet : plan → recherche → preuves → agents → vérification →
consensus → arbitrage → synthèse → rapport. Chaque étape est tracée.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Callable

from ..core.db import Mission
from ..core.errors import MissionCancelled
from ..core.logging_conf import log_event
from ..core.schemas import MissionStatus, Mode
from .modes import MODE_CONFIG, mode_summary


class ResearchPipeline:
    def __init__(self, runtime: Any) -> None:
        self.rt = runtime

    async def submit(self, query: str, mode: Mode, owner: str = "system",
                     options: dict[str, Any] | None = None) -> tuple[str, asyncio.Task]:
        """Crée la mission puis lance son exécution en tâche de fond."""
        options = dict(options or {})
        mission_id = self.rt.commander.create(query, mode, owner, options)
        await self.rt.memory.queue.put(mission_id, {"mode": mode.value,
                                                    "query": query[:200]})
        task = asyncio.create_task(self.run(mission_id, query, mode, options),
                                   name=f"mission-{mission_id}")
        self.rt.tasks[mission_id] = task
        return mission_id, task

    async def run(self, mission_id: str, query: str, mode: Mode,
                  options: dict[str, Any] | None = None) -> dict[str, Any]:
        options = options or {}
        rt = self.rt
        cmd = rt.commander
        cfg = MODE_CONFIG[mode]
        data_origin = str(options.get("data_origin", "live"))
        started = time.perf_counter()
        async with cmd.slot(mission_id):
            try:
                self._check_cancel(mission_id)
                cmd.stage(mission_id, MissionStatus.PLANNING, "planning", 0.05)

                category = rt.router.category_for(query)
                available = [
                    name for name in rt.router.rank(category)
                    if (p := rt.router.registry.get(name)) is not None
                    and p.is_configured() and name not in rt.router.disabled
                ]
                plan = rt.planner.plan(query, mode, available, category, options)
                waves = rt.scheduler.build_waves(plan)
                rt.store.update(Mission, mission_id, plan=plan.to_dict())
                cmd.emit(mission_id, "mission_planned", "planning",
                         agents=len(plan.steps), waves=len(waves),
                         providers=plan.providers,
                         max_parallel=plan.max_parallel,
                         reasoning=plan.reasoning[:400])

                # -- recherche Internet réelle --------------------------------
                self._check_cancel(mission_id)
                cmd.stage(mission_id, MissionStatus.SEARCHING, "searching", 0.18)
                limit = min(cfg.max_sources,
                            rt.settings.max_sources_per_mission,
                            int(options.get("max_sources") or 10 ** 6))
                outcome = await rt.router.search(
                    query, mission_id=mission_id, limit=limit,
                    language=str(options.get("language", "fr")),
                    category=category,
                    provider_names=plan.providers or None,
                    max_providers=cfg.provider_count,
                    verify_http=bool(rt.settings.dns_ssrf_check
                                     and rt.settings.env not in {"test", "offline"}),
                )
                cmd.emit(mission_id, "search_completed", "searching",
                         sources=len(outcome.sources),
                         providers=outcome.providers_used,
                         errors=outcome.errors[:6],
                         dedup_removed=outcome.dedup_removed)
                bundle = rt.collector.collect(outcome, mission_id)

                # -- extraction ----------------------------------------------
                if outcome.sources and cfg.extractions and data_origin == "live" \
                        and not options.get("skip_extraction"):
                    self._check_cancel(mission_id)
                    cmd.stage(mission_id, MissionStatus.EXTRACTING, "extracting", 0.32)
                    outcome.extracted = await rt.router.extract_pages(
                        bundle.docs, mission_id,
                        limit=min(cfg.extractions,
                                  rt.settings.max_extractions_per_mission))
                    cmd.emit(mission_id, "extraction_completed", "extracting",
                             pages=outcome.extracted)

                # -- exécution des agents -------------------------------------
                self._check_cancel(mission_id)
                cmd.stage(mission_id, MissionStatus.ANALYZING, "analyzing", 0.45,
                          planned=len(plan.steps))
                execution = await rt.executor.execute(
                    mission_id, waves, query=query, plan=plan, mode=mode,
                    evidence=bundle.docs, data_origin=data_origin,
                    is_cancelled=lambda: cmd.cancelled(mission_id),
                )
                self._check_cancel(mission_id)
                cmd.emit(mission_id, "agents_completed", "analyzing",
                         executed=execution.executed, failed=execution.failed,
                         peak_concurrency=execution.peak_concurrency,
                         wall_s=round(execution.wall_s, 3))

                # -- vérification / consensus / arbitrage ----------------------
                cmd.stage(mission_id, MissionStatus.VERIFYING, "verifying", 0.72)
                verification = rt.verifier.verify(execution.outputs, bundle.docs,
                                                  mission_id, cfg.verification_passes)
                consensus = rt.consensus.evaluate(verification.claims,
                                                  execution.outputs, bundle.docs)
                if cfg.contradiction_analysis:
                    conflicts = rt.conflicts.resolve(verification.claims,
                                                     execution.outputs, bundle.docs,
                                                     mission_id,
                                                     deep=cfg.contradiction_deep)
                else:
                    from .conflict_resolver import ConflictReport
                    conflicts = ConflictReport()
                # Contradictions éventuelles signalées par les agents FACT.
                for claim in verification.claims:
                    if claim.status == "contested":
                        claim.contradict_ids.append("signals")

                # -- synthèse --------------------------------------------------
                self._check_cancel(mission_id)
                cmd.stage(mission_id, MissionStatus.SYNTHESIZING, "synthesizing", 0.86)
                synthesis = await rt.synthesizer.synthesize(
                    query, mode, verification.claims, conflicts.contradictions,
                    bundle.citations, bundle.citation_by_id,
                )
                cmd.stage(mission_id, MissionStatus.REPORTING, "reporting", 0.94)
                report = rt.reports.generate(
                    mission_id=mission_id, query=query, mode=mode, plan=plan,
                    outcome=outcome, bundle=bundle, execution=execution,
                    verification=verification, consensus=consensus,
                    conflicts=conflicts, synthesis=synthesis,
                    provider_status=rt.router.status(),
                    data_origin=data_origin, mode_summary=mode_summary(mode, rt.settings),
                )
                status = (MissionStatus.COMPLETED if bundle.docs
                          else MissionStatus.INSUFFICIENT_EVIDENCE)
                cmd.complete(mission_id, status, report.verdict.value, 1.0)
                await rt.memory.remember(query, mode.value, mission_id,
                                         {"verdict": report.verdict.value,
                                          "sources": len(bundle.docs)})
                rt.store.record_metric("mission_wall_seconds",
                                       time.perf_counter() - started, mission_id)
                rt.store.audit("system", "mission_completed", mission_id,
                               verdict=report.verdict.value,
                               sources=len(bundle.docs))
                return {
                    "mission_id": mission_id, "status": status.value,
                    "verdict": report.verdict.value, "gates": report.gates,
                    "sources": len(bundle.docs), "agents": execution.executed,
                    "providers": outcome.providers_used,
                    "wall_s": round(time.perf_counter() - started, 3),
                }
            except MissionCancelled:
                cmd.emit(mission_id, "mission_stopped", "cancelled")
                return {"mission_id": mission_id, "status": "cancelled"}
            except Exception as exc:
                cmd.fail(mission_id, f"{type(exc).__name__}: {exc}")
                log_event("pipeline", "mission_failed", level="ERROR",
                          mission_id=mission_id, error_type=type(exc).__name__)
                return {"mission_id": mission_id, "status": "failed",
                        "error": f"{type(exc).__name__}: {exc}"[:500]}
            finally:
                self.rt.tasks.pop(mission_id, None)

    def _check_cancel(self, mission_id: str) -> None:
        if self.rt.commander.cancelled(mission_id):
            raise MissionCancelled(f"Mission {mission_id} annulée")
