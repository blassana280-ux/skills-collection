"""Helper de test LOCAL RÉEL : worker subprocess avec outil ralenti instrumenté.

Non découvert par unittest (préfixe `_`). Utilisé uniquement par les tests de
concurrence/crash pour observer le démarrage d'une mission pendant qu'un autre
worker démarre, sans simuler de fournisseur IA.
"""
from __future__ import annotations

import json
import os
import signal
import threading
import time
from pathlib import Path

import supreme.orchestrator as O
from supreme.config import VAR_DIR
from supreme.db import connect, init_db
from supreme.worker import run_worker


def main() -> int:
    var = Path(os.environ.get("SUPREME_VAR_DIR", str(VAR_DIR)))
    var.mkdir(parents=True, exist_ok=True)
    conn = connect(var / "supreme.db")
    init_db(conn)
    worker_id = os.environ.get("TEST_WORKER_ID", "helper-worker")
    slow = float(os.environ.get("TEST_SLOW_SECONDS", "3"))
    lease = float(os.environ.get("TEST_LEASE_SECONDS", "30"))
    hb = float(os.environ.get("TEST_HEARTBEAT_SECONDS", str(max(0.05, lease / 3))))
    core = O.OmniBrainCore(conn=conn, worker_id=worker_id, lease_seconds=lease)
    original = O.run_tool
    marker = var / "tool-starts.jsonl"

    def slow_tool(name, inp):
        with marker.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"pid": os.getpid(), "worker_id": worker_id, "tool": name, "at": time.time()}) + "\n")
        time.sleep(slow)
        return original(name, inp)

    O.run_tool = slow_tool
    stop = threading.Event()
    def _handle(signum, frame):
        stop.set()
    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)
    res = run_worker(once=True, interval=0.05, core=core, worker_id=worker_id,
                     lease_seconds=lease, heartbeat_interval=hb, stop_event=stop)
    conn.close()
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
