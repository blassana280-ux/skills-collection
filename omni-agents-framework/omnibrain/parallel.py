"""Exécution parallèle de plusieurs plans d'orchestration.

Chaque demande est traitée par un **processus indépendant** et produit sa
propre vague de briefs (wave 0) : il n'y a aucun séquençage entre demandes,
conformément au manifeste OmniBrain (« dispatcher en une seule vague
parallèle, jamais séquentiel »).

Le worker reste une fonction de niveau module pour être picklable par
``ProcessPoolExecutor``.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass


def _build_plan(task: str) -> dict:
    """Worker : construit le plan complet d'une demande (isolat de contexte)."""
    from .dispatcher import Dispatcher

    return Dispatcher().plan(task).as_dict()


@dataclass
class ParallelRun:
    plans: list[dict]
    workers: int
    parallel_seconds: float
    sequential_seconds: float

    @property
    def speedup(self) -> float:
        if self.parallel_seconds <= 0:
            return 0.0
        return self.sequential_seconds / self.parallel_seconds

    def coverage(self) -> dict[str, list[int]]:
        """Agent -> indices des plans qui le mobilisent."""
        index: dict[str, list[int]] = {}
        for i, plan in enumerate(self.plans):
            for agent in plan["squad"]:
                index.setdefault(agent["id"], []).append(i)
        return index

    def total_briefs(self) -> int:
        return sum(len(plan["briefs"]) for plan in self.plans)

    def active_contracts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for plan in self.plans:
            for contract in plan["contracts"]:
                counts[contract["artifact"]] = counts.get(contract["artifact"], 0) + 1
        return counts

    def classifications(self) -> list[str]:
        return [plan["classification"]["level"] for plan in self.plans]


def run_plans_parallel(tasks: list[str], max_workers: int | None = None) -> ParallelRun:
    """Lance les plans en parallèle (vrais processus), puis mesure le séquentiel.

    La mesure séquentielle sert de base de comparaison honnête : le routage
    lui-même est rapide, le gain parallèle devient déterminant quand les
    agents exécutent de vrais travaux (appels d'outils, E/S, génération).
    """
    tasks = list(tasks)
    if not tasks:
        raise ValueError("au moins une demande est requise")
    workers = max_workers or min(len(tasks), os.cpu_count() or 2)
    workers = max(1, min(workers, len(tasks)))

    parallel_start = time.perf_counter()
    plans: list[dict | None] = [None] * len(tasks)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_build_plan, task): i for i, task in enumerate(tasks)}
        for future in as_completed(futures):
            plans[futures[future]] = future.result()
    parallel_seconds = time.perf_counter() - parallel_start

    sequential_start = time.perf_counter()
    for task in tasks:
        _build_plan(task)
    sequential_seconds = time.perf_counter() - sequential_start

    return ParallelRun(
        plans=[plan for plan in plans if plan is not None],
        workers=workers,
        parallel_seconds=parallel_seconds,
        sequential_seconds=sequential_seconds,
    )
