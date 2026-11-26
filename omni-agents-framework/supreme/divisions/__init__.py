"""Chargement des 20 divisions SUPREME (50 spécialisations chacune).

Chaque module ``divNN`` exporte ``META`` (métadonnées de division) et ``ROWS``
(50 chaînes compactes ``slug|titre|objectif|comp1;comp2;comp3|tâche|évaluation[|tool=x][|risk=y]``).
Les données sont la source de vérité versionnée ; le catalogue JSON est généré.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Division:
    num: int
    slug: str
    title: str
    mission: str
    risk: str
    models: tuple[str, ...]
    tools: tuple[str, ...]
    partners: tuple[int, ...]
    secondary: tuple[str, ...]
    inputs: tuple[str, ...]
    output: str
    protocol: str

    @property
    def id(self) -> str:
        return f"D{self.num:02d}"

    @property
    def manager_id(self) -> str:
        return f"M{self.num:02d}-{self.slug}-chief"


def load_divisions() -> list[Division]:
    out: list[Division] = []
    for n in range(1, 21):
        mod = importlib.import_module(f"supreme.divisions.div{n:02d}")
        m = mod.META
        rows = mod.ROWS
        if len(rows) != 50:
            raise ValueError(f"division {n:02d}: {len(rows)} lignes, 50 attendues")
        out.append(Division(
            num=m["num"], slug=m["slug"], title=m["title"], mission=m["mission"],
            risk=m.get("risk", "low"), models=tuple(m["models"]),
            tools=tuple(m["tools"]), partners=tuple(m.get("partners", [])),
            secondary=tuple(m.get("secondary", [])), inputs=tuple(m["inputs"]),
            output=m["output"], protocol=m["protocol"],
        ))
    return out


def load_rows() -> dict[int, list[str]]:
    return {
        n: list(importlib.import_module(f"supreme.divisions.div{n:02d}").ROWS)
        for n in range(1, 21)
    }
