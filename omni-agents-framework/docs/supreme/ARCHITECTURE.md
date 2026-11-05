# Architecture OMNIBRAIN SUPREME 1000

## Principe
SUPREME est une couche multi-agents **au-dessus** du framework OmniBrain V4 existant
(`omni/`, `omnibrain/`). Elle réutilise la mémoire SQLite, le sandbox, le RBAC et la
télémétrie V4 plutôt que de les réécrire. Python 3.11+ **stdlib uniquement**, stockage
**SQLite** unique, aucun service externe requis pour démarrer gratuitement.

## Les 30 composants demandés → implémentation réelle

| # | Composant | Module | État |
| --- | --- | --- | --- |
| 1 | OmniBrain Core | `supreme/orchestrator.py` `OmniBrainCore` | Implémenté, testé |
| 2 | Mission Planner | `supreme/planner.py` `MissionPlanner` | Implémenté, testé |
| 3 | Task Decomposer | `supreme/planner.py` (décomposition auto + DAG) | Implémenté, testé |
| 4 | Agent Registry | `supreme/registry.py` | Implémenté, testé |
| 5 | Agent Factory | `supreme/factory.py` | Implémenté, testé |
| 6 | Agent Orchestrator | `supreme/orchestrator.py` (DAG, états, reprises) | Implémenté, testé |
| 7 | Division Managers | 20 profils `kind=manager` + outil `division_report` | Implémenté, testé |
| 8 | Intelligent Model Router | `supreme/router.py` | Implémenté ; **0 fournisseur configuré** |
| 9 | Multi-Model Council | `supreme/council.py` | Implémenté ; nécessite fournisseurs |
| 10 | Shared Memory Engine | `supreme/memory.py` (central/division/collective) | Implémenté, testé |
| 11 | Individual Memory Engine | `supreme/memory.py` (individual) | Implémenté, testé |
| 12 | Knowledge Graph | `supreme/memory.py` `relate/neighbors` | Implémenté, testé |
| 13 | Communication Bus | `supreme/bus.py` (ACL, anti-usurpation, DLQ) | Implémenté, testé |
| 14 | Execution Runtime | `supreme/runtime.py` `WorkerPool` | Implémenté, testé |
| 15 | Tool Integration Layer | `supreme/tools.py` (42 outils déterministes) | Implémenté, testé |
| 16 | Security Supervisor | `supreme/security.py` | Implémenté, testé |
| 17 | Policy Engine | `supreme/policy.py` (4 niveaux, approbations) | Implémenté, testé |
| 18 | Evaluation Engine | `supreme/evaluation.py` (7 tests/profil) | Implémenté, testé |
| 19 | Learning Engine | `supreme/learning.py` | Implémenté, testé |
| 20 | Self-Improvement Engine | `supreme/learning.py` (gain mesuré + rollback) | Implémenté, testé |
| 21 | Failure Recovery Engine | `orchestrator.recover` + retries bornés | Implémenté, testé |
| 22 | Resource Manager | `runtime` (concurrence, backpressure) + `budget` | Implémenté, testé |
| 23 | Cost Controller | `supreme/budget.py` | Implémenté, testé |
| 24 | Observability Engine | `supreme/observability.py` (KPIs réels) | Implémenté, testé |
| 25 | Mission History | tables `missions`/`tasks` + `reporting` | Implémenté, testé |
| 26 | Version Manager | `factory` versions + catalogue versionné | Implémenté, testé |
| 27 | Backup and Recovery Manager | `supreme/backup.py` | Implémenté, testé |
| 28 | API Gateway | `supreme/api.py` | Implémenté, testé |
| 29 | Administrative Interface | `supreme/dashboard/index.html` | Implémenté, testé |
| 30 | Reporting Engine | `supreme/reporting.py` | Implémenté, testé |

## Flux d'une mission
```
objectif → MissionPlanner (classification + DAG) → Registry (sélection agents)
→ OmniBrainCore.run (vagues parallèles, WorkerPool) → outils déterministes réels
→ validation sortie → Bus (messages) → Memory (collectif, provenance)
→ Budget (coût) → Observability (métriques) → Reporting (rapport)
```

## Séparation profil / instance (1000 agents ≠ 1000 processus)
- **Profil** : donnée versionnée dans `supreme/divisions/divNN.py` → `catalog/agents.json`.
- **Enregistrement** : ligne SQLite `agents` avec statut.
- **Instance** : tâche temporaire exécutée par le `WorkerPool` (4 workers par défaut).
- **Mémoire** : niveaux SQLite avec ACL.
Aucun processus permanent par agent ; activation à la demande, concurrence bornée.

## Statuts (preuve obligatoire)
- `registered` : présent au catalogue.
- `validated` : 7 contrôles offline OK (mission représentative réussie ou différée).
- `operational` : mission représentative **réellement exécutée avec succès**.
- `monitored` : operational + performances suivies.
Au démarrage : **1000 spécialistes registered → 1000 validated → 40 operational/monitored**
(2 par division, outils déterministes) + **20 chefs monitored**. Les 960 autres ont une
mission représentative LLM **différée** (aucun fournisseur configuré) — jamais comptés opérationnels.

## Dépendances entre modules (pas de cycle)
`config` ← `db` ← `security` ← {`registry`, `bus`, `memory`, `budget`, `policy`}
← `planner` ← `orchestrator` ← {`api`, `__main__`}. `tools` est autonome.
`router`/`council`/`evaluation`/`learning`/`observability`/`reporting`/`backup` au-dessus.
