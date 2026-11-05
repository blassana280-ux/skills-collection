# Matrice des tests OMNIBRAIN SUPREME 1.2.1

Racine dépôt : `skills-collection/`. Framework : `skills-collection/omni-agents-framework/`.
Dernière exécution réelle locale : **340 tests verts** = **105 V4/non-SUPREME + 235 SUPREME**.

Commandes exécutées depuis `skills-collection/omni-agents-framework/` :
```bash
python3 -m unittest discover -s tests                              # 340 OK
python3 -m unittest discover -s tests -p "test_supreme_*.py"       # 235 OK
# V4/non-SUPREME : 105 OK (sélection des modules non test_supreme_*)
python3 -m unittest tests.test_supreme_hardening                   # 20 OK
python3 -m supreme audit                                           # ok=true, version 1.2.1
```
Journaux locaux gitignorés : `omni-agents-framework/var/supreme/validation/`.
CI : `.github/workflows/omnibrain-supreme.yml` + `.github/workflows/omnibrain-v4.yml`
(Python 3.11/3.12/3.13). Les contrôles GitHub sont vérifiés sur la branche de la PR #5.

| Fichier | Couverture | Tests |
| --- | --- | --- |
| `omni-agents-framework/tests/test_supreme_catalog.py` | 1000 agents, 20×50, unicité, champs, évals, permissions, déterminisme, anti-clones | 9 |
| `omni-agents-framework/tests/test_supreme_tools.py` | outils déterministes : fixtures réelles, entrées vides, erreurs, sécurité | 9 |
| `omni-agents-framework/tests/test_supreme_registry.py` | sync idempotent, statuts sur preuve, recherche, divisions | 7 |
| `omni-agents-framework/tests/test_supreme_factory.py` | création, doublons, incomplétude, update/rollback, suppression contrôlée | 6 |
| `omni-agents-framework/tests/test_supreme_policy.py` | niveaux de risque, actions protégées, approbations, RBAC | 6 |
| `omni-agents-framework/tests/test_supreme_bus.py` | anti-usurpation, ACL, dédup, ack, file morte, injection | 7 |
| `omni-agents-framework/tests/test_supreme_memory.py` | 4 niveaux, ACL, FTS, versions, TTL, graphe, contradictions, rédaction, TF-IDF | 16 |
| `omni-agents-framework/tests/test_supreme_router.py` | détection, indisponibilité honnête, fixtures, confidentialité + conseil preuves ≠ majorité | 8 |
| `omni-agents-framework/tests/test_supreme_budget.py` | quotas, coupure, alertes, multi-scopes, coût nul local | 6 |
| `omni-agents-framework/tests/test_supreme_planner.py` | classification, DAG valide, tâches explicites, permissions, cycles | 6 |
| `omni-agents-framework/tests/test_supreme_orchestrator.py` | DAG réel, parallélisme, dépendances, idempotence, annulation, reprise, blocage LLM, threads | 10 |
| `omni-agents-framework/tests/test_supreme_evaluation.py` | 7 tests/profil, activation sur preuve, différés, évaluation globale | 6 |
| `omni-agents-framework/tests/test_supreme_learning.py` | collecte, analyse, stratégies, gain, rollback, noyau protégé | 6 |
| `omni-agents-framework/tests/test_supreme_observability.py` | KPIs réels/null, anti-doublons, traces, pas de secrets | 7 |
| `omni-agents-framework/tests/test_supreme_backup.py` | sauvegarde/restauration, intégrité, refus corruption | 2 |
| `omni-agents-framework/tests/test_supreme_api.py` | auth, écritures protégées, données réelles, dashboard, concurrence, sécurité jeton, observabilité, TF-IDF, historique | 45 |
| `omni-agents-framework/tests/test_supreme_providers.py` | mode sans fournisseur, client HTTP stub local, erreurs, fallback, priorité, conseil, sécurité clés, mission LLM stub | 23 |
| `omni-agents-framework/tests/test_supreme_security_audit.py` | anti-fuite dépôt, fichiers secrets non suivis, isolation profils, anti-injection, actions protégées, stdlib | 15 |
| `omni-agents-framework/tests/test_supreme_intelligence.py` | explicabilité, arbitrage conseil, activation LLM sur appel stub réussi/échoué/différé | 9 |
| `omni-agents-framework/tests/test_supreme_operations.py` | worker subprocess, audit exécutable, cycle d'apprentissage, noyau protégé | 9 |
| `omni-agents-framework/tests/test_supreme_hardening.py` | **1.2.1** : migration v1→v2, deux workers réels, SIGKILL/SIGTERM, fencing, apprentissage périodique/CLI, budget conseil/quotas concurrents | 20 |
| `omni-agents-framework/tests/test_supreme_docs_coherence.py` | **1.2.1** : version courante dans les documents de livraison ; décompte TEST-MATRIX égal à la découverte unittest réelle | 2 |
| `omni-agents-framework/tests/test_supreme_e2e.py` | mission réelle → mémoire → télémétrie → rapport → traçabilité | 1 |
| **Total SUPREME** | | **235** |
| **V4/non-SUPREME** | modules historiques `test_catalog`, `test_classifier`, `test_cli`, `test_dispatcher`, `test_frontmatter`, `test_gates`, `test_parallel`, `test_registry`, `test_router`, `test_wrapper`, `test_v4_*` | **105** |
| **Total général** | | **340** |

## Catégories strictement séparées
| Catégorie | Description | État 1.2.1 |
| --- | --- | --- |
| **Tests simulés (fixtures)** | Données injectées explicitement, aucun réseau | conseil avec analyses fixtures, routage fixture |
| **Tests locaux réels** | SQLite, subprocess, signaux POSIX, outils déterministes, HTTP vers stub 127.0.0.1 | 340 tests locaux ; stub ≠ fournisseur IA réel |
| **Tests fournisseurs IA réels** | Appel API réel avec clé vers fournisseur externe | **0** : aucune clé, egress sandbox limité |
| **Tests cloud réels** | Déploiement cloud vérifié | **0** : aucun cloud déployé |

## Durcissement 1.2.1 — scénarios obligatoires couverts
- Worker A commence une mission ; worker B démarre pendant l'exécution : B ne récupère
  pas la mission active, A termine, **un seul résultat commité** (`task_executions=1`).
- Arrêt brutal `SIGKILL` de A puis redémarrage : bail expiré + worker silencieux,
  récupération exclusive, mission complétée une seule fois, `run_attempts=2`.
- `SIGTERM` : arrêt propre, mission replanifiée, redémarrage complète sans doublon de résultat.
- Bail perdu/fencing : l'ancien propriétaire ne peut pas committer une complétion.
- Deux cycles d'apprentissage simultanés : le second est `skipped` ; rapports persistés ;
  erreur surveillée ; bail expiré interrompu puis repris ; CLI périodique borné et `SIGTERM`.
- Conseil : réservation avant HTTP, budget individuel/collectif, quota central, tokens,
  erreur 500 incertaine conservée en réservation, 401 libéré, réservations concurrentes.

> Un test local réel contre un stub HTTP n'est pas une intégration fournisseur réelle.
> Un serveur local n'est pas un déploiement cloud. Les 960 agents LLM restent en attente
> tant qu'un fournisseur réel n'a pas été connecté et vérifié par appel réussi.
