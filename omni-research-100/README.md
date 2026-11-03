# OMNI-RESEARCH 100

> Plateforme de recherche multi-agents réellement exécutable : **100 profils
> spécialisés**, **10 divisions**, **3 modes**, **5 connecteurs Internet**,
> un cerveau de recherche en 11 modules, une mémoire persistante, un adaptateur
> **OmniBrain v1** versionné, une API sécurisée et une interface web responsive
> (Android / ordinateur, PWA).

**Règle de vérité** : ce projet ne simule jamais un résultat de recherche. Un
fournisseur non configuré ou en panne produit **zéro source** et une erreur
explicite. Un rapport ne peut pas recevoir le verdict `READY` sans qu'un
fournisseur **réel** ait répondu. Les contenus du Web sont traités comme des
données non fiables (neutralisation des injections, aucune exécution de code).

---

## 1. État de la livraison (lecture honnête)

| Élément | État |
|---|---|
| Code complet (backend, 100 agents, moteur Internet, cerveau, mémoire, API, UI) | **OPÉRATIONNEL ET TESTÉ** |
| 100 handlers exécutés individuellement avec sorties distinctes | **OPÉRATIONNEL ET TESTÉ** (71 tests Python + 5 tests Node) |
| Pipeline FAST / DEEP / MAXIMUM de bout en bout | **OPÉRATIONNEL ET TESTÉ** (avec double de test hors ligne déclaré) |
| Adaptateur OmniBrain v1 (contrat réel inspecté + file JSONL) | **OPÉRATIONNEL ET TESTÉ** |
| Parseurs des 5 connecteurs (SearXNG, Tavily, Brave, Exa, Firecrawl) | **IMPLÉMENTÉS, PARSING TESTÉ** avec transport HTTP simulé ; `scripts/verify_providers_live.py` permet la vérification live dès qu'une clé/service existe |
| Compatibilité OmniBrain au contrat réel | **OPÉRATIONNELLE ET TESTÉE** : `scripts/verify_omnibrain_contract.py` relit les 4 fichiers sources et valide 6/6 contrôles |
| Appels **réels** aux 5 API externes | **IMPLÉMENTÉS MAIS NON VÉRIFIÉS** : `live_verified: []` (`test-results/providers_live.json`), aucune clé API présente et réseau sortant du sandbox limité |
| PostgreSQL / Redis / Qdrant | **ADAPTATEURS IMPLÉMENTÉS, NON EXÉCUTÉS ici** (binaires absents) ; SQLite / file en mémoire / index cosinus local **exécutés et testés** |
| Fournisseurs de modèles (OpenAI-compatible, Anthropic, Ollama) | **IMPLÉMENTÉS MAIS NON VÉRIFIÉS** (sans clé) ; synthèse extractive déterministe **exécutée et testée** |
| Interface dans un vrai navigateur | **PARTIELLE** : tests statiques Node + tests de ses endpoints ; aucun navigateur dans le sandbox |
| Dépôt privé `blassana280-ux/omni-research-100` | **BLOQUÉ** : `gh repo create` → `GraphQL: Resource not accessible by integration (createRepository)`. Voir [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) |
| Protection de branche `main` | **BLOQUÉE** (403 + modification de permissions globales soumise à autorisation) |
| CI GitHub Actions (PR #2, run 41727343863) | **VERTE** : 71 tests Python, 5 tests Node, 100 profils, `pip-audit`, vérification hors ligne |
| Application réelle en aperçu local | **OPÉRATIONNELLE** : `uvicorn` sur `0.0.0.0:8000`, health/UI/login/agents/providers/mission vérifiés via HTTP (`test-results/live_app_smoke.json`) |
| Fusion de Pull Request | **NON EFFECTUÉE** (autorisation explicite requise) |

Le code livré se trouve dans **`blassana280-ux/skills-collection`**, branche
`arena/63999462-skills-collection`, dossier `omni-research-100/`. C'est une
architecture **indépendante d'OmniBrain** : aucun dépôt OmniBrain n'a été
modifié.

---

## 2. Démarrage rapide (3 commandes)

```bash
cd omni-research-100
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Ouvrir `http://localhost:8000` (interface) ou `http://localhost:8000/docs`
(OpenAPI). Comptes par défaut : `admin` / `change-me-admin`,
`researcher` / `change-me-user` — **à changer via `.env`**.

Aucune clé API n'est obligatoire. Sans fournisseur joignable, une mission se
termine en `insufficient_evidence` avec un rapport explicitant l'absence de
sources ; aucun résultat n'est inventé.

```bash
# Vérification complète hors ligne, sans réseau
.venv/bin/python scripts/verify_offline.py
# Tests
.venv/bin/python -m pytest -q
node --test tests/test_web_ui.test.js
```

---

## 3. Architecture en une phrase

`Question → Mission Planner → Research Commander → Provider Router (recherche
parallèle + bascule) → Evidence Collector → Task Scheduler → Parallel Executor
(100 agents bornés) → Claim Verifier → Consensus Engine → Conflict Resolver →
Research Synthesizer → Report Generator (6 gates) → API / UI / OmniBrain`.

Voir [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## 4. Les 100 agents

10 divisions × 10 profils : Web Intelligence, Deep Research, News Intelligence,
Scientific Research, Technology Intelligence, Open Source Intelligence, Social
Intelligence, Fact Verification, Data Intelligence, Research Synthesis.

Chaque agent possède : un **handler Python distinct** (100 fonctions générées
de façon reproductible depuis `scripts/gen_profiles.py`), **31 noyaux
d'analyse déterministes** (`app/agents/kernels.py`), des compétences, des outils
autorisés avec liste blanche, une configuration (seuils, poids, motif, nombre
maximal de résultats, reprises), un schéma d'entrée `INPUT_SCHEMA`, un schéma
de sortie `OUTPUT_SCHEMA` et une trace d'exécution horodatée.

La liste complète avec l'état individuel est dans
[`docs/AGENTS_CATALOG.md`](docs/AGENTS_CATALOG.md) — les 100 sont
**OPÉRATIONNELS ET TESTÉS** (`tests/test_agents_all_100.py` produit
`test-results/agent_results.json`, 100 empreintes de sortie distinctes).

## 5. Les trois modes

| Mode | Agents planifiés | Fournisseurs | Sources | Extractions | Vérification | Contradictions |
|---|---|---|---|---|---|---|
| FAST | 3 | 1 | 8 | 0 | 1 passe | non |
| DEEP | 16 | 3 | 24 | 6 | 2 passes | oui |
| MAXIMUM | **100** (les 10 divisions) | 5 | 60 | 12 | 3 passes | oui + arbitrage approfondi |

`MAXIMUM` **mobilise** les 100 agents mais ne prétend jamais qu'ils tournent
simultanément : le `ParallelExecutor` applique un sémaphore
`OMNI_MAX_PARALLEL_AGENTS` (défaut 8), répartit le travail en vagues et
**mesure** le pic de concurrence réel, publié dans le rapport. Les agents non
simultanés sont mis en file ; `mode_summary()` expose
`queued_not_simultaneous`.

## 6. Documentation

| Document | Contenu |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Architecture technique, flux de données, schémas, tables |
| [`docs/INSTALL.md`](docs/INSTALL.md) | Installation serveur et poste de travail |
| [`docs/ANDROID_DESKTOP.md`](docs/ANDROID_DESKTOP.md) | Guide Android / ordinateur, PWA, accès LAN |
| [`docs/API_KEYS.md`](docs/API_KEYS.md) | Configuration des 5 fournisseurs + modèles, sans abonnement obligatoire |
| [`docs/API.md`](docs/API.md) | Documentation API complète (auth, endpoints, SSE, codes d'erreur) |
| [`docs/OMNIBRAIN.md`](docs/OMNIBRAIN.md) | Contrat réel inspecté, adaptateur v1, file JSONL, compatibilité |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Docker, PostgreSQL/Redis/Qdrant, sauvegardes, reprise |
| [`docs/RETENTION.md`](docs/RETENTION.md) | Politique de rétention et suppression |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Sécurité, anti-injection, SSRF, RBAC, quotas |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | Dépannage |
| [`docs/TEST_RESULTS.md`](docs/TEST_RESULTS.md) | Résultats de tests réellement exécutés |
| [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) | État précis, éléments bloqués, procédure de reprise |
| [`docs/FINAL_DELIVERY.md`](docs/FINAL_DELIVERY.md) | Classification exhaustive de chaque fonctionnalité, URLs, résultats et blocage |
| [`docs/AGENTS_CATALOG.md`](docs/AGENTS_CATALOG.md) | Les 100 agents, état individuel |
| [`.env.example`](.env.example) | Toutes les variables, commentées |

## 7. Ce qui n'a PAS été fait (et pourquoi)

- **Créer le dépôt privé dédié** : le jeton GitHub connecté n'a pas le scope
  `Administration / repo creation` (`createRepository` → 403). Création
  manuelle ou reconnexion GitHub nécessaire. Le travail n'est pas perdu : il
  est versionné sur la branche de session et prêt à être poussé/mirorré.
- **Protéger `main`** : 403 sur l'API de protection + opération classée
  « modification de permissions globales », soumise à autorisation explicite.
- **Fusionner une PR** : interdit sans accord explicite.
- **Appels live aux API de recherche** : aucune clé présente, réseau sortant
  restreint. Les connecteurs sont prêts et documentés ; les tests valident la
  construction des requêtes et le parsing, pas la facturation réelle.
- **Déployer sur une infrastructure payante** : non fait.
- **Exécuter un vrai navigateur** : absent du sandbox ; l'UI est testée
  statiquement et via tous ses endpoints.

---

## 8. Licence et origine

MIT. Le contrat OmniBrain a été lu dans le dépôt public
`blassana280-ux/omni-agents-framework` (`OMNIBRAIN.md`, `AGENTS.md`,
`registry/permissions.json`, `cf100/bridges/omnibrain.py`,
`cf100/bridges/omni_queue.py`, `docs/OMNIBRAIN-INTEGRATION.md`) et dans
`blassana280-ux/skills-collection:AGENTS.md`. Aucun dépôt OmniBrain n'a été
modifié.
