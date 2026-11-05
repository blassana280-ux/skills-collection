"""Instrumentation des vagues : durée par agent, tokens, taux d'échec.

Export JSON (source de vérité) + rapport markdown auto-généré par mission.
Le markdown est toujours dérivé du JSON : aucune divergence possible.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class AgentMetric:
    agent_id: str
    wave: int = 0
    duration_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    status: str = "ok"
    verdict: str = "PASS"
    error: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id, "wave": self.wave,
            "duration_ms": round(self.duration_ms, 3),
            "tokens_in": self.tokens_in, "tokens_out": self.tokens_out,
            "status": self.status, "verdict": self.verdict, "error": self.error,
        }


@dataclass
class WaveTelemetry:
    mission_id: str
    project_type: str = "generic"
    started_at: str = field(default_factory=_ts)
    _metrics: dict[str, AgentMetric] = field(default_factory=dict, repr=False)
    _running: dict[str, float] = field(default_factory=dict, repr=False)

    # ------------------------------------------------------------- collecte
    def start_agent(self, agent_id: str, wave: int = 0) -> None:
        self._running[agent_id] = time.perf_counter()
        self._metrics.setdefault(agent_id, AgentMetric(agent_id=agent_id, wave=wave))

    def end_agent(
        self,
        agent_id: str,
        *,
        status: str = "ok",
        verdict: str = "PASS",
        tokens_in: int = 0,
        tokens_out: int = 0,
        error: str = "",
    ) -> AgentMetric:
        started = self._running.pop(agent_id, None)
        elapsed = (time.perf_counter() - started) * 1000 if started is not None else 0.0
        metric = self._metrics.setdefault(agent_id, AgentMetric(agent_id=agent_id))
        metric.duration_ms += elapsed
        metric.tokens_in += int(tokens_in)
        metric.tokens_out += int(tokens_out)
        metric.status = status
        metric.verdict = verdict
        metric.error = error
        return metric

    def record(
        self,
        agent_id: str,
        *,
        wave: int = 0,
        duration_ms: float = 0.0,
        tokens_in: int = 0,
        tokens_out: int = 0,
        status: str = "ok",
        verdict: str = "PASS",
        error: str = "",
    ) -> AgentMetric:
        """Upsert déterministe : un agent = une ligne, même si plusieurs events."""
        metric = self._metrics.get(agent_id)
        if metric is None:
            metric = AgentMetric(agent_id=agent_id, wave=wave)
            self._metrics[agent_id] = metric
        metric.wave = wave or metric.wave
        metric.duration_ms += float(duration_ms)
        metric.tokens_in += int(tokens_in)
        metric.tokens_out += int(tokens_out)
        metric.status = status
        metric.verdict = verdict
        metric.error = error
        return metric

    # -------------------------------------------------------------- agrégats
    def summary(self) -> dict[str, Any]:
        metrics = [self._metrics[k].as_dict() for k in sorted(self._metrics)]
        total = len(metrics)
        failures = sum(1 for m in metrics if m["status"] != "ok" or m["verdict"] != "PASS" or m["error"])
        waves = sorted({m["wave"] for m in metrics})
        return {
            "mission_id": self.mission_id,
            "project_type": self.project_type,
            "started_at": self.started_at,
            "generated_at": _ts(),
            "agents": metrics,
            "waves": waves,
            "totals": {
                "agents": total,
                "failures": failures,
                "failure_rate": round(failures / total, 4) if total else 0.0,
                "duration_ms": round(sum(m["duration_ms"] for m in metrics), 3),
                "tokens_in": sum(m["tokens_in"] for m in metrics),
                "tokens_out": sum(m["tokens_out"] for m in metrics),
                "tokens_total": sum(m["tokens_in"] + m["tokens_out"] for m in metrics),
            },
            "reinforcements": {
                "revue_adverse": "revue_adverse" in self._metrics,
                "tests": "tests" in self._metrics,
                "expert_risque": "verification" in self._metrics,
            },
        }

    # --------------------------------------------------------------- exports
    def export_json(self, path: str | Path | None = None) -> dict[str, Any]:
        payload = self.summary()
        if path is not None:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return payload

    def render_markdown(self) -> str:
        s = self.summary()
        t = s["totals"]
        lines = [
            f"# Rapport de mission — `{s['mission_id']}`",
            "",
            f"- **Type de projet :** `{s['project_type']}`",
            f"- **Début :** {s['started_at']} · **Généré :** {s['generated_at']}",
            f"- **Vagues :** {', '.join(str(w) for w in s['waves']) or 'aucune'}",
            "",
            "## Totaux",
            "",
            "| Mesure | Valeur |",
            "| --- | --- |",
            f"| Agents instrumentés | {t['agents']} |",
            f"| Échecs | {t['failures']} |",
            f"| Taux d'échec | {t['failure_rate']:.2%} |",
            f"| Durée cumulée | {t['duration_ms']:.1f} ms |",
            f"| Tokens entrée / sortie | {t['tokens_in']} / {t['tokens_out']} |",
            f"| Tokens totaux | {t['tokens_total']} |",
            "",
            "## Par agent",
            "",
            "| Agent | Vague | Durée (ms) | Tokens in | Tokens out | Statut | Verdict |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for m in s["agents"]:
            lines.append(
                f"| `{m['agent_id']}` | {m['wave']} | {m['duration_ms']:.1f} | "
                f"{m['tokens_in']} | {m['tokens_out']} | {m['status']} | {m['verdict']} |"
            )
        if not s["agents"]:
            lines.append("| _aucun agent_ | — | 0.0 | 0 | 0 | — | — |")
        lines += [
            "",
            "## Renforts obligatoires",
            "",
        ]
        for key, label in (("revue_adverse", "Revue adverse"), ("tests", "QA / tests"), ("expert_risque", "Expert risque")):
            lines.append(f"- {label} : {'présent' if s['reinforcements'][key] else 'ABSENT'}") 
        lines += [
            "",
            "> Rapport dérivé du JSON de télémétrie. Aucune valeur rédigée à la main.",
            "",
        ]
        return "\n".join(lines)


def from_memory(store: Any, mission_id: str) -> WaveTelemetry:
    """Reconstruit la télémétrie depuis les résultats persistés en base."""
    mission = store.get_mission(mission_id) or {}
    telemetry = WaveTelemetry(mission_id, project_type=mission.get("project_type", "generic"))
    for row in store.results_for(mission_id):
        telemetry.record(
            row["agent_id"], wave=1, duration_ms=float(row["duration_ms"]),
            tokens_in=int(row["tokens_in"]), tokens_out=int(row["tokens_out"]),
            status=row["status"], verdict=row["verdict"],
        )
    return telemetry


def write_mission_report(telemetry: WaveTelemetry, directory: str | Path) -> tuple[Path, Path]:
    """Écrit le JSON et le markdown d'une mission ; retourne les deux chemins."""
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"telemetry-{telemetry.mission_id}.json"
    md_path = out / f"rapport-mission-{telemetry.mission_id}.md"
    telemetry.export_json(json_path)
    md_path.write_text(telemetry.render_markdown(), encoding="utf-8")
    return json_path, md_path
