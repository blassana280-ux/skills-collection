#!/usr/bin/env python3
"""Suite de benchmarks OmniBrain v4 (Phase 4.2).

10 tâches de référence **figées** (``task_fingerprint``) : toute modification
du jeu de référence casse l'empreinte et donc l'historique. Chaque exécution
mesure le taux d'activation attendu, la latence de routage, le nombre d'agents
sélectionnés et une estimation de tokens ; les gains sont calculés contre la
première exécution de même empreinte et historisés en JSONL + SQLite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from omnibrain.classifier import Classifier  # noqa: E402
from omnibrain.config import load_matrix  # noqa: E402
from omnibrain.registry import Registry  # noqa: E402
from omnibrain.router import Router  # noqa: E402

DEFAULT_HISTORY = ROOT / "var" / "benchmark_history.jsonl"


@dataclass(frozen=True)
class BenchmarkTask:
    id: str
    project_type: str
    query: str
    expected_id: str
    complexity: str


BENCHMARK_TASKS: tuple[BenchmarkTask, ...] = (
    BenchmarkTask("B01", "security", "Audit pentest de l'API avec test d'intrusion", "pentester", "medium"),
    BenchmarkTask("B02", "fintech", "Intégration du paiement Orange Money et Wave avec KYC", "mobile-money-fintech", "complex"),
    BenchmarkTask("B03", "localisation", "Traduction et localisation en bambara bamanankan des SMS", "localization-bambara", "simple"),
    BenchmarkTask("B04", "cloud", "Déploiement Terraform et durcissement du cluster Kubernetes", "terraform-iac", "complex"),
    BenchmarkTask("B05", "qa", "Test de charge k6 pour mesurer la latence p95", "performance-testing", "medium"),
    BenchmarkTask("B06", "finance", "Optimisation fiscale et prix de transfert du groupe", "tax-planner", "medium"),
    BenchmarkTask("B07", "observability", "Instrumentation des vagues avec télémétrie json et rapport de mission", "observability-telemetry", "medium"),
    BenchmarkTask("B08", "memory", "Mémoire sqlite et recettes par projet pour l'historique des missions", "memory-sqlite", "medium"),
    BenchmarkTask("B09", "governance", "Gate humaine et escalade lassana pour plan de fusion", "risk-gate-keeper", "complex"),
    BenchmarkTask("B10", "accessibility", "Tests d'accessibilité WCAG et automatisation Playwright", "accessibility-testing", "medium"),
)


def task_fingerprint() -> str:
    payload = json.dumps([asdict(t) for t in BENCHMARK_TASKS], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_once(root: Path = ROOT) -> dict[str, Any]:
    """Une passe de mesure réelle sur le routeur (aucune simulation)."""
    matrix = load_matrix(root)
    router = Router(Registry(root=root, matrix=matrix), Classifier(matrix))
    details: list[dict[str, Any]] = []
    for task in BENCHMARK_TASKS:
        started = time.perf_counter()
        decision = router.route(task.query)
        elapsed = (time.perf_counter() - started) * 1000
        ids = [a.id for a in decision.agents]
        details.append({
            "id": task.id,
            "expected_id": task.expected_id,
            "hit": task.expected_id in ids,
            "routed": ids,
            "latency_ms": round(elapsed, 4),
            "tokens_estimate": len(task.query.split()) + len(ids) * 12,
        })
    hits = sum(1 for d in details if d["hit"])
    return {
        "fingerprint": task_fingerprint(),
        "tasks": len(BENCHMARK_TASKS),
        "hits": hits,
        "hit_rate": round(hits / len(BENCHMARK_TASKS), 4),
        "mean_latency_ms": round(sum(d["latency_ms"] for d in details) / len(details), 4),
        "routed_agents": sum(len(d["routed"]) for d in details),
        "tokens_estimate": sum(d["tokens_estimate"] for d in details),
        "wave_count": 1,
        "measured_at": _ts(),
        "details": details,
    }


def read_history(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def compute_gains(current: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    same = [h for h in history if h.get("fingerprint") == current["fingerprint"]]
    if not same:
        return {"baseline": None, "gain_latency_pct": 0.0, "gain_hit_rate_pp": 0.0, "runs_in_history": 0}
    base = same[0]["metrics"]
    base_latency = float(base["mean_latency_ms"]) or 1.0
    return {
        "baseline": base["measured_at"],
        "gain_latency_pct": round((base_latency - current["mean_latency_ms"]) / base_latency * 100, 4),
        "gain_hit_rate_pp": round((current["hit_rate"] - float(base["hit_rate"])) * 100, 4),
        "runs_in_history": len(same),
    }


def run_benchmark(
    *, runs: int = 1, history_path: Path = DEFAULT_HISTORY, store: Any | None = None, write: bool = True
) -> dict[str, Any]:
    history = read_history(history_path)
    passes = [run_once() for _ in range(max(1, runs))]
    current = dict(passes[-1])
    current["mean_latency_ms"] = round(sum(p["mean_latency_ms"] for p in passes) / len(passes), 4)
    current["hit_rate"] = round(sum(p["hit_rate"] for p in passes) / len(passes), 4)
    current["details"] = passes[-1]["details"]
    gains = compute_gains(current, history)
    record = {"run_id": uuid.uuid4().hex[:12], "ts": _ts(), "fingerprint": current["fingerprint"], "metrics": current, "gains": gains}
    if write:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with history_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    if store is not None:
        store.record_benchmark(record["run_id"], current["fingerprint"], {**current, "gains": gains, "run_id": record["run_id"]})
    return {"record": record, "passes": len(passes), "history_path": str(history_path)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmarks de routage OmniBrain v4")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--history", default=str(DEFAULT_HISTORY))
    parser.add_argument("--no-write", action="store_true", help="mesure sans historisation (CI)")
    parser.add_argument("--json", dest="json_out", help="écrit le bilan complet à ce chemin")
    args = parser.parse_args(argv)

    result = run_benchmark(runs=args.runs, history_path=Path(args.history), write=not args.no_write)
    metrics = result["record"]["metrics"]
    print(json.dumps({
        "fingerprint": metrics["fingerprint"],
        "tasks": metrics["tasks"],
        "hit_rate": metrics["hit_rate"],
        "mean_latency_ms": metrics["mean_latency_ms"],
        "gains": result["record"]["gains"],
        "passes": result["passes"],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if metrics["hits"] == metrics["tasks"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
