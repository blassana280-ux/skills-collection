# Résultats de tests — exécutés et conservés

Date : 2026-11-03 (UTC). Environnement : Python 3.11.2, Node v22.22.3,
FastAPI 0.115.6, Pydantic 2.10.4, SQLAlchemy 2.0.36, SQLite en mémoire/fichier
temporaire, `httpx.MockTransport` pour les hôtes HTTP externes.

## Commandes réellement exécutées

```bash
.venv/bin/python -m pytest -q --junitxml=test-results/junit.xml
node --test tests/test_web_ui.test.js tests/test_web_ui_dom.test.js
.venv/bin/python scripts/verify_offline.py
.venv/bin/python scripts/audit_dependencies.py
.venv/bin/python scripts/gen_profiles.py --check
.venv/bin/python scripts/verify_omnibrain_contract.py
.venv/bin/python scripts/verify_providers_live.py
```

Codes de retour : **0 pour les sept commandes** (les deux vérifications
supplémentaires produisent des rapports JSON conservés).

## Résultat global

| Suite | Tests | Échecs | Erreurs | Ignorés |
|---|---|---|---|---|
| `pytest` (Python) | **79** | 0 | 0 | 0 |
| `node --test` (interface) | **16** | 0 | 0 | 0 |
| Vérification hors ligne de bout en bout | 1 pipeline FAST | 0 | — | — |
| **Total** | **95 tests + 1 pipeline** | **0** | **0** | **0** |

Durée pytest : 16,371 s. Durée Node : 58,1 ms.

**CI GitHub Actions** : PR #2, run `41727343863` → **SUCCÈS** (1 min 03 s) :
intégrité des 100 profils, analyse locale des dépendances, `pip-audit`,
79 tests Python, catalogue régénéré, 16 tests Node, vérification hors ligne,
artefacts conservés. Un premier run (`41727016713`) a échoué sur l'intégrité des
profils générés car `test-results/agent_results.json` était exclu par la règle
racine `*_results.json` ; corrigé par une négation dans le `.gitignore` du
produit (commit `824072f`), puis CI verte.

## Ventilation par fichier (`test-results/junit.xml`)

| Fichier | Tests | Couverture |
|---|---:|---|
| `tests/test_agents_all_100.py` | 4 | 100 profils, 100 handlers exécutés, 100 empreintes distinctes, schémas, liste blanche, entrées invalides ; écrit `test-results/agent_results.json` |
| `tests/test_agent_registry.py` | 5 | validation 100/10×10, sélection, export OmniBrain, alignement des actions dangereuses |
| `tests/test_security.py` | 5 | hachage/JWT, permissions, anti-injection, SSRF, rédaction |
| `tests/test_providers.py` | 11 | parseurs SearXNG/Tavily/Brave/Exa/Firecrawl, clés absentes, quotas, extraction, modèles |
| `tests/test_router.py` | 6 | routage, parallélisme, bascule, déduplication, vérification, cap `providers_real` |
| `tests/test_brain.py` | 5 | planificateur, ordonnanceur, collecteur, consensus, synthétiseur |
| `tests/test_modes.py` | 5 | FAST/DEEP/MAXIMUM, couverture des 100 agents, limites de concurrence honnêtes |
| `tests/test_concurrency.py` | 2 | pic de concurrence mesuré, agents en file |
| `tests/test_failures.py` | 4 | fournisseur en panne, agent défaillant, pannes réseau, verdict `NEEDS_WORK` honnête |
| `tests/test_memory.py` | 5 | persistance, cache réutilisable, événements rejouables, audit, sauvegarde, purge confirmée |
| `tests/test_citations.py` | 3 | table des preuves, citations validées, données web non fiables |
| `tests/test_bootstrap.py` | 3 | garanties du script de reprise : aucun force-push/fusion/suppression, `main` sans code produit, 4 branches empilées, refus d'écraser un dépôt non vide |
| `tests/test_api.py` | 7 | cycle de mission complet via HTTP, auth/RBAC, agents/fournisseurs/réglages/métriques, SSE, erreurs |
| `tests/test_omnibrain.py` | 8 | contrat, clé, version sur TOUTES les routes, cycle complet, `mode` racine (bug corrigé), file JSONL, absence de droits admin |
| `tests/test_deployment_and_ssrf.py` | 6 | garde DNS SSRF avec résolveur contrôlé (IPv4 privée/publique, échec DNS, mode hors ligne), cohérence Docker/compose/SearXNG, syntaxe et confirmation des scripts de sauvegarde |

Tests de l'interface : `tests/test_web_ui.test.js` (5 tests statiques :
absence de données fictives, absence de `innerHTML`, vrais endpoints,
PWA/service worker qui ne cache pas `/api/*`, responsive) et
`tests/test_web_ui_dom.test.js` (**11 tests exécutés dans un vrai DOM jsdom** :
santé, connexion, 3 modes, lancement de mission, SSE authentifié, agents,
sources, contradictions, rapport anti-XSS, historique, fournisseurs,
paramètres, test fournisseur sans clé, déconnexion). Ces tests exécutent le
`app/web/app.js` réel ; seul `fetch` est remplacé par des réponses de forme
identique à l'API. Aucun navigateur réel n'est encore utilisé.

## Fichiers conservés (`test-results/`, versionnés)

| Fichier | Contenu |
|---|---|
| `junit.xml` | Rapport JUnit des 79 tests |
| `pytest.txt` | Sortie console pytest |
| `node.txt` | Sortie console Node |
| `agent_results.json` | État individuel des 100 agents |
| `offline_verification.json` | Pipeline réel hors ligne : statut, verdict, gates, sources, mémoire |
| `verify_offline.txt` | Sortie console de la vérification |
| `dependency_audit.json` / `.txt` | 11 dépendances épinglées, politique `PASS` |
| `generated_profiles.txt` | Intégrité des fichiers générés (`--check`) |
| `live_api_full.json` / `.txt` | 38/38 contrôles HTTP réels sur l'application lancée (dont SSE) |
| `delivery_repo_check.json` / `.txt` | État du dépôt privé livré : `BLOQUÉ` (403 au jeton de cette session), champs non vérifiés listés |
| `omnibrain_contract_check.json` / `.txt` | Compatibilité OmniBrain : **6/6 contrôles vrais** contre les 4 fichiers sources réels relus depuis `omni-agents-framework` |
| `providers_live.json` / `.txt` | Vérification live des 5 connecteurs : 0 fournisseur vérifié en direct, 0 source simulée, erreurs explicites |
| `live_app_smoke.json` | Application réelle lancée en `uvicorn` : health, UI, login, providers, validation des 100 agents, mission réelle ⇒ `insufficient_evidence` avec 0 source |
| `live_api_full.json` / `.txt` | **38/38 contrôles HTTP réels** sur l'application lancée : auth, settings, metrics, audit, backup, refus de purge, 100 agents, fournisseurs, cycle de mission, **SSE avec événements réels lus**, rapport, contrat/modes/version/queue OmniBrain et cycle complet de soumission |

## Bugs découverts et corrigés (avant de déclarer la livraison)

9-11. Vérification HTTP live du 2026-11-04 (`scripts/verify_live_api.py`) :
- `omni_submit` renvoyait 422 quand `mode` était fourni au niveau racine :
  `str(Mode.FAST)` vaut `"Mode.FAST"` en Python 3.11 → `_mode()` extrait
  désormais `.value` et accepte un `Mode` déjà typé ;
- la garde `X-OmniBrain-Contract` n'était appliquée qu'à `POST /missions` :
  elle est maintenant une dépendance du routeur entier (GET inclus), avec
  2 tests de non-régression ;
- le résultat du bouton « Tester réellement » disparaissait au re-rendu de la
  liste des fournisseurs : le résultat est conservé dans l'état de l'UI et
  réaffiché après re-rendu (détecté par le test DOM).


1. `AgentRegistry.validate()` cherchait les handlers par nom de noyau →
   « handler manquant WEB-01 » : passage à un index par identifiant.
2. `SyntaxError: f-string unterminated string` dans `report_generator.py` →
   précalcul de `wave_text`.
3. `app/main.py` instanciait le runtime dans le lifespan → `RuntimeError` sur
   les dépendances : instanciation au `create_app()`.
4. `AgentRunner.build_context()` exigeait `claims` dans les tests isolés →
   paramètre optionnel.
5. `TestClient` sans gestionnaire de cycle de vie recréait une boucle par
   requête et **tuait** les missions en tâche de fond → `with TestClient(app)`.
6. Tests UI : le mot `innerHTML` dans un commentaire et les suffixes
   d'endpoint construits dynamiquement faisaient échouer des assertions
   statiques → commentaire reformulé et flux SSE réel ajouté
   (`missionPath('/events')`).
7. Le planificateur MAXIMUM écartait les profils de pertinence nulle → ajout
   en fin de plan pour garantir les 100 agents mobilisables.
8. Assertions sur le marqueur de données non fiables et sur le nombre de
   sources d'un test fournisseur borné → alignées sur le comportement réel.

## Ce que ces tests ne prouvent PAS

- Aucun appel live à Tavily/Brave/Exa/Firecrawl/SearXNG (pas de clé, réseau
  sortant restreint). Parsing et construction de requêtes testés ; appels
  réels ⇒ `IMPLÉMENTÉ MAIS NON VÉRIFIÉ`.
- Aucun LLM externe réel ; la synthèse extractive locale est testée.
- PostgreSQL/Redis/Qdrant/Docker non exécutés ici (binaires absents) ;
  replis locaux exécutés et testés.
- Aucun navigateur réel : l'UI est couverte par des tests statiques et par
  les tests de ses endpoints.
- L'orchestrateur OmniBrain externe n'a pas été lancé contre l'API ; en
  revanche la **conformité au contrat est vérifiée automatiquement contre les
  fichiers sources réels** et le protocole JSONL est testé.
- `scripts/verify_providers_live.py` a été exécuté : Tavily/Brave/Exa/Firecrawl
  `not_configured`, SearXNG `error` (hôte `searxng` non résolu, aucune instance
  locale). **`live_verified: []`** — aucun appel live réussi, aucun résultat
  simulé.
- Aucune simulation de résultat de recherche réel n'a été utilisée en
  production ; les doubles sont marqués `test_double=True` et font échouer la
  gate `real_provider`.
