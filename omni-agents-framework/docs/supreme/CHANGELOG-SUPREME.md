# Changelog OMNIBRAIN SUPREME

Version de livraison courante : **SUPREME 1.2.1**. Le paquet V4 historique
`omnibrain-framework` reste à `1.0.0` dans `omni-agents-framework/pyproject.toml` ;
il ne faut pas confondre cette version V4 avec la version de la couche SUPREME.
Racine dépôt : `skills-collection/`. Chemins ci-dessous relatifs à
`skills-collection/omni-agents-framework/` sauf mention contraire.

## 1.2.1 — 2026-11-05 (durcissement final : workers, apprentissage, budget, cohérence)
### Corrigé / durci
- **Concurrence workers** : `recover()` ne réinitialise plus toutes les missions `running`.
  Ajout de `omni-agents-framework/supreme/leases.py` : worker_id unique, propriétaire,
  bail expirant, heartbeat, jeton de fencing, récupération exclusive des missions
  abandonnées (bail expiré + worker arrêté/silencieux), arrêt propre et reprise après crash.
- **Idempotence de commit** : table `task_executions` ; un résultat de tâche n'est commité
  qu'une fois. Les écritures de l'ancien propriétaire sont refusées après perte du bail.
  Un appel LLM interrompu avec réservation incertaine est bloqué pour réconciliation
  humaine avant nouvelle tentative, afin d'éviter une double facturation aveugle.
- **Schéma SQLite v2 additif** : migration sans suppression de données ; sauvegarde
  préalable créée (`bk-20261105T163835-22f858`, intégrité `ok`). Test de migration v1→v2.
- **Apprentissage continu** : `LearningEngine.run_cycle()` persiste chaque rapport
  (`learning_runs` + `omni-agents-framework/var/supreme/learning/`), protégé par un index
  unique contre deux cycles simultanés, heartbeat de cycle, erreurs surveillées,
  interruption propre et reprise après bail expiré. Ajout `LearningScheduler` et
  `python3 -m supreme learn --periodic --interval N [--max-cycles N] [--status]`.
- **Budget strict** : `BudgetController.reserve/settle/release` avec transaction
  `BEGIN IMMEDIATE`, exposition = dépenses soldées + réservations ouvertes/interrompues.
  Le routeur réserve une borne supérieure avant chaque appel, solde sur l'usage réel,
  trace fournisseur/modèle/statut/réservation, bloque les dépassements individuels et
  collectifs, respecte les quotas centraux et les limites de tokens/contexte.
- **Conseil multi-modèles** : ne contourne plus le routeur via `router.client.complete`.
  Chaque analyse passe par `router.complete`, sans fallback interne au conseil, avec
  plafond collectif conservateur fondé sur les bornes de coût, pas seulement le coût réel.
- **Audit exécutable** : version, schéma, workers/baux, tâches orphelines, cycles
  d'apprentissage, réservations et violations de quotas ; code de sortie non nul si échec.
- **Synchronisation GitHub** : merge propre de `master` `af4b951` dans la branche de
  travail, sans réécriture d'historique, sans modification directe de `master`, sans fusion de PR.
### Tests
- Suite complète réelle : **340 tests verts** = **105 V4/non-SUPREME + 235 SUPREME**.
- Ajout `omni-agents-framework/tests/test_supreme_hardening.py` : 20 tests locaux réels
  (multi-processus, SIGKILL/SIGTERM, fencing, migration, apprentissage périodique,
  budget/conseil, quotas concurrents). Aucun fournisseur IA réel, aucun cloud.

## 1.2.0 — 2026-11-05 (intelligence, opérations, audit — finalisation A→J)
### Ajouté
- **Explicabilité OmniBrain** : chaque plan porte `explanation` et chaque tâche `why`.
  Exposé via `/api/missions/{id}` et le bouton « Pourquoi ? » du dashboard.
- **Arbitrage intégré** : missions complexes → conseil multi-modèles sur preuves réelles ;
  sans fournisseur → statut `unavailable` honnête.
- **Évaluation LLM réelle** : `EvaluationEngine(router=...)` tente un vrai appel ;
  activation sur preuve, échec réel non différé, différé honnête sans fournisseur.
- **Worker séparé (première version)** : file persistante + claim atomique + subprocess.
  Durci en 1.2.1 par baux/heartbeat/fencing.
- **Audit exécutable** : `python3 -m supreme audit`, rapport JSON archivé.
- **Cycle d'amélioration ponctuel** : `run_cycle()` ; rendu périodique et persistant en 1.2.1.
- **Historique par agent** : `/api/agents/{id}/history`, détail `/api/missions/{id}`.
### Tests à cette livraison
- **318 tests verts** (105 V4 + 213 SUPREME).

## 1.1.0 — 2026-11-05 (multi-modèles réel, sécurité, dashboard)
### Ajouté
- Client multi-fournisseurs HTTP réel (`supreme/providers.py`), Mistral/Vide prioritaire,
  fallback, clés via env/fichier gitignoré 0600, jamais journalisées.
- Agents LLM exécutables via routeur si fournisseur configuré ; blocage honnête sinon.
- Audit sécurité, dashboard coûts/sécurité, API providers/alerts/security.
- Mémoire TF-IDF cosinus locale réelle (`mode='tfidf'`) ; embeddings neuronaux indisponibles
  sans fournisseur, signalés honnêtement.
- Documentation PROVIDERS/ECOSYSTEM.
### Tests à cette livraison
- **298 tests verts** (105 V4 + 193 SUPREME) après ajout du mode TF-IDF API/dashboard.
  Étapes intermédiaires : 267 (162 SUPREME), 294 (189), 297 (192), 298 (193).
### Honnêteté
- 0 fournisseur IA réel connecté ; tests HTTP contre stub local = local réel, pas fournisseur réel.

## 1.0.2 — 2026-11-05 (sécurité : jeton API + journal d'accès)
- Rotation de jeton sûre 256 bits, fichier 0600, ancien jeton révoqué sur disque,
  jamais affiché ; journal d'accès expurgé ; tests anti-fuite.
- **244 tests verts** (105 V4 + 139 SUPREME).

## 1.0.1 — 2026-11-05 (durcissement concurrence thread)
- Connexion SQLite par thread (WAL) pour workers DAG/API ; correction `database is locked`.
- **231 tests verts** (105 V4 + 126 SUPREME).

## 1.0.0 — 2026-11-05
- Couche SUPREME complète au-dessus d'OmniBrain V4 : 20 divisions × 50 spécialistes
  + 20 chefs, registre, DAG, bus, mémoire 4 niveaux, routeur/conseil, policy, évaluation,
  apprentissage, budget, observabilité, backup, API/dashboard, reporting, outils déterministes.
- **221 tests verts** (105 V4 + 116 SUPREME).
- Limites : aucun fournisseur IA connecté, embeddings inactifs, promotion dépôt autonome 403.
