# `omni/memory` — mémoire persistante & auto-amélioration (Phases 2.1 → 2.3)

Remplace les recettes volatiles par un **store SQLite** (`var/omnibrain.sqlite3`
par défaut, ou `OMNIBRAIN_DB`). Zéro dépendance, transactions, rédaction des
secrets avant toute insertion, sûr pour les threads d'une vague.

## Schéma (version 1)

| Table | Contenu |
| --- | --- |
| `missions` | id, `project_type`, titre, spec, statut, verdict, horodatages, metadata |
| `escouades` | escouades rattachées à une mission, numéro de vague |
| `resultats` | par agent : statut, verdict, `duration_ms`, `tokens_in/out`, artefacts, preuves |
| `echecs` | incidents par `profile` et `error_type`, tentative, message rédigé |
| `recettes` | **par type de projet**, étapes, succès/échecs, score, mission source |
| `prompt_iterations` | une ligne par itération GEPA (scores, acceptation, rationale) |
| `benchmarks` | historique des passes de `tools/benchmark.py` |
| `autofix_runs` | signatures des correctifs déjà proposés (idempotence) |
| `orchestration_logs` | logs persistants du runtime / graphe / optimizer |

`schema_meta.schema_version` permet les migrations sans perte.

## API

```python
from omni.memory import MemoryStore, record_mission, get_recettes, AutoFix

store = MemoryStore(":memory:")            # ou MemoryStore(Path("var/omnibrain.sqlite3"))
mid = store.record_mission({"project_type": "fintech", "title": "Paiement", "spec": "..."})
sid = store.record_squad(mid, "escouade-fintech", wave=1)
store.record_result(mid, "backend-api", escouade_id=sid, duration_ms=42, tokens_out=900)
store.record_failure(mid, "backend-api", "backend-api", "timeout", "seuil dépassé")
store.upsert_recette("fintech", "spec-tests-deploy", ["spécifier", "tester", "déployer"], success_delta=1)
recettes = store.get_recettes("fintech")   # triées par score décroissant
```

API module-level (store par défaut, configurable via `configure(path)`) :
`record_mission()` / `get_recettes()`.

## Auto-amélioration (2.2)

`AutoFix.check(profile)` lit les échecs du profil : **à partir de 2**, il crée
une fiche corrigée déterministe (une règle par type d'échec), une branche
`omnibrain/fix-<agent>`, un commit, un push et une **PR**. Il n'existe aucune
méthode de merge dans le backend et `autofix_runs` rend l'opération idempotente.

Sécurité : `CommandBackend(dry_run=True)` par défaut n'exécute rien ; seule
`OMNIBRAIN_AUTOFIX_APPLY=1` active `git`/`gh`. Les tests utilisent
`RecordingBackend`. **Décision de fusion : Lassana uniquement.**

## Boucle GEPA (2.3)

`tools/optimize_prompts.py` lit résultats/échecs/recettes, calcule un score de
couverture, propose des règles correctives, n'accepte que sur gain et journalise
**chaque** itération en base + `var/prompt_iterations.jsonl`.

```bash
python3 tools/optimize_prompts.py --project-type fintech --iterations 3
```
