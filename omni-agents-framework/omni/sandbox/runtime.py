"""Runtime continu (scheduler simple) + RBAC + logs persistants (Phase 3.3).

Aucune dépendance Agno/APScheduler : ``Runtime.start()`` est un scheduler borné,
traçable et testable. Les actions irréversibles sont refusées aux rôles machine ;
seule l'identité humaine ``Lassana`` avec approbation explicite peut les autoriser.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "viewer": frozenset({"read", "list", "report"}),
    "operator": frozenset({"read", "list", "report", "plan", "run_mission", "record", "sandbox_local"}),
    "reviewer": frozenset({"read", "list", "report", "review", "approve_gate", "record"}),
    "admin": frozenset({"read", "list", "report", "plan", "run_mission", "record", "configure", "review"}),
    "human": frozenset({"read", "list", "report", "approve_gate", "merge_pr", "force_push", "delete_branch", "write_main"}),
}

IRREVERSIBLE = frozenset({
    "merge_pr", "force_push", "delete_repo", "delete_branch", "rotate_secret", "write_main",
})


class RBAC:
    """Contrôle d'accès basique, déterministe, sans source externe."""

    def __init__(self, actors: dict[str, str] | None = None):
        self._actors = {"Lassana": "human", "lassana": "human"}
        self._actors.update(actors or {})

    def role_of(self, actor: str) -> str:
        return self._actors.get(actor, "viewer")

    def assign(self, actor: str, role: str) -> None:
        if role not in ROLE_PERMISSIONS:
            raise ValueError(f"rôle inconnu : {role}")
        self._actors[actor] = role

    def allow(self, actor: str, action: str, *, human_approval: bool = False) -> bool:
        role = self.role_of(actor)
        if action in IRREVERSIBLE:
            # « Toute fusion de PR reste à Lassana » : jamais une machine.
            return role == "human" and human_approval and actor.lower() == "lassana"
        return action in ROLE_PERMISSIONS.get(role, frozenset())

    def check(self, actor: str, action: str, *, human_approval: bool = False) -> None:
        if not self.allow(actor, action, human_approval=human_approval):
            raise PermissionError(
                f"action refusée : actor={actor!r} role={self.role_of(actor)!r} action={action!r}"
            )


@dataclass
class RuntimeConfig:
    interval_s: float = 1.0
    max_ticks: int = 1
    artifacts_dir: str | None = None


@dataclass
class Runtime:
    """Mode service : file de missions -> graphe -> mémoire + logs persistants."""

    store: Any
    rbac: RBAC = field(default_factory=RBAC)
    config: RuntimeConfig = field(default_factory=RuntimeConfig)
    queue: list[dict[str, Any]] = field(default_factory=list, repr=False)
    stopped: bool = False

    def __post_init__(self) -> None:
        self.rbac.assign("omnibrain-service", "operator")
        self.store.log("omnibrain-service", "runtime", "service_start", self.config.__dict__)

    def submit(
        self,
        spec: str,
        *,
        project_type: str = "generic",
        actor: str = "omnibrain-service",
        approvals: dict[str, bool] | None = None,
    ) -> str:
        self.rbac.check(actor, "run_mission")
        mission_id = self.store.record_mission(
            {"project_type": project_type, "title": spec[:80], "spec": spec, "status": "queued"}
        )
        self.queue.append({"mission_id": mission_id, "approvals": dict(approvals or {})})
        self.store.log(actor, self.rbac.role_of(actor), "submit", {"mission_id": mission_id})
        return mission_id

    def tick(self) -> list[str]:
        """Traite une mission ; un gate non approuvé reste en escalade Lassana."""
        from ..graph.pipeline import run_pipeline

        if self.stopped or not self.queue:
            self.store.log("omnibrain-service", "runtime", "tick_idle", {"queue": len(self.queue)})
            return []
        job = self.queue.pop(0)
        mission = self.store.get_mission(job["mission_id"]) or {}
        self.store.log("omnibrain-service", "runtime", "tick_start", {"mission_id": job["mission_id"]})
        result = run_pipeline(
            mission.get("spec", ""), project_type=mission.get("project_type", "generic"),
            mission_id=job["mission_id"], approvals=job["approvals"], store=self.store,
            artifacts_dir=self.config.artifacts_dir,
        )
        self.store.log(
            "omnibrain-service", "runtime", "tick_done",
            {"mission_id": job["mission_id"], "verdict": result.state.verdict,
             "pending_human": result.state.pending_human},
        )
        return [job["mission_id"]]

    def start(self, *, continuous: bool = False) -> int:
        """Scheduler borné : ``max_ticks`` itérations, jamais de boucle infinie en CI."""
        processed = 0
        limit = 10_000 if continuous and self.config.max_ticks <= 0 else self.config.max_ticks
        for _ in range(max(0, limit)):
            if self.stopped:
                break
            handled = self.tick()
            processed += len(handled)
            if not handled and not continuous:
                break
            if continuous and self.config.interval_s > 0:
                time.sleep(self.config.interval_s)
        self.store.log("omnibrain-service", "runtime", "service_stop", {"processed": processed})
        return processed

    def stop(self) -> None:
        self.stopped = True


def main(argv: list[str] | None = None) -> int:
    import argparse

    from ..memory.store import get_store

    parser = argparse.ArgumentParser(prog="python3 -m omni.sandbox.runtime", description="Runtime OmniBrain v4")
    parser.add_argument("--max-ticks", type=int, default=1)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--continuous", action="store_true")
    parser.add_argument("--artifacts-dir", default=os.environ.get("OMNIBRAIN_ARTIFACTS"))
    args = parser.parse_args(argv)
    store = get_store()
    runtime = Runtime(
        store=store,
        config=RuntimeConfig(
            interval_s=args.interval, max_ticks=args.max_ticks, artifacts_dir=args.artifacts_dir
        ),
    )
    count = runtime.start(continuous=args.continuous)
    print(f"runtime arrêté : {count} mission(s) traitée(s), {len(store.logs())} entrées de log")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
