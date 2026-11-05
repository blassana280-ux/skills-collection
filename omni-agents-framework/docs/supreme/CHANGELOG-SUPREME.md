# Changelog OMNIBRAIN SUPREME

Version de livraison courante : **SUPREME 1.3.0**. Le paquet V4 historique
`omnibrain-framework` reste à `1.0.0` dans `omni-agents-framework/pyproject.toml` ;
il ne faut pas confondre cette version V4 avec la version de la couche SUPREME.
Racine dépôt : `skills-collection/`. Chemins ci-dessous relatifs à
`skills-collection/omni-agents-framework/` sauf mention contraire.

## 1.3.0 — 2026-11-05 (activation intelligence réelle : Mistral, campagnes, conseil vérifiable)
### Ajouté / durci
- **Mistral/Vide** : adaptateur HTTP officiel `/v1/models` + `/v1/chat/completions`, Bearer en en-tête,
  découverte de modèles, parsing capacités/contexte/usage, erreurs/délais bornés, pas de retry automatique
  des POST d'inférence, pas de redirection suivie, journalisation sans secrets.
- **Connexion sécurisée sans clé dans le chat** : `providers --connect mistral` (getpass, terminal privé),
  env, `MISTRAL_API_KEY_FILE`, fichier runtime `var/supreme/secrets/mistral.key` 0600/répertoire 0700 ;
  refus des permissions trop larges, symlinks, fichiers non détenus par l'utilisateur courant.
- **Autorisation d'inférence fermée par défaut** : `provider_controls`, confirmation humaine CLI,
  plafond USD, nombre d'appels, expiration ≤24 h, quotas centraux, garde atomique dans la réservation.
  Aucune autorisation d'inférence via l'API publique ; découverte GET séparée de la génération.
- **Prix attestés** : pas de génération externe sans prix déclarés par l'opérateur, source HTTPS,
  fraîcheur ≤30 jours ; le coût réel est soldé sur l'usage fournisseur, une réponse sans usage est incertaine.
- **Activation progressive** : paliers cumulatifs 5 → 20 → 60 → 100 → +100 → 960 agents LLM,
  sélection round-robin entre divisions, preuve `external_api` obligatoire, sortie JSON exploitable,
  permissions/budget vérifiés, quarantaine isolée, reprise après interruption, revue humaine pour lever la quarantaine.
  Un stub local ne peut pas activer un agent LLM.
- **Conseil vérifiable** : seules les références vers les preuves fournies comptent ; confiance auto-déclarée
  insuffisante ; second avis borné si désaccord ; statut `needs_review` au lieu d'une fausse décision.
- **Planification multi-spécialités** : mode LLM explicite sans substitut local simulé, sélection cross-division,
  vérification structurelle indépendante distinguée de la vérité métier.
- **Mémoire** : contradictions fondées sur `subject_key` + `claim_key` + `claim_value`, pas sur la simple formulation.
- **Apprentissage** : comparaison mesurée avant/après entre cycles persistés ; une baseline initiale n'est pas un gain.
- **Dashboard mobile** : fournisseurs/modèles, activation, décisions, performances par division, coûts/exposition,
  réservations, alertes ; échappement HTML des données externes.
- **Schéma SQLite v3 additif** : contrôles fournisseurs, modèles découverts, vérifications, campagnes,
  membres, preuves d'activation, quarantaine. Aucune suppression de données.
### Tests à cette livraison
- **378 tests découverts** = **105 V4/non-SUPREME + 273 SUPREME**.
- **377 tests locaux exécutés verts + 1 test fournisseur réel opt-in ignoré** faute d'identifiant et d'egress.
  Aucun fournisseur IA réel connecté, aucun cloud, aucune dépense.

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
- Suite complète réelle : **378 tests verts** = **105 V4/non-SUPREME + 273 SUPREME**.
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
