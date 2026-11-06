# Suivi durable OMNIBRAIN SUPREME 1000

**Dernière mise à jour : 2026-11-05** · **Version SUPREME : 1.4.0** · Branche :
`arena/ffc77bf1-skills-collection` · PR #5 ouverte, non fusionnée · PR #2 non modifiée.
Racine dépôt : `skills-collection/`. Framework : `skills-collection/omni-agents-framework/`.
Ce document permet une reprise sans perdre le contexte. Aucune fusion de PR n'est autorisée implicitement.

## État actuel vérifié (1.4.0)
- **Alignement inter-dépôts** : voir `ECOSYSTEM-ALIGNMENT.md`. SUPREME vit dans
  `skills-collection` (fork, branche Arena, PR #5 OPEN) ; le document Mistral du dépôt
  `omni-agents-framework` le déclarait « introuvable » à cause de la recherche GitHub
  (forks et branches non par défaut non indexés). Correction documentée avec preuves.
  Deux « PR #5 » distinctes existent : toujours qualifier par le dépôt.
- Couche SUPREME **1.4.0** : protection continue (Guardian), arbitrage mémoire, reprise d'activation
  (re-spécification/réconciliation), contexte modèle attesté, API durcie, exploitation `ops/`.
  Rapport de livraison courant : **`FINAL-COMPLETION-REPORT.md`** ; runbook : **`RUNBOOK.md`**.
- **Schéma SQLite live v4** (33 tables déclarées), migration additive depuis v3, données préservées.
- Audit CLI 1.4.0 : version `1.4.0`, `schema_version=4`, **443 tests découverts**.
- Tests : **442 découverts = 105 V4/non-SUPREME + 338 SUPREME** ; 442 locaux verts + 1 opt-in ignoré.
- Missions réelles cumulées : **13 completed**, **44 tâches done**, **9 divisions**, **18 agents distincts**,
  88 messages bus, 44 mémoires, **0 USD**. Preuves : `validation/missions-real-140-*.json`.
- Répartition exacte clarifiée : **40 spécialistes outil + 20 chefs outil = 60 `monitored`** ;
  **960 spécialistes LLM `validated`** ; 0 `operational` strict.
- Guardian : 11 contrôles ; les constats `core_file_modified` de la livraison 1.4.0 restent ouverts
  jusqu'à re-baseline humaine documentée (`--rebaseline-core --confirm 'REVUE HUMAINE EFFECTUEE'`).
- Sauvegardes durcies **0600/0700** (20 fichiers existants corrigés), 4 sauvegardes intégrité `ok` ;
  vérification `backup --verify` et rétention opt-in `backup --prune N` (simulation par défaut).

- CI **6/6 pass** sur `82262ce9e35496934753eb1f83f4d69342c6335d`
  (runs `42115962570` Supreme, `42115962588` V4 ; Python 3.11/3.12/3.13).
- Commits 1.4.0 : `e2c9628` (livraison) puis `82262ce` (tri de rétention déterministe
  + réponse 413 fiable, défauts révélés par la CI et corrigés, aucun test désactivé).

## Historique 1.3.0 (conservé)
- Couche SUPREME **1.3.0** : fournisseurs/intelligence/activation progressive/CLI/API/dashboard mobile,
  sans reconstruire les composants 1.2.1 stabilisés.
- **Schéma SQLite live v3** appliqué après sauvegarde v2 :
  `omni-agents-framework/var/supreme/backups/bk-20261105T183636-36fe3c/` (intégrité `ok`, schéma `2`).
  Ancienne sauvegarde 1.2.1 conservée : `bk-20261105T163835-22f858`.
- Audit CLI 1.3.0 : `ok=true`, version `1.3.0`, schéma `3`, **378 tests découverts**.
  Preuve : `omni-agents-framework/var/supreme/validation/audit-130-cli.json`.
- Serveur local/preview **1.4.0** démarré sur `0.0.0.0:8765` ; santé `ok`, version `1.4.0`,
  healthcheck `ok=true`, Guardian `ready=true` (0 bloquant), dashboard 14 onglets.
  Sauvegarde préalable : `bk-20261105T215536-41908d`. Ce n'est pas un déploiement cloud public.
- **1020 profils** : 1000 spécialistes + 20 chefs. Statuts live : `registered=0`, `validated=960`,
  `monitored=60`, `operational=0`. **60 outils déterministes locaux opérationnels sur preuve** ;
  **960 agents LLM en attente**.
- **0 clé fournisseur**, **0 fournisseur connecté réellement**, **0 modèle externe découvert en production**,
  **0 inférence externe réussie**, **0 agent LLM opérationnel**, **0 dépense**, **0 cloud**.
- Campagne pilote locale préparée puis bloquée sans clé : `act-a7cf4de1f0bf`, palier 5,
  `external_calls=0`, raison : inférence externe non autorisée (CLI humain requis).
  Preuves : `validation/cli-activation-prepare.json`, `validation/cli-activation-run-blocked.json`.
- Tests : **378 découverts = 105 V4/non-SUPREME + 273 SUPREME**.
  Dernière suite complète : `Ran 378 tests`, `OK (skipped=1)` ; **377 locaux exécutés verts + 1 test réel opt-in ignoré**.
  Journaux : `validation/full-suite-130-final.log`, `validation/supreme-suite-130-final.log`,
  `validation/v4-suite-130-final.log`.

## Modules 1.4.0 à connaître
- `supreme/guardian.py` : 11 contrôles de protection continue, dédup par empreinte, bail unique,
  ordonnanceur périodique, résolution et re-baseline humaines tracées ; ne modifie jamais le noyau.
- `supreme/memory.py` : `resolve_contradiction` (versionnement + provenance + relation `supersedes`,
  aucune ligne effacée) et `open_contradictions`.
- `supreme/activation.py` : paliers 5→20→60→100→200→400→600→800→960, `respecify`, `reconcile_member`
  (remplacement obligatoire pour préserver le palier), preuve post-quarantaine, fencing + heartbeat.
- `supreme/backup.py` : permissions 0600/0700, `verify_all`, `prune` opt-in, `_integrity` sans exception.
- `supreme/api.py` : corps borné (413), JSON invalide 400, validation numérique, endpoints
  guardian/divisions.detail/collaborations/activity/quarantine/respecify/reconcile.
- `ops/` : `supreme-ctl.sh`, 8 unités systemd, Dockerfile, compose.yaml, healthcheck.py, env.example.

## Modules 1.3.0 (conservés)
- `supreme/credentials.py` : env → `*_FILE` → fichier runtime privé 0600 → legacy 0600 ;
  saisie TTY/getpass, pas de secret dans les statuts.
- `supreme/provider_control.py` : autorisation/révocation inférence, prix attestés, preflight,
  vérification, modèles découverts. Fermé par défaut ; CLI humain only pour l'inférence.
- `supreme/providers.py` : transport réel Mistral/OpenAI-compatible/Gemini/Anthropic/Ollama,
  HTTPS hors loopback, pas de retry POST, pas de redirection, usage fournisseur obligatoire.
- `supreme/router.py` : découverte, catalogue persisté, routage sous contraintes, preuves par tentative.
- `supreme/activation.py` : paliers cumulatifs 5→20→60→100→…→960, bail fencé, preuve `external_api`,
  quarantaine isolée, reprise, levée seulement après revue humaine.
- `supreme/council.py` : preuves référencées, second avis borné, `needs_review` si non vérifiable.
- `supreme/planner.py` / `orchestrator.py` : mode LLM explicite sans substitut simulé, cross-division,
  vérificateur indépendant, mémoire centrale seulement si décision vérifiée.
- `supreme/memory.py` : contradictions `subject_key` + `claim_key` + `claim_value`.
- `supreme/evaluation.py` : un représentant LLM ne peut pas être activé sur un stub local.
- `supreme/learning.py` : baseline initiale ≠ gain ; comparaison mesurée avant/après entre cycles.
- `supreme/db.py` : schéma v3 additif, 7 tables fournisseurs/activation.
- `supreme/api.py`, `supreme/dashboard/index.html`, `supreme/audit.py`, `supreme/__main__.py` :
  endpoints/onglets/audit/CLI 1.3.0, données réelles, confirmations explicites.

## Décisions conservées
1. Réutiliser V4 et SUPREME 1.2.1 plutôt que réécrire ; préserver les fonctionnalités existantes.
2. Stdlib uniquement, SQLite local, démarrage gratuit sans service externe.
3. 1000 profils = données versionnées, pas 1000 processus ; workers séparés à baux/heartbeat/fencing.
4. Activation sur preuve réelle ; LLM sans fournisseur = bloqué honnête ; pas de saut 60→1020.
5. Aucun fournisseur supposé connecté ; aucun secret dans le dépôt/chat/rapports ; aucune dépense sans accord.
6. Branche Arena fixe ; merge propre de `master` `af4b951` via `b8b3978` ; pas de rebase/force-push ;
   aucune fusion de PR ; `master` non modifié directement.
7. Budget strict : réserver avant appel, garde atomique, exposition = soldé + réservé/interrompu incertain.
8. Apprentissage contrôlé : aucune auto-modification du noyau/permissions/sécurité ;
   toute modification importante passe par branche, tests, comparaison, rollback, PR humaine.
9. Dashboard mobile prioritaire, données réelles uniquement ; actions sensibles confirmation explicite.
10. « Vide (Mistral AI) » est l'affichage du connecteur `mistral`, pas un second endpoint inventé.

## Phases
- **Terminées et testées localement** : audit, fondations, mémoire, routeur/conseil, runtime,
  divisions, catalogue 1000, activation/tests, apprentissage périodique, interface, validation,
  durcissement 1.2.1, activation intelligence réelle 1.3.0 (code + tests locaux + migration live v3).
- **En attente d'autorisation / clés** : connexion réelle fournisseurs IA, inférence externe bornée,
  activation réelle des agents LLM par paliers, déploiement cloud, exposition publique,
  promotion dépôt autonome, fusion PR #5, arbitrage PR #2.
- **Évolutions possibles après accord** : embeddings si fournisseur réel, réconciliation des réservations
  incertaines, outils locaux sûrs supplémentaires, convergence conceptuelle avec PR #2.

## Branches / PR / GitHub
- Travail : `arena/ffc77bf1-skills-collection` (nom fixe de session).
- Historique 1.2.1 : merge `b8b3978`, commits `df0c471`, `a46a30e`.
- Livraison 1.3.0 : commit principal `5b226070ae856ef02ec24ca560f7865b8035eab2`, poussé et visible dans PR #5.
- PR #5 : ouverte vers `master`, non fusionnée. PR #2 `omni-research-100` : non touchée.
- CI : `.github/workflows/omnibrain-supreme.yml`, `.github/workflows/omnibrain-v4.yml` ;
  **6/6 pass** sur `5b22607` (runs `42091613321`, `42091613381`).
- Permissions manquantes documentées : push dépôt autonome 403, création dépôt 403,
  lecture `optimiser-mes-agents-IA` 403 ; non contournées.

## Commandes de reprise
Depuis `skills-collection/omni-agents-framework/` :
```bash
python3 -m supreme catalog --check
python3 -m supreme status
python3 -m supreme providers --status
python3 -m supreme mistral status
python3 -m supreme activation --status
python3 -m supreme audit
python3 -m unittest discover -s tests
python3 -m supreme serve --port 8765 --host 0.0.0.0
python3 -m supreme worker --once --lease-seconds 30 --heartbeat-seconds 5
python3 -m supreme learn --status
```
Connexion réelle Mistral, seulement en terminal privé opérateur :
```bash
python3 -m supreme providers --connect mistral
python3 -m supreme providers --verify mistral
python3 -m supreme providers --set-prices mistral --model MODELE_DECOUVERT \
  --input-per-million USD --output-per-million USD --source https://SOURCE_OFFICIELLE \
  --confirm 'JE CONFIRME LES PRIX'
python3 -m supreme providers --authorize mistral --budget-usd 0.25 --max-calls 5 --hours 1 \
  --confirm 'AUTORISER INFERENCE'
python3 -m supreme activation --prepare 5 --provider mistral --model MODELE_DECOUVERT
python3 -m supreme activation --run CAMPAGNE_ID
```
Arrêt propre worker/learn/serve : `SIGINT` ou `SIGTERM`. Les rapports et baux sont persistés ;
un bail expiré est repris uniquement si le worker est arrêté/silencieux.

## Problèmes / limites actuelles
- Aucune clé fournisseur IA dans l'environnement ; egress sandbox limité. Une tentative Mistral
  a échoué au handshake TLS avant HTTP ; ce n'est pas une preuve d'authentification invalide.
- Connecteur Arena `mistral` : non disponible.
- Aucun cloud déployé ; aucune dépense engagée ; aucune campagne LLM réelle réussie.
- La campagne pilote `act-a7cf4de1f0bf` reste bloquée tant qu'un fournisseur réel n'est pas connecté/autorisé.
- Les tests réels opt-in sont ignorés sans identifiant privé et `SUPREME_REAL_MISTRAL_TESTS=1`.

## Prochaines tâches humaines
1. Connecter un fournisseur réel hors dépôt/chat, puis découverte GET, prix attestés, autorisation bornée.
2. Lancer le palier 5 réel, inspecter preuves/coûts, puis seulement étendre 20→60→100→…→960.
3. Décider la fusion de la PR #5 et l'arbitrage avec la PR #2.
4. Autoriser ou non cloud/exposition publique/promotion dépôt autonome.
5. Réconciler humainement toute réservation LLM interrompue avant nouvelle tentative payante.
