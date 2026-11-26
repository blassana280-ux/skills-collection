"""Assemblage du runtime complet (utilisé par l'API et les tests)."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

from .agents.registry import AgentRegistry
from .agents.runner import AgentRunner
from .brain.claim_verifier import ClaimVerifier
from .brain.commander import ResearchCommander
from .brain.conflict_resolver import ConflictResolver
from .brain.consensus import ConsensusEngine
from .brain.evidence_collector import EvidenceCollector
from .brain.executor import ParallelExecutor
from .brain.pipeline import ResearchPipeline
from .brain.planner import MissionPlanner
from .brain.report_generator import ReportGenerator
from .brain.scheduler import TaskScheduler
from .brain.synthesizer import ResearchSynthesizer
from .brain.modes import mode_summary
from .core.config import Settings, get_settings
from .core.db import Store
from .core.logging_conf import configure_logging
from .core.memory import ResearchMemory, make_queue, make_vector_index
from .core.schemas import Mode
from .core.security import RateLimiter
from .providers.models import ModelRouter
from .providers.registry import ProviderRegistry
from .providers.router import ProviderRouter


@dataclass
class Runtime:
    settings: Settings
    store: Store
    memory: ResearchMemory
    queue: Any
    vector_index: Any
    registry: AgentRegistry
    provider_registry: ProviderRegistry
    router: ProviderRouter
    model_router: ModelRouter
    runner: AgentRunner
    commander: ResearchCommander
    planner: MissionPlanner
    scheduler: TaskScheduler
    executor: ParallelExecutor
    collector: EvidenceCollector
    verifier: ClaimVerifier
    consensus: ConsensusEngine
    conflicts: ConflictResolver
    synthesizer: ResearchSynthesizer
    reports: ReportGenerator
    pipeline: ResearchPipeline
    limiter: RateLimiter
    tasks: dict[str, asyncio.Task] = field(default_factory=dict)

    def status(self) -> dict[str, Any]:
        return {
            "version": "1.0.0",
            "memory": self.memory.describe(),
            "agents": self.registry.validate(),
            "providers": self.router.status(),
            "models": self.model_router.describe(),
            "modes": {mode.value: mode_summary(mode, self.settings) for mode in Mode},
            "settings": self.settings.public_dict(),
            "active_missions": sorted(self.commander.active),
            "database_stats": self.store.stats(),
        }

    def close(self) -> None:
        self.store.close()


def build_runtime(
    settings: Settings | None = None,
    *,
    store: Store | None = None,
    client_factory: Callable[[], httpx.AsyncClient] | None = None,
    extra_providers: list[Any] | None = None,
    provider_plugins: bool = True,
    init_db: bool = True,
) -> Runtime:
    """Construit toutes les briques. Les tests injectent `store`,
    `client_factory` (MockTransport) et des connecteurs de fixture explicites."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    store = store or Store(
        settings.database_url,
        admin_password=settings.admin_password,
        user_password=settings.user_password,
    )
    if init_db:
        store.init()

    queue = make_queue(settings.redis_url)
    vector_index = make_vector_index(store, settings.qdrant_url,
                                     settings.qdrant_collection)
    memory = ResearchMemory(store, queue, vector_index, settings.retention_days)

    registry = AgentRegistry()
    provider_registry = ProviderRegistry(settings, plugins=provider_plugins)
    for provider in extra_providers or []:
        provider_registry.register(provider)
    router = ProviderRouter(settings, store, provider_registry,
                            client_factory=client_factory)
    disabled = store.get_setting("disabled_providers", []) or []
    router.set_disabled(list(disabled))
    quota_overrides = store.get_setting("quota_overrides", {}) or {}
    router.quota.overrides = {str(k): int(v) for k, v in quota_overrides.items()}

    model_router = ModelRouter(settings, client_factory=client_factory)
    runner = AgentRunner(registry, store, memory, model_router)
    commander = ResearchCommander(store, settings)
    planner = MissionPlanner(registry, settings)
    scheduler = TaskScheduler(retry_attempts=1)
    executor = ParallelExecutor(registry, runner, store, settings, scheduler)
    collector = EvidenceCollector(store)
    verifier = ClaimVerifier(store)
    consensus = ConsensusEngine()
    conflicts = ConflictResolver(store)
    synthesizer = ResearchSynthesizer(model_router)
    reports = ReportGenerator(store, settings)
    limiter = RateLimiter(settings.rate_limit_per_minute)

    rt = Runtime(
        settings=settings, store=store, memory=memory, queue=queue,
        vector_index=vector_index, registry=registry,
        provider_registry=provider_registry, router=router,
        model_router=model_router, runner=runner, commander=commander,
        planner=planner, scheduler=scheduler, executor=executor,
        collector=collector, verifier=verifier, consensus=consensus,
        conflicts=conflicts, synthesizer=synthesizer, reports=reports,
        pipeline=None,  # type: ignore[arg-type]
        limiter=limiter,
    )
    rt.pipeline = ResearchPipeline(rt)
    return rt
