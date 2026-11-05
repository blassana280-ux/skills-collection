# Guide de maintenance OMNIBRAIN SUPREME 1.2.1

Racine dépôt : `skills-collection/`. Framework : `skills-collection/omni-agents-framework/`.
Les chemins `omni-agents-framework/...` sont relatifs à la racine dépôt ; les commandes
`python3 -m supreme ...` s'exécutent depuis `skills-collection/omni-agents-framework/`.

## Ajouter / modifier un agent
1. Modifier la ligne dans `supreme/divisions/divNN.py` (ou utiliser l'Agent Factory pour un agent temporaire).
2. `python3 -m supreme catalog` (régénère le catalogue ; échoue si doublon/incomplet).
3. `python3 -m supreme sync` puis `python3 -m supreme evaluate --activate`.
4. Commit sur la branche dédiée + PR. La CI vérifie la régénération.

## Règles de qualité du catalogue
- 20 divisions × 50 spécialistes exactement ; 20 chefs.
- IDs, noms, objectifs, tâches représentatives uniques ; pas de clones.
- 27 champs obligatoires + 7 évaluations par profil.
- Permissions moindre privilège ; outils existants dans le Tool Registry.

## Mettre à jour un outil
Modifier `supreme/tools.py` (fonction + fixture + critère). Les tests `test_supreme_tools`
vérifient chaque fixture et la gestion des entrées vides. Régénérer le catalogue si les
allowlists de division changent.

## Surveillance continue
- `python3 -m supreme status` / `report` : état réel.
- KPIs via `/api/kpis` ; null = indisponible (ne pas inventer de valeur).
- Le Learning Engine analyse échecs récurrents et agents peu performants ; propose des
  stratégies versionnées, acceptées seulement sur gain mesuré, avec rollback.

## Versions
- Profils : `version` + `changelog` ; l'Agent Factory conserve les versions (`agent_versions`)
  et permet `rollback`.
- Catalogue : source de vérité `divisions/`, sortie `catalog/` régénérable et vérifiée en CI.

## Commandes d'exploitation (v1.2.1)
```bash
python3 -m supreme audit            # audit exécutable : catalogue, sécurité, baux, budget, apprentissage, tests
python3 -m supreme learn            # cycle ponctuel persistant (rapport JSON, PR = humain)
python3 -m supreme learn --periodic --interval 300 --lease-seconds 30 --heartbeat-seconds 5
python3 -m supreme learn --status   # ordonnanceur, derniers cycles, erreurs
python3 -m supreme worker --once --lease-seconds 30 --heartbeat-seconds 5
python3 -m supreme worker --interval 1 --lease-seconds 30 --heartbeat-seconds 5
python3 -m supreme providers        # statut fournisseurs sans clés ; --check = appel réel
python3 -m supreme rotate-token     # rotation du jeton API (jamais affiché), puis redémarrer serve
```

## Workers, baux et reprise
- Chaque worker a un `worker_id`, un bail expirant et un heartbeat. Un worker qui démarre
  ne réinitialise pas une mission encore détenue par un bail vivant.
- Reprise exclusive : bail expiré + worker arrêté ou silencieux ; jeton de fencing refuse
  les écritures de l'ancien propriétaire ; résultats dédupliqués dans `task_executions`.
- Arrêt propre : `SIGINT`/`SIGTERM`. Crash : reprise après expiration du bail.
- Un appel LLM interrompu avec réservation incertaine est bloqué pour réconciliation humaine
  avant nouvelle tentative payante.

## Apprentissage périodique
- Fréquence configurable (`--interval`), bornable (`--max-cycles`), arrêt propre.
- Un seul cycle `running` global ; un seul ordonnanceur actif par `scheduler_id`.
- Rapports persistés : SQLite `learning_runs` + `omni-agents-framework/var/supreme/learning/` (`0600`).
- Erreurs surveillées via `learn --status` et `/api/alerts` ; aucune modification du noyau,
  des permissions ou de la sécurité. Toute modification importante de code passe par branche,
  tests, comparaison, rollback et PR humaine.

## Budget et conseil
- Réservation atomique avant chaque appel (`BEGIN IMMEDIATE`), solde sur usage réel.
- Exposition = dépenses soldées + réservations ouvertes/interrompues ; quotas mission,
  agent, division, fournisseur, global. Le conseil passe par le routeur et ne le contourne pas.
- Surveiller `budget_reservations` et `budget_ledger` ; ne pas solder manuellement sans preuve.

## Migration / sauvegarde
- Schéma SQLite v2 additif ; toujours sauvegarder avant migration : `python3 -m supreme backup`.
- Sauvegarde pré-durcissement 1.2.1 : `bk-20261105T163835-22f858` (intégrité `ok`).
