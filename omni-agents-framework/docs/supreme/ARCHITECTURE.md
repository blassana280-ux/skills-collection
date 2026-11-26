# Architecture OMNIBRAIN SUPREME 1000 — version 1.3.0

Racine dépôt : `skills-collection/`. Framework : `skills-collection/omni-agents-framework/`.
Dans les tableaux ci-dessous, `supreme/...` signifie
`skills-collection/omni-agents-framework/supreme/...`.

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
| 8 | Intelligent Model Router | `supreme/router.py` + `providers.py` + `credentials.py` + `provider_control.py` | Implémenté, testé localement ; **0 fournisseur connecté réellement** |
| 9 | Multi-Model Council | `supreme/council.py` (preuves référencées, second avis borné, `needs_review`) | Implémenté, testé ; nécessite fournisseurs réels |
| 10 | Shared Memory Engine | `supreme/memory.py` (central/division/collective) | Implémenté, testé |
| 11 | Individual Memory Engine | `supreme/memory.py` (individual) | Implémenté, testé |
| 12 | Knowledge Graph | `supreme/memory.py` `relate/neighbors` | Implémenté, testé |
| 13 | Communication Bus | `supreme/bus.py` (ACL, anti-usurpation, DLQ) | Implémenté, testé |
| 14 | Execution Runtime | `supreme/runtime.py` `WorkerPool` | Implémenté, testé |
| 15 | Tool Integration Layer | `supreme/tools.py` (41 outils déterministes) | Implémenté, testé |
| 16 | Security Supervisor | `supreme/security.py` | Implémenté, testé |
| 17 | Policy Engine | `supreme/policy.py` (4 niveaux, approbations) | Implémenté, testé |
| 18 | Evaluation Engine | `supreme/evaluation.py` (7 tests/profil) | Implémenté, testé |
| 19 | Learning Engine | `supreme/learning.py` | Implémenté, testé |
| 20 | Self-Improvement Engine | `supreme/learning.py` (gain mesuré + rollback) | Implémenté, testé |
| 21 | Failure Recovery Engine | `supreme/leases.py` + `orchestrator.recover` + retries bornés | Implémenté, testé multi-processus/crash |
| 22 | Resource Manager | `runtime` (pool borné) + `worker`/`leases` (baux, heartbeat, fencing) + `budget` | Implémenté, testé |
| 23 | Cost Controller | `supreme/budget.py` (réservations atomiques, exposition, quotas) | Implémenté, testé |
| 24 | Observability Engine | `supreme/observability.py` (KPIs réels) | Implémenté, testé |
| 25 | Mission History | tables `missions`/`tasks` + `reporting` | Implémenté, testé |
| 26 | Version Manager | `factory` versions + catalogue versionné | Implémenté, testé |
| 27 | Backup and Recovery Manager | `supreme/backup.py` | Implémenté, testé |
| 28 | API Gateway | `supreme/api.py` | Implémenté, testé |
| 29 | Administrative Interface | `supreme/dashboard/index.html` | Implémenté, testé |
| 30 | Reporting Engine | `supreme/reporting.py` | Implémenté, testé |

## Composants ajoutés/durcis en 1.3.0
| Module | Rôle | Garde-fou |
| --- | --- | --- |
| `credentials.py` | env → `*_FILE` → fichier runtime privé 0600 → legacy 0600 | TTY/getpass pour saisie, pas de secret dans statuts/logs |
| `provider_control.py` | autorisation/révocation inférence, prix attestés, vérification, modèles découverts | fermé par défaut, ≤24 h, plafond USD/appels, prix ≤30 j |
| `activation.py` | campagnes 5→20→60→100→…→960, preuves, quarantaine, reprise | `external_api` obligatoire, bail fencé, revue humaine |
| `planner.py` | mode LLM explicite, cross-division, vérificateur indépendant | pas de substitut local simulé pour un agent LLM |
| `memory.py` | contradictions `subject_key`/`claim_key`/`claim_value` | pas de contradiction sur simple formulation |
| `learning.py` | comparaison mesurée avant/après entre cycles | baseline ≠ gain, pas de modification noyau |
| `db.py` v3 | 7 tables additives fournisseurs/activation | migration sans suppression, audit |

## Flux d'une mission
```
objectif → MissionPlanner (classification + DAG, cross-division si complexe)
→ Registry (sélection agents, vérificateur indépendant)
→ OmniBrainCore.run (vagues parallèles, WorkerPool)
→ outils déterministes réels OU inférence externe autorisée (jamais de stub activant)
→ validation sortie → Council si complexe (preuves, second avis borné, needs_review)
→ Bus (messages) → Memory (provenance ; central seulement si vérifié)
→ Budget (usage réel/exposition) → Observability → Reporting
```

## Flux d'activation LLM
```
clé privée → découverte GET réelle → modèles persistés → prix attestés → autorisation humaine bornée
→ campagne palier suivant → par agent : permissions/budget/garde → POST réel → JSON exploitable + usage
→ preuve privée + activation atomique ; échec isolé → quarantaine ; panne fournisseur → arrêt campagne
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
État réel 1.3.0 : **1020 profils enregistrés** ; statuts SQLite `registered=0`,
`validated=960`, `monitored=60`, `operational=0`. Les **60 agents locaux** (40 spécialistes
outil + 20 chefs) sont réellement opérationnels en local sur preuve et marqués `monitored`.
Les 960 autres ont une mission représentative LLM **différée** (aucun fournisseur réel connecté)
— jamais comptés opérationnels. Le statut `operational` strict n'est pas utilisé comme substitut
à une preuve fournisseur ; `monitored` signifie preuve locale + suivi.

## Dépendances entre modules (pas de cycle)
`config` ← `db` ← `security` ← {`registry`, `bus`, `memory`, `budget`, `policy`}
← `planner` ← `orchestrator` ← {`api`, `__main__`}. `tools` est autonome.
`router`/`council`/`evaluation`/`learning`/`observability`/`reporting`/`backup` au-dessus.

## Compléments v1.1–1.3.0
- `supreme/providers.py` : client HTTP multi-fournisseurs réel (composant Model Router étendu).
- `supreme/worker.py` + `supreme/leases.py` : workers séparés, file SQLite, propriétaire,
  bail expirant, heartbeat, fencing, récupération exclusive, idempotence `task_executions`.
- `supreme/audit.py` : audit exécutable avec preuves (catalogue, sécurité, schéma, baux,
  apprentissage, réservations/quotas, tests découverts).
- Orchestrateur : arbitrage `Council` intégré aux missions complexes ; plans explicables
  (`explanation` + `why`) ; writes fenced par bail.
- Evaluation : représentatifs LLM tentés réellement si fournisseur configuré (activation sur preuve).
- Learning : `run_cycle()` persistant + `LearningScheduler` périodique, verrou unique,
  heartbeat, erreurs surveillées, arrêt/reprise ; PR/fusion = porte humaine.
- Budget/Router/Council : réservation avant appel, solde réel, quotas centraux, limites
  tokens/contexte, plafond collectif conservateur ; aucun contournement du routeur par le conseil.
- Schéma SQLite v2 additif : `workers`, `task_executions`, `budget_reservations`,
  `budget_reservation_scopes`, `learning_schedulers`, `learning_runs`, colonnes de bail/fencing.
