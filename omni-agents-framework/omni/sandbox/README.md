# `omni/sandbox` — exécution isolée & runtime (Phases 3.2 / 3.3)

## Hook E2B avec fallback local

```python
from omni.sandbox import Sandbox
result = Sandbox().run_code("print(6 * 7)", heavy=True)
result.backend          # "e2b" | "local" | "none"
result.fallback_reason  # raison honnête si E2B indisponible
```

- E2B : import paresseux, clé `E2B_API_KEY` (jamais dans le dépôt), méthode
  `run_code` / `runCode` du SDK. Toute exception → fallback.
- Fallback local : `python3 -I`, environnement minimal, répertoire temporaire,
  timeout, limites POSIX CPU/mémoire best-effort, sorties capturées.
- Aucun E2B installé / aucune clé → `backend="local"`, jamais une simulation
  silencieuse ; `Sandbox.events` trace chaque tentative.

## Runtime continu + RBAC

```bash
OMNIBRAIN_DB=var/runtime.sqlite3 python3 -m omni.sandbox --max-ticks 1
```

`Runtime` est un scheduler **borné** (`max_ticks`) : file de missions → graphe
critique → mémoire SQLite → `orchestration_logs`. `RBAC` : `viewer`, `operator`,
`reviewer`, `admin`, `human`. Les actions irréversibles (`merge_pr`,
`write_main`, `force_push`, …) sont **refusées à toute identité machine**, même
avec `human_approval=True` ; seule `Lassana` avec approbation explicite peut les
autoriser.
