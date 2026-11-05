# API OMNIBRAIN SUPREME

Base : `http://<hôte>:8765`. Auth : en-tête `X-API-Token: <jeton>` (ou `Authorization: Bearer`).
Lecture anonyme si `SUPREME_ALLOW_ANON_READ=1`. Écritures : jeton admin obligatoire.

## Lecture (GET)
| Route | Description |
| --- | --- |
| `/api/health` | Santé + version |
| `/api/status` | État système (agents, missions, tâches, mémoire, budget, KPIs) |
| `/api/kpis` | 15 indicateurs (null = indisponible) |
| `/api/agents?division=&kind=&status=` | Liste des agents |
| `/api/agents/{id}` | Profil complet d'un agent |
| `/api/divisions` | 20 divisions + chefs + statuts |
| `/api/missions` | Historique des missions |
| `/api/missions/{id}` | Détail mission + tâches |
| `/api/models` | Statut réel des fournisseurs |
| `/api/quotas` | Quotas + totaux dépenses |
| `/api/memory/search?q=&level=&limit=` | Recherche mémoire (FTS5) |
| `/api/approvals` | Approbations en attente |
| `/api/tools` | 41 outils exécutables |
| `/api/skills` | Skills documentaires + outils |
| `/api/bus` | Statistiques du bus |
| `/api/reports/global` | Rapport global |
| `/api/backups` | Liste des sauvegardes |
| `/api/trace/{mission_id}` | Trace complète (événements, métriques, tâches) |
| `/` | Tableau de bord mobile |

## Écriture (POST, jeton admin)
| Route | Corps | Effet |
| --- | --- | --- |
| `/api/missions` | `{objective, priority?, budget_usd?, tasks?, run?}` | Soumet (+exécute si run≠false) |
| `/api/missions/{id}/run` | — | Exécute une mission planifiée |
| `/api/missions/{id}/cancel` | — | Annule |
| `/api/approvals` | `{action, requested_by, context}` | Demande une approbation |
| `/api/approvals/{id}/decide` | `{approved, decided_by}` | Décision humaine |
| `/api/backup` | `{label?}` | Sauvegarde |
| `/api/providers/check` | `{}` | Vérification réelle de disponibilité |

## Exemple
```bash
curl -X POST http://localhost:8765/api/missions \
  -H "X-API-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"objective":"Vérifier la syntaxe Python et valider un JSON"}'
```
Réponse : `{submitted:{mission_id,plan}, result:{state:"completed",tasks:{done:N},cost_usd:0.0}}`.

## Formats
- Mission : `objective` (str ≤4000), `priority` (int), `budget_usd` (float ≥0),
  `tasks` optionnel `[{agent_id, tool?, input?, depends_on?}]`.
- Erreurs : `{error: "..."}` avec code HTTP 400/401/403/404/500.
