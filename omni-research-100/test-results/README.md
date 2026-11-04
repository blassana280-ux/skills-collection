# Résultats de tests (versionnés volontairement)

Produits par une exécution réelle locale le 2026-11-03 (UTC) et reproduits par
la CI GitHub Actions. Voir `../docs/TEST_RESULTS.md` pour l'analyse complète.

- `junit.xml` — 79 tests Python, 0 échec
- `node.txt` — 16 tests d'interface (5 statiques + 11 DOM jsdom), 0 échec
- `agent_results.json` — 100/100 `OPÉRATIONNELLE ET TESTÉE`
- `offline_verification.json` — pipeline bout en bout, verdict `NEEDS_WORK`
  (double de test hors ligne ⇒ gate `real_provider=false`, comportement voulu)
- `dependency_audit.json` — 11 dépendances épinglées, politique `PASS`
- `live_api_full.json` — 38/38 contrôles HTTP réels sur l'application lancée
- `delivery_repo_check.json` — vérification du dépôt privé livré : BLOQUÉ (403)
