"""Worker SUPREME — processus séparé consommant la file de missions SQLite.

Plusieurs workers peuvent partager la même base WAL. Chaque mission est détenue
par un bail nominatif avec heartbeat et jeton de fencing ; un worker qui démarre
ne réinitialise pas les missions encore actives. La reprise ne cible que les
baux expirés dont le worker est arrêté ou silencieux. Les résultats commités sont
idempotents par tâche ; un appel LLM interrompu est bloqué pour réconciliation
humaine afin d'éviter une double facturation aveugle.
"""
from __future__ import annotations

import json
import threading

from .db import get_conn, log_event, now, transaction
from .leases import (LeaseLostError, claim_next, heartbeat_worker, new_worker_id,
                     register_worker, stop_worker)
from .orchestrator import OmniBrainCore
from .security import redact


def claim_next_mission(core: OmniBrainCore, worker_id: str | None = None,
                       lease_seconds: float | None = None) -> str | None:
    """Compatibilité : revendique la prochaine mission et retourne son id.

    Le bail reste enregistré en base au nom du worker ; `core.run(mid)` le
    réutilise s'il est encore vivant. Les nouveaux appelants préfèrent
    `claim_next` qui retourne le bail complet.
    """
    lease = claim_next(core.conn, worker_id or core.worker_id,
                       lease_seconds if lease_seconds is not None else core.lease_seconds)
    return lease.mission_id if lease else None


def run_worker(once: bool = False, interval: float = 1.0, max_missions: int | None = None,
               core: OmniBrainCore | None = None, max_polls: int | None = None,
               worker_id: str | None = None, lease_seconds: float | None = None,
               heartbeat_interval: float | None = None,
               stop_event: threading.Event | None = None) -> dict:
    """Boucle worker résiliente.

    - `once` : vide la file planifiée puis sort.
    - `max_polls` : borne les scrutations à vide (mode service borné pour tests/CI).
    - `stop_event` : arrêt propre ; la mission en cours est replanifiée si interrompue.
    - `lease_seconds` / `heartbeat_interval` : bail et heartbeat configurables.
    """
    if interval <= 0:
        raise ValueError("interval doit être positif")
    core = core or OmniBrainCore()
    worker_id = worker_id or core.worker_id or new_worker_id()
    core.worker_id = worker_id
    lease_seconds = lease_seconds if lease_seconds is not None else core.lease_seconds
    if lease_seconds <= 0:
        raise ValueError("lease_seconds doit être positif")
    heartbeat_interval = heartbeat_interval if heartbeat_interval is not None else max(0.05, min(lease_seconds / 3.0, 5.0))
    if heartbeat_interval <= 0 or heartbeat_interval >= lease_seconds:
        raise ValueError("heartbeat_interval doit être positif et inférieur au bail")
    stop_event = stop_event or threading.Event()
    register_worker(core.conn, worker_id)
    recovered = core.recover()  # uniquement les baux expirés / workers arrêtés
    hb_stop = threading.Event()

    def idle_heartbeat():
        conn = get_conn(core.db_path) if core.db_path else core.conn
        while not hb_stop.wait(heartbeat_interval):
            try:
                heartbeat_worker(conn, worker_id)
            except Exception:
                return

    hb = threading.Thread(target=idle_heartbeat, name=f"worker-hb-{worker_id}", daemon=True)
    hb.start()
    processed, missions, polls = 0, [], 0
    try:
        while not stop_event.is_set():
            lease = claim_next(core.conn, worker_id, lease_seconds)
            if lease is None:
                if once:
                    break
                polls += 1
                if max_polls is not None and polls >= max_polls:
                    break
                if stop_event.wait(interval):
                    break
                continue
            try:
                res = core.run(lease.mission_id, lease=lease, stop_event=stop_event)
                missions.append({"mission_id": lease.mission_id, "state": res["state"],
                                 "worker_id": worker_id, "fencing_token": lease.fencing_token})
                if res["state"] != "interrupted":
                    processed += 1
            except LeaseLostError as e:
                log_event(core.conn, "warning", "worker", f"bail perdu : {e}", lease.mission_id)
                missions.append({"mission_id": lease.mission_id, "state": "lease_lost", "worker_id": worker_id})
            except Exception as e:
                log_event(core.conn, "error", "worker", f"mission échouée dans le worker : {e}", lease.mission_id)
                # Évite une boucle chaude sur une erreur persistante : état failed explicite.
                safe_error = redact(str(e))[:500]
                with transaction(core.conn, immediate=True):
                    core.conn.execute(
                        "UPDATE missions SET state='failed', result_json=?, updated_at=? WHERE id=? AND state='planned'",
                        (json.dumps({"error": safe_error}, ensure_ascii=False), now(), lease.mission_id))
                missions.append({"mission_id": lease.mission_id, "state": "error", "error": safe_error[:200]})
                processed += 1
            if max_missions is not None and processed >= max_missions:
                break
    finally:
        hb_stop.set()
        hb.join(timeout=2.0)
        stopped = stop_worker(core.conn, worker_id)
        log_event(core.conn, "info", "worker",
                  f"worker terminé : {processed} mission(s), reprises {recovered}, libérées {stopped['released']}",
                  data={"worker_id": worker_id})
    return {"processed": processed, "missions": missions, "recovered": recovered,
            "worker_id": worker_id, "stopped": True}
