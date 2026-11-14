# API OMNIBRAIN SUPREME 1.3.0

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
- Erreurs : `{error: "..."}` avec code HTTP 400/401/403/404/409/500.
  `409` : conflit de bail/mission déjà détenue par un autre worker (`LeaseLostError`).

## Endpoints ajoutés (v1.1–1.2)
| Route | Auth | Description |
| --- | --- | --- |
| `GET /api/providers` | lecture | Fournisseurs : configuré (clé présente) vs vérifié (appel réel), priorité Mistral/Vide, noms de variables d'env — **aucune valeur secrète** |
| `POST /api/providers/check` | admin | Découverte RÉELLE de catalogue (appel HTTP `/models`), pas une inférence payante |
| `GET /api/activation` | lecture | Paliers, campagne courante, membres, preuves, quarantaine, compteurs réels |
| `GET /api/activation/{id}` | lecture | État détaillé d'une campagne |
| `POST /api/activation/prepare` | admin + `confirm=PREPARER CAMPAGNE` | Prépare le palier suivant `{size, provider, model?, budget_usd?, per_agent_usd?}` ; ne lance pas d'appel |
| `POST /api/activation/{id}/run` | admin + `confirm=ACTIVER CAMPAGNE` | Exécute une campagne préparée ; exige en plus l'autorisation d'inférence CLI distincte |
| `GET /api/decisions` | lecture | Décisions/conseils persistés, y compris `needs_review`, sans secret |
| `GET /api/divisions/performance` | lecture | Tâches mesurées, taux de succès et coûts par division |
| `GET /api/quotas` | lecture | Totaux, exposition réservée/incertaine, réservations récentes, quotas |
| `GET /api/alerts` | lecture | 50 derniers événements warning/error/critical, expurgés |
| `GET /api/security` | lecture | Journal d'accès expurgé (30 dernières lignes), permissions du jeton, posture — aucun secret |
| `GET /api/missions/{id}` | lecture | Détail : plan complet avec `explanation` + `why` par tâche, tâches, résultat (dont `council` si mission complexe) |
| `GET /api/agents/{id}/history` | lecture | Historique des missions de l'agent, KPIs (taux de succès), 7 dernières évaluations, supervision |
| `GET /api/memory/search?mode=tfidf` | lecture | Recherche contextuelle TF-IDF locale (en plus de `auto`/`fts`) |

## Limites de sécurité 1.3.0
- L'API ne peut pas écrire une clé fournisseur, attester des prix, accorder/révoquer l'autorisation d'inférence,
  ni lever une quarantaine. Ces actions restent en CLI privé avec confirmation humaine.
- `configured_count` compte les clés présentes ; `verification.connected` compte seulement les découvertes réelles réussies.
- Les rapports publics omettent `api_key_prefix` et chemins privés complets.
- Préparer une campagne ne dépense rien ; l'exécuter sans contrôle d'inférence actif est refusé avant réseau.

## Explicabilité & arbitrage
- Chaque plan contient `explanation` : pourquoi cette classification, cette taille d'escouade,
  cette stratégie (outils locaux vs LLM), cette vérification croisée, cet arbitrage.
- Chaque tâche contient `why` : pourquoi cet agent et cet outil.
- Les missions `complexe` produisent `result.council` : décision du conseil multi-modèles
  fondée sur les preuves (sorties de tâches réelles), ou `unavailable` honnête sans fournisseur.

## Durcissement 1.3.0 visible via l'API
- `/api/health` retourne la version SUPREME courante (`1.3.0`).
- `/api/missions` / `/api/missions/{id}` exposent les champs de bail/fencing persistés
  (`owner_worker_id`, `lease_expires_at`, `fencing_token`, `run_attempts`) lorsqu'ils existent.
- Une exécution concurrente conflictuelle renvoie `409` au lieu d'écraser le travail d'un worker.
- Le conseil inclut `budget_max_usd`, `budget_spent_usd`, `budget_reserved_bound_usd`,
  `attempts`, `errors`, `models` ; aucun appel ne contourne le routeur/budget.
- Les réservations budgétaires interrompues restent visibles en base pour réconciliation humaine.
