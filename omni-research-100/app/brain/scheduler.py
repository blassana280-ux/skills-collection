"""Task Scheduler : vagues, dépendances, priorités, reprises et file d'attente."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..core.schemas import MissionPlan, Mode, PlanStep
from .modes import MODE_CONFIG


@dataclass
class Wave:
    index: int
    name: str
    steps: list[PlanStep]
    depends_on: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.depends_on is None:
            self.depends_on = []


class TaskScheduler:
    def __init__(self, retry_attempts: int = 1) -> None:
        self.retry_attempts = retry_attempts
        self.dead_letter: list[dict[str, Any]] = []

    def build_waves(self, plan: MissionPlan) -> list[Wave]:
        cfg = MODE_CONFIG[plan.mode]
        division_to_wave: dict[str, int] = {}
        names: list[str] = []
        for index, group in enumerate(cfg.waves):
            names.append(" / ".join(group))
            for division in group:
                division_to_wave[division] = index
        by_wave: dict[int, list[PlanStep]] = {}
        for step in plan.steps:
            wave_index = division_to_wave.get(step.division, len(cfg.waves) - 1)
            step.wave = wave_index
            by_wave.setdefault(wave_index, []).append(step)
        waves: list[Wave] = []
        previous: list[str] = []
        for index in sorted(by_wave):
            steps = sorted(by_wave[index], key=lambda s: (-s.relevance, s.agent_id))
            for step in steps:
                step.depends_on = list(previous[:3])
            waves.append(Wave(index=index, name=names[index] if index < len(names)
                              else f"vague {index}", steps=steps,
                              depends_on=previous[:3]))
            previous = [s.agent_id for s in steps]
        # Le plan porte les numéros de vague attribués (traçabilité).
        plan.steps = [s for w in waves for s in w.steps]
        return waves

    def record_dead_letter(self, agent_id: str, mission_id: str, error: str) -> None:
        self.dead_letter.append({"agent_id": agent_id, "mission_id": mission_id,
                                 "error": error[:500]})

    def summary(self, waves: list[Wave]) -> dict[str, Any]:
        return {
            "waves": len(waves),
            "sizes": [len(w.steps) for w in waves],
            "total_tasks": sum(len(w.steps) for w in waves),
            "wave_names": [w.name for w in waves],
            "dead_letter": len(self.dead_letter),
        }
