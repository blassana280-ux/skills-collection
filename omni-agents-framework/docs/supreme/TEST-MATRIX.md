# Matrice des tests OMNIBRAIN SUPREME 1.4.0

Racine dépôt : `skills-collection/`. Framework : `skills-collection/omni-agents-framework/`.
Dernière exécution réelle locale : **455 tests découverts** = **105 V4/non-SUPREME + 350 SUPREME**.
Résultat : **454 tests locaux exécutés verts + 1 test fournisseur réel opt-in ignoré** (`OK (skipped=1)`).

Commandes exécutées depuis `skills-collection/omni-agents-framework/` :
```bash
python3 -m unittest discover -s tests                              # 455 découverts, OK (skipped=1)
python3 -m unittest discover -s tests -p "test_supreme_*.py"       # 350 découverts, OK (skipped=1)
# V4/non-SUPREME : 105 OK (sélection des modules non test_supreme_*)
python3 -m unittest tests.test_supreme_hardening                   # 20 OK
python3 -m supreme audit                                           # ok=true, version 1.4.0, schéma 4
```
Journaux locaux gitignorés : `omni-agents-framework/var/supreme/validation/`
(`full-suite-140-final.log`, `supreme-suite-140-final.log`, `v4-suite-140-final.log`,
`final-140-new-tests.log`, `audit-140-cli.json`).
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
| `omni-agents-framework/tests/test_supreme_intelligence.py` | explicabilité, arbitrage conseil, non-activation LLM sur stub local, échec/différé honnête | 9 |
| `omni-agents-framework/tests/test_supreme_operations.py` | worker subprocess, audit exécutable, cycle d'apprentissage, noyau protégé | 9 |
| `omni-agents-framework/tests/test_supreme_hardening.py` | migration additive v1→v4, deux workers réels, SIGKILL/SIGTERM, fencing, apprentissage périodique/CLI, budget conseil/quotas concurrents | 20 |
| `omni-agents-framework/tests/test_supreme_docs_coherence.py` | version courante dans les documents de livraison ; PV historique 1.3.0 préservé ; phrases de confirmation code↔docs ; décompte TEST-MATRIX égal à la découverte unittest réelle | 4 |
| `omni-agents-framework/tests/test_supreme_activation_130.py` | **1.3.0** : credentials sécurisés, adaptateur Mistral local, autorisation/prix/quotas, campagnes progressives, quarantaine, conseil/second avis, mémoire/apprentissage, API/dashboard ; inclut 1 test réel opt-in ignoré sans clé | 38 |
| `omni-agents-framework/tests/test_supreme_e2e.py` | mission réelle → mémoire → télémétrie → rapport → traçabilité | 1 |
| `omni-agents-framework/tests/test_supreme_final_140.py` | **1.4.0** : Guardian (11 contrôles, dédup, bail concurrent, résolution humaine, non-mutation, re-baseline tracée), paliers 5→960, preuve post-quarantaine, reprise propriétaire vivant/mort, re-spécification campagne, réconciliation membre avec remplacement, contexte attesté HTTPS, parsing `context_length`, arbitrage mémoire sans suppression, ACL, corps API borné 413/400, validation numérique, contrat JSON opt-in, sauvegardes 0600/0700 + vérification + rétention opt-in, endpoints exploitation, ordre de rétention déterministe, scripts ops/systemd, kit d'enrôlement fournisseur (TTY, anti-trace, budget sans prix inventé), alignement inter-dépôts | 75 |
| **Total SUPREME** | | **350** |
| **V4/non-SUPREME** | modules historiques `test_catalog`, `test_classifier`, `test_cli`, `test_dispatcher`, `test_frontmatter`, `test_gates`, `test_parallel`, `test_registry`, `test_router`, `test_wrapper`, `test_v4_*` | **105** |
| **Total général** | | **455** |

## Catégories strictement séparées
| Catégorie | Description | État 1.4.0 |
| --- | --- | --- |
| **Tests simulés (fixtures)** | Données injectées explicitement, aucun réseau | conseil avec analyses fixtures, routage fixture |
| **Tests locaux réels** | SQLite, subprocess, signaux POSIX, outils déterministes, HTTP vers stub 127.0.0.1 | **454 exécutés verts** ; stub ≠ fournisseur IA réel |
| **Tests fournisseurs IA réels** | Appel API réel avec clé vers fournisseur externe | **0 exécuté** ; 1 test opt-in ignoré ; aucune clé, egress sandbox limité |
| **Tests cloud réels** | Déploiement cloud vérifié | **0** : aucun cloud déployé |

## Durcissement 1.3.0 — scénarios obligatoires couverts (conservés)
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

## Activation intelligence réelle 1.3.0 — scénarios couverts (conservés)
- Clé saisie sans écho dans un terminal privé ; fichier 0600/répertoire 0700 ; env prioritaire ;
  `*_FILE` supporté ; permissions trop larges/symlinks refusés ; aucun secret dans les métadonnées.
- Adaptateur Mistral local : `/models`, capacités/contexte, `/chat/completions` non streamé, usage,
  retry GET borné, POST jamais rejoué automatiquement, redirection non suivie, HTTPS hors loopback,
  réponse sans usage traitée comme incertaine, secret expurgé des erreurs réseau.
- Autorisation d'inférence fermée par défaut, confirmation humaine, expiration, plafond USD/nombre
  d'appels, garde atomique dans `BudgetController.reserve`, prix attestés et expirables.
- Campagne pilote 5 répartis sur 5 divisions ; saut de palier refusé ; exécution sans clé bloquée ;
  stub local non activant ; permissions fautives isolées sans annuler les autres ; revue humaine requise.
- Conseil : second avis borné sur désaccord, preuves inventées non vérifiées, statut `needs_review`.
- Mémoires successives avec provenance ; contradictions sur valeur déclarée plutôt que formulation ;
  cycles d'apprentissage persistés avec comparaison mesurée avant/après.
- API/dashboard : confirmations explicites, endpoints activation/décisions/performances/exposition,
  sections mobiles et échappement HTML.

> Un test local réel contre un stub HTTP n'est pas une intégration fournisseur réelle.
> Un serveur local n'est pas un déploiement cloud. Les 960 agents LLM restent en attente
> tant qu'un fournisseur réel n'a pas été connecté et vérifié par appel réussi.
