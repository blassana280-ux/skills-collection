"""Worker SUPREME (Phase G) — processus séparé consommant la file de missions SQLite.

Montée en charge horizontale réelle et gratuite : N workers peuvent tourner sur la
même base (WAL). Chaque mission est revendiquée atomiquement (UPDATE ... WHERE
state='planned') : deux workers ne peuvent pas exécuter la même mission. Ceci est
exécutable en local dès maintenant ; le déploiement cloud reste une décision humaine.
"""
from __future__ import annotations

import time

from .db import log_event, now, transaction
from .orchestrator import OmniBrainCore


def claim_next_mission(core: OmniBrainCore) -> str | None:
    """Revendique atomiquement la prochaine mission planifiée (priorité, puis ancienneté)."""
    row = core.conn.execute(
        "SELECT id FROM missions WHERE state='planned' ORDER BY priority ASC, created_at ASC LIMIT 1").fetchone()
    if row is None:
        return None
    mid = row["id"]
    with transaction(core.conn):
        cur = core.conn.execute(
            "UPDATE missions SET state='running', updated_at=? WHERE id=? AND state='planned'", (now(), mid))
        if cur.rowcount == 1:
            return mid
    return None  # revendiquée par un autre worker entre-temps


def run_worker(once: bool = False, interval: float = 1.0, max_missions: int | None = None,
               core: OmniBrainCore | None = None, max_polls: int | None = None) -> dict:
    """Boucle worker. `once` : traite la file puis sort. `max_polls` : borne les scrutations.

    Renvoie {"processed": n, "missions": [...]}. Les échecs d'une mission n'arrêtent
    pas le worker (résilience) ; ils sont journalisés.
    """
    core = core or OmniBrainCore()
    recovered = core.recover()
    processed, missions, polls = 0, [], 0
    while True:
        mid = claim_next_mission(core)
        if mid is None:
            if once:
                break  # file vidée
            polls += 1
            if max_polls is not None and polls >= max_polls:
                break
            time.sleep(interval)
            continue
        try:
            res = core.run(mid)
            missions.append({"mission_id": mid, "state": res["state"]})
        except Exception as e:
            log_event(core.conn, "error", "worker", f"mission {mid} échouée dans le worker : {e}", mid)
            missions.append({"mission_id": mid, "state": "error", "error": str(e)[:200]})
        processed += 1
        if max_missions is not None and processed >= max_missions:
            break
    log_event(core.conn, "info", "worker", f"worker terminé : {processed} mission(s), reprises {recovered}")
    return {"processed": processed, "missions": missions, "recovered": recovered}
