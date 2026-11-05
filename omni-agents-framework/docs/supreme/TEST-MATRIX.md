# Matrice des tests OMNIBRAIN SUPREME

Suite : `python3 -m unittest discover -s tests` → **221 tests** (105 V4 + 116 SUPREME), tous verts.
CI : `.github/workflows/omnibrain-supreme.yml` (Python 3.11/3.12/3.13).

| Fichier | Couverture | Tests |
| --- | --- | --- |
| `test_supreme_catalog.py` | 1000 agents, 20×50, unicité, 27 champs, 7 évals, permissions, déterminisme, anti-clones | 9 |
| `test_supreme_tools.py` | 42 outils : fixtures réelles, entrées vides, cas d'erreur, sécurité | 9 |
| `test_supreme_registry.py` | sync idempotent, statuts sur preuve, recherche, divisions | 7 |
| `test_supreme_factory.py` | création, doublons, incomplétude, update/rollback, suppression contrôlée | 6 |
| `test_supreme_policy.py` | niveaux de risque, actions protégées, approbations, RBAC | 6 |
| `test_supreme_bus.py` | anti-usurpation, ACL, dédup, ack, file morte, injection | 7 |
| `test_supreme_memory.py` | 4 niveaux, ACL, FTS, versionnement, TTL, graphe, contradictions, rédaction, non-fiable, suppression | 13 |
| `test_supreme_router.py` | détection réelle, indisponibilité honnête, fixtures, confidentialité | 5 |
| `test_supreme_council.py` (dans router) | conseil indisponible, décision par preuves ≠ majorité, budget | 3 |
| `test_supreme_budget.py` | quotas, coupure, alertes, multi-scopes, coût nul local | 6 |
| `test_supreme_planner.py` | classification, DAG valide, tâches explicites, permissions, cycles | 6 |
| `test_supreme_orchestrator.py` | exécution réelle, parallélisme, dépendances, idempotence, annulation, reprise, blocage LLM, permissions | 9 |
| `test_supreme_evaluation.py` | 7 tests/profil, activation sur preuve, différés, évaluation globale | 6 |
| `test_supreme_learning.py` | collecte, analyse, stratégies, gain, rollback, noyau protégé | 6 |
| `test_supreme_observability.py` | KPIs réels/null, anti-doublons, traces, pas de secrets | 7 |
| `test_supreme_backup.py` | sauvegarde/restauration, intégrité, refus corruption | 2 |
| `test_supreme_api.py` | auth, lecture anonyme, écritures protégées, données réelles, dashboard | 8 |
| `test_supreme_e2e.py` | mission réelle → mémoire → télémétrie → rapport → traçabilité | 1 |

## Tests particuliers des agents (7 par profil, exécutés sur 1020 profils)
load, config, representative (outil réel ou différé), structured_output, permissions, errors, quality.

## Tests système globaux
Mission reçue/décomposée/exécutée, agents sélectionnés, parallélisme, résultats vérifiés,
mémoire consultée selon permissions, échecs traités, permissions respectées, traçabilité,
reprise après panne, interface sur données réelles.
