"""Mission Planner : décompose une question complexe en missions spécialisées."""
from __future__ import annotations

from typing import Any

from ..agents.registry import AgentRegistry
from ..core.config import Settings
from ..core.schemas import MissionPlan, Mode, PlanStep
from .modes import MODE_CONFIG, effective_agent_count


class MissionPlanner:
    def __init__(self, registry: AgentRegistry, settings: Settings) -> None:
        self.registry = registry
        self.settings = settings

    def plan(self, query: str, mode: Mode,
             available_providers: list[str] | None = None,
             category: str = "general",
             options: dict[str, Any] | None = None) -> MissionPlan:
        options = options or {}
        cfg = MODE_CONFIG[mode]
        target = effective_agent_count(mode, self.settings)
        if options.get("max_agents"):
            target = min(target, max(1, int(options["max_agents"])))

        ranked = self.registry.select(query, mode)
        requested_divisions = options.get("divisions")
        if isinstance(requested_divisions, (list, tuple)) and requested_divisions:
            allowed = {str(d).upper() for d in requested_divisions}
            filtered = [pair for pair in ranked if pair[0].division_code in allowed]
            if filtered:
                ranked = filtered
        if mode == Mode.MAXIMUM:
            # Mobilisation adaptative : tous les profils pertinents, avec un
            # plancher par division pour garantir la couverture des 10 divisions.
            selected = [pair for pair in ranked if pair[1] > 0][:target]
            divisions = {s.division_code for s, _ in selected}
            for div in sorted({s.division_code for s in self.registry.specs}):
                if div not in divisions:
                    candidates = [pair for pair in ranked if pair[0].division_code == div]
                    if candidates:
                        selected.append(candidates[0])
            selected = sorted(selected, key=lambda p: (-p[1], p[0].id))[:target]
            # Les profils à pertinence nulle restent mobilisables : ils sont
            # ajoutés en fin de plan plutôt que déclarés « actifs » à tort.
            if len(selected) < target:
                chosen = {spec.id for spec, _ in selected}
                selected += [pair for pair in ranked
                             if pair[0].id not in chosen][: target - len(selected)]
        else:
            selected = ranked[:target]

        steps = [
            PlanStep(
                agent_id=spec.id, division=spec.division_code,
                objective=(f"Appliquer « {spec.name} » à la question : {query[:160]}. "
                           f"Mission : {spec.mission}"),
                relevance=score, wave=0,
            )
            for spec, score in selected
        ]
        provider_pool = available_providers or []
        providers = provider_pool[: cfg.provider_count] if cfg.cross_provider_search \
            else provider_pool[:1]
        reasoning = (
            f"Mode {cfg.name} : {len(steps)} agents sélectionnés par pertinence "
            f"sur 100 profils ({len({s.division for s in steps})} divisions), "
            f"{len(providers)} fournisseur(s) ciblé(s) pour la catégorie « {category} », "
            f"concurrence maximale {min(self.settings.max_parallel_agents, len(steps))}. "
            f"Les agents non simultanés sont mis en file, jamais déclarés actifs."
        )
        return MissionPlan(query=query, mode=mode, steps=steps,
                           providers=providers, reasoning=reasoning,
                           max_parallel=min(self.settings.max_parallel_agents, len(steps)))
