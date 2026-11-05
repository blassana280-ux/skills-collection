# Suivi durable OMNIBRAIN SUPREME 1000

**Dernière mise à jour : 2026-11-05** · **Version SUPREME : 1.2.1** · Branche :
`arena/ffc77bf1-skills-collection` · `master` synchronisé par merge propre depuis `af4b951`.
Racine dépôt : `skills-collection/`. Framework : `skills-collection/omni-agents-framework/`.
Ce document permet une reprise sans perdre le contexte. Aucune fusion de PR n'est autorisée implicitement.

## État actuel
- Couche SUPREME **1.2.1** dans `skills-collection/omni-agents-framework/supreme/`.
- Workers séparés fiables : `omni-agents-framework/supreme/leases.py`, `worker.py`,
  `orchestrator.py` — worker_id, propriétaire, bail expirant, heartbeat, fencing,
  récupération exclusive, idempotence `task_executions`, arrêt propre, reprise après crash.
- Apprentissage : `omni-agents-framework/supreme/learning.py` — `run_cycle()` persistant,
  verrou unique, `LearningScheduler`, CLI `learn --periodic`, rapports dans
  `omni-agents-framework/var/supreme/learning/`, erreurs surveillées, reprise après interruption.
- Budget/conseil : `budget.py`, `router.py`, `council.py` — réservation atomique avant appel,
  solde réel, quotas centraux, limites tokens, conseil sans contournement du routeur.
- Schéma SQLite **v2 additif** ; sauvegarde pré-migration :
  `omni-agents-framework/var/supreme/backups/bk-20261105T163835-22f858/` (intégrité `ok`).
- **1020 profils enregistrés** : 1000 spécialistes + 20 chefs. Statuts réels :
  `registered=0`, `validated=960`, `monitored=60`, `operational=0`.
  **60 agents locaux réellement opérationnels sur preuve** (outils déterministes, marqués `monitored`).
  **960 agents LLM en attente** d'un fournisseur réel ; **0 fournisseur IA connecté** ; **0 cloud déployé**.
- Tests locaux réels : **340 verts** = **105 V4/non-SUPREME + 235 SUPREME**.
  Journaux : `omni-agents-framework/var/supreme/validation/`.
- API + dashboard mobile fonctionnels sur données réelles ; jeton API 0600 jamais affiché.
- PR #5 ouverte non fusionnée ; PR #2 non modifiée ; `master` non modifié directement.

## Architecture retenue
Voir `omni-agents-framework/docs/supreme/ARCHITECTURE.md`. Python stdlib + SQLite WAL,
couche au-dessus de V4. Source de vérité des profils :
`omni-agents-framework/supreme/divisions/divNN.py` →
`omni-agents-framework/supreme/catalog/agents.json`.
Données runtime gitignorées : `omni-agents-framework/var/supreme/`.

## Décisions prises
1. Réutiliser V4 plutôt que réécrire ; préserver les fonctionnalités existantes.
2. Stdlib uniquement, SQLite local, démarrage gratuit sans service externe.
3. 1000 profils = données versionnées, pas 1000 processus ; workers séparés à baux.
4. Activation sur preuve réelle ; LLM sans fournisseur = différé/bloqué honnête.
5. Aucun fournisseur supposé connecté ; aucun secret dans le dépôt/chat/rapports.
6. Branche Arena fixe ; merge propre de `master`, pas de rebase/force-push ; aucune fusion de PR.
7. Budget strict : réserver avant appel, exposition = soldé + réservé/interrupté incertain.
8. Apprentissage périodique contrôlé : aucune auto-modification du noyau/permissions/sécurité ;
   toute modification importante de code passe par branche, tests, PR et décision humaine.

## Phases
- **Terminées et testées localement** : audit, fondations, mémoire, routeur/conseil, runtime,
  divisions, catalogue 1000, activation/tests, apprentissage périodique, interface, validation,
  durcissement workers/budget/cohérence 1.2.1.
- **En attente d'autorisation / clés** : connexion réelle fournisseurs IA, déploiement cloud,
  exposition publique, promotion dépôt autonome, fusion PR #5, arbitrage PR #2.
- **Évolutions possibles** : embeddings si fournisseur réel, réconciliation des réservations LLM
  interrompues, outils locaux sûrs supplémentaires, convergence conceptuelle avec PR #2.

## Branches / PR / GitHub
- Travail : `arena/ffc77bf1-skills-collection` (nom fixe de session).
- Merge de synchronisation : `b8b3978` depuis `master` `af4b951`.
- Durcissement : `df0c471` + commit final documentation/CI (voir HEAD/PR #5).
- PR #5 : ouverte vers `master`, non fusionnée. PR #2 `omni-research-100` : non touchée.
- CI : `.github/workflows/omnibrain-supreme.yml`, `.github/workflows/omnibrain-v4.yml`.

## Commandes de reprise
Depuis `skills-collection/omni-agents-framework/` :
```bash
python3 -m supreme catalog --check
python3 -m supreme sync
python3 -m supreme evaluate --activate
python3 -m supreme status
python3 -m supreme serve --port 8765 --host 0.0.0.0
python3 -m supreme worker --once --lease-seconds 30 --heartbeat-seconds 5
python3 -m supreme learn --periodic --interval 300 --lease-seconds 30 --heartbeat-seconds 5
python3 -m supreme learn --status
python3 -m supreme audit
python3 -m unittest discover -s tests
```
Arrêt propre worker/learn : `SIGINT` ou `SIGTERM`. Les rapports et baux sont persistés ;
un bail expiré est repris uniquement si le worker est arrêté/silencieux.

## Problèmes / permissions manquantes
- Push vers `omni-agents-framework` autonome : **403** ; lecture `optimiser-mes-agents-IA` : **403** ;
  création de dépôt : **403**. Non contourné.
- Aucune clé fournisseur IA dans l'environnement ; egress sandbox limité.
- Aucun cloud déployé ; aucune dépense engagée.

## Prochaines tâches humaines
1. Connecter un fournisseur réel hors dépôt, puis `python3 -m supreme providers --check`
   et `python3 -m supreme evaluate --activate` sur appel réel réussi.
2. Décider la fusion de la PR #5 et l'arbitrage avec la PR #2.
3. Autoriser ou non cloud/exposition publique/promotion dépôt autonome.
4. Réconciler humainement les réservations LLM interrompues avant toute nouvelle tentative payante.
