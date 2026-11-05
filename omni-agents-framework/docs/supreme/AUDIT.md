# OMNIBRAIN SUPREME 1000 — Phase 1 : Audit réel de l'écosystème

**Date :** 2026-11-05 · **Branche de travail :** `arena/ffc77bf1-skills-collection` (base initiale `4500e93` ; `master` synchronisé ensuite à `af4b951` en 1.2.1)
**Méthode :** `gh auth status`, `gh repo list`, `gh api`, `gh pr list/view/diff`, lecture des fichiers locaux, exécution de la suite de tests existante. Aucune donnée inventée ; les accès refusés sont listés tels quels.

---

## 1. Accès et permissions vérifiés

| Vérification | Résultat réel |
| --- | --- |
| Authentification GitHub | `gh auth status` → connecté en tant que **blassana280-ux** (GH_TOKEN, jeton d'installation GitHub App) |
| Dépôts listés | **46 dépôts** accessibles via `gh repo list blassana280-ux --limit 300` (1 créé par le compte, 45 forks) |
| Push `skills-collection` | **OK** — historique : PR #1, #3, #4 fusionnées depuis des branches Arena |
| Push `omni-agents-framework` | **REFUSÉ (403)** documenté en session V4 (`docs/PROMOTION-403.md`) malgré `permissions.push=true` dans l'API. Lecture seule vérifiée ici (`git ls-remote` → `41203f7`). Aucune tentative d'écriture effectuée. |
| `optimiser-mes-agents-IA` | **403 en lecture** (documenté V4, toujours cité comme non vérifiable) |
| Création de dépôt / dépôt profil `.github` | **403** `Resource not accessible by integration` (documenté V4) |
| Clés fournisseurs IA dans l'environnement | **Aucune** : OPENAI, MISTRAL, DEEPSEEK, GEMINI/GOOGLE, OPENROUTER, ANTHROPIC, TOGETHER, GROQ, HF, OLLAMA_HOST, E2B → toutes absentes (vérifié par script, valeurs jamais affichées) |
| Réseau sortant du sandbox | Limité à `github.com`, `api.github.com`, `codeload.github.com`, `registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org`. **Les API de modèles IA ne sont pas joignables depuis ce sandbox**, même avec une clé. |
| Python / Node | Python 3.11.2, Node v22.22.3 |

**Conséquence de conception :** tout ce qui dépend d'un fournisseur IA externe est implémenté avec détection réelle de configuration et tests sur fixtures explicites, mais sera rapporté « non configuré / indisponible » tant qu'aucune clé n'est fournie. Aucune connexion simulée ne sera présentée comme réelle.

## 2. Inventaire par catégorie (A–L)

### Dépôt principal de travail : `blassana280-ux/skills-collection`
- **Origine :** fork de `alexander-kastil/skills-collection` (lui-même écosystème `sickn33/antigravity-awesome-skills`), licence **MIT**, branche `master`.
- **Contenu réel :** 855 entrées dans `skills/` (852+ skills `SKILL.md`), `skills_index.json` (860 entrées), `CATALOG.md`, `data/` (bundles, aliases, workflows), `scripts/` (validate, index, catalog, sync Microsoft), CI `ci.yml`, `publish-npm.yml`.
- **Couche OmniBrain déjà fusionnée (PR #3, #4) :** `omni-agents-framework/` complet + `AGENTS.md` overlay + `RAPPORT-PHASE1.md` + `RAPPORT-ORCHESTRATION-V4.md`.
- **PR ouverte #2 :** `OMNI-RESEARCH 100` (141 fichiers, +20 443 lignes, branche `arena/63999462-skills-collection`, non fusionnée) — projet parallèle `omni-research-100/` (100 agents, API, UI). **Non touché** ; décision de convergence à prendre par Lassana.

### `omni-agents-framework/` (vendored dans skills-collection, source de vérité opérationnelle)
Licence Apache-2.0. **105 tests verts** vérifiés localement (`python3 -m unittest discover -s tests` → `Ran 105 tests … OK`, 10,7 s).

| Cat. | Ressource | Fichiers | État réel |
| --- | --- | --- | --- |
| A. Orchestrateur | `omnibrain/` (classifier, router, dispatcher, gates, parallel, registry, report, CLI) | 12 modules | Fonctionnel, testé (routage par mots-clés, escouades 1–8, vague parallèle unique) |
| A. Graphe HITL | `omni/graph/` (state, pipeline) | 2 modules | Pipeline déterministe `spec→implementation→revue_adverse→tests→verification`, cycles rejetés, escalade humaine |
| B. Agents | `specialized/*.md` + `matrix.toml` + `catalog/catalog-100.toml` | **115 agents** (103 catalogue + 12 cœur) | Fiches Markdown + frontmatter, générés par `tools/generate_agents.py` |
| C. Profils | `tools/catalog_01..07_*.py`, `tools/agent_spec.py` | 7 modules de specs | Générateur déterministe, contrôle de doublons |
| D. Skills | `skills/` (racine du dépôt, 852+) + `skills_index.json` (860) | SKILL.md | Skills **documentaires** (instructions), pas des exécutables |
| E. Fournisseurs IA | Aucun connecteur actif dans le framework ; fork `OmniRoute` (passerelle multi-fournisseurs) et `9router` | — | **Non connecté** ; à intégrer si clés fournies |
| F. Mémoire | `omni/memory/store.py` (SQLite, 9 tables, rédaction secrets), `autofix.py` ; forks `mem0`, `cognee`, `hindsight`, `GPTCache` | 2 modules + forks | Store V4 fonctionnel et testé ; forks = ressources externes non déployées |
| G. Automatisation | `scripts/`, `bin/`, workflows GitHub Actions, `tools/finalize_actions.py` | — | CI verte (run `41952139700` documenté V4) |
| H. Sécurité défensive | `omni/sandbox/` (E2B hook + fallback local `python -I`), RBAC `runtime.py`, `docs/SECURITY_GUARDRAILS.md`, skills security | — | Sandbox local réel testé ; E2B non configuré (pas de clé) |
| I. CI/CD | `.github/workflows/omnibrain-v4.yml` (3.11/3.12/3.13), `ci.yml`, `publish-npm.yml` | — | Fonctionnel ; le workflow V4 ne couvre que l'ancienne branche Arena en push |
| J. Tests/benchmarks | `tests/` (105), `tools/benchmark.py` (10 tâches gelées), `omni/telemetry/metrics.py` | — | Verts, mesurés |
| K. Documentation | `docs/V4.md`, `README.md`, rapports de phase, `docs/` racine (guides skills) | — | Cohérente avec le code |
| L. Missions | `omni/memory/store.py` (missions, escouades, résultats, échecs), `Runtime` (file bornée) | — | Base posée, pas encore de DAG multi-tâches persistant |

### Autres forks (ressources externes, non déployées)
`OmniRoute` (passerelle 339 fournisseurs), `Open-Agents` (orchestrateur TS), `mem0`/`cognee`/`hindsight` (mémoire), `GPTCache`/`LLMLingua`/`LMCache` (cache/compression), `how-claude-code-works`, `Awesome-Context-Engineering`, `Context-Engineering`, `Prompt-Engineering-Guide` (connaissances), `opencode`, `kilocode`, `builder`, collections de skills (`agent-skills`, `skills`, `antigravity-skills`, `gemini-skills`, etc.), `minimind`, `Red-DiscordBot`, `video-use`, `vpn-decryptor`, `xquads-squads`, `agency-agents`, `awesome-*`. Tous publics, lecture possible, aucun déployé.

## 3. Matrice de réutilisation

| Ressource | Utilisation actuelle | Fonctionnalité réutilisable | Intégration prévue SUPREME | Classe |
| --- | --- | --- | --- | --- |
| `omni/memory/store.py` | Mémoire orchestration V4 | SQLite transactionnel, rédaction secrets, tables missions/résultats/échecs | Réutilisé tel quel pour l'historique V4 ; SUPREME ajoute sa propre base 4 niveaux | 1 — direct |
| `omni/sandbox/runtime.py` (RBAC) | Contrôle d'accès V4 | Rôles, actions irréversibles réservées à l'humain | Réutilisé par le Policy Engine SUPREME | 1 — direct |
| `omni/sandbox/e2b_hook.py` | Exécution isolée | Hook E2B + fallback local `python -I` | Réutilisé pour l'exécution de code non fiable | 1 — direct |
| `omni/graph/` | Pipeline HITL | Graphe déterministe, gates, escalade | Réutilisé comme brique ; SUPREME ajoute un DAG de missions multi-tâches | 2 — adapter |
| `omni/telemetry/metrics.py` | Télémétrie vagues | Métriques par agent, export JSON | Branché sur l'Observability Engine SUPREME | 2 — adapter |
| `omnibrain/` (router, classifier, gates) | Routage 115 agents | Classification, briefs, gates qualité | Conservé pour le réseau V4 ; SUPREME a son propre planificateur 1000 agents | 5 — externe |
| `tools/agent_spec.py` + générateur | 103 fiches | Génération déterministe + contrôle doublons | Patron réutilisé pour le générateur 1000 profils | 2 — adapter |
| `skills/` + `skills_index.json` | Bibliothèque de skills | 860 skills documentaires versionnés | Skill Registry SUPREME les indexe (marqués non exécutables) | 1 — direct |
| `tools/optimize_prompts.py` | Auto-amélioration GEPA | Itérations journalisées, acceptation sur gain | Patron réutilisé par le Learning Engine | 2 — adapter |
| Forks `mem0`/`cognee`/`hindsight` | Non déployés | Mémoire sémantique avancée | Option d'évolution payante/lourde ; non requis pour démarrer gratuitement | 5 — externe |
| Fork `OmniRoute` | Non déployé | Routage multi-fournisseurs TS | Alternative au routeur Python natif si besoin de 339 fournisseurs | 5 — externe |
| PR #2 `omni-research-100` | Non fusionnée | API/UI/100 agents | Convergence à décider ; pas de duplication volontaire | 5 — externe |
| `scripts/validate_skills.py` | Validation skills | Contrôles frontmatter | Réutilisé pour le Skill Registry | 1 — direct |

## 4. Lacunes détectées (priorité → correction)

| # | Lacune | Priorité | Correction SUPREME |
| --- | --- | --- | --- |
| 1 | Pas de registre structuré 1000 agents / 20 divisions | P0 | `supreme/` : 20 divisions × 50 profils complets, registre SQLite + JSON versionné |
| 2 | Pas d'orchestrateur DAG multi-tâches persistant (états, reprises, idempotence) | P0 | `supreme/orchestrator.py` + `runtime.py` (pool de workers, files, backpressure) |
| 3 | Pas de bus de communication inter-agents (ACL, DLQ, anti-usurpation) | P0 | `supreme/bus.py` |
| 4 | Mémoire sans niveaux central/individuel/division/collectif ni ACL/recherche | P0 | `supreme/memory.py` (FTS5, graphe de connaissances, provenance, versions, TTL) |
| 5 | Aucun routeur multi-modèles ni conseil | P1 | `supreme/router.py` + `council.py` (détection réelle, fallback, budget) |
| 6 | Pas de moteur de politique/risque + approbations | P0 | `supreme/policy.py` (4 niveaux, file d'approbations, règles protégées) |
| 7 | Pas d'Agent Factory avec quarantaine/tests/activation | P0 | `supreme/factory.py` |
| 8 | Pas d'API ni tableau de bord mobile | P1 | `supreme/api.py` + dashboard HTML/JS (données 100 % réelles) |
| 9 | Pas de gestion de budget/quotas par agent/division/mission | P1 | `supreme/budget.py` |
| 10 | Pas d'évaluation indépendante ni d'activation sur preuve | P0 | `supreme/evaluation.py` (7 tests par profil, activation sur exécution réelle) |
| 11 | CI ne couvre pas la nouvelle branche Arena en push | P1 | Nouveau workflow `omnibrain-supreme.yml` |
| 12 | Fournisseurs IA non configurés | P1 | Détection + documentation ; activation sur fourniture de clés (action humaine) |
| 13 | Pas de sauvegarde/restauration unifiées | P2 | `supreme/backup.py` |
| 14 | Skills documentaires ≠ compétences exécutables | P1 | Tool Registry (outils déterministes réels) + Skill Registry (savoir-faire versionné) |

## 5. Décisions d'architecture issues de l'audit

1. **Réutiliser V4** (mémoire, sandbox, RBAC, télémétrie, graphe) plutôt que réécrire. SUPREME est une couche au-dessus, dans `omni-agents-framework/supreme/`.
2. **Python 3.11+ stdlib uniquement** (cohérent V4, gratuit, CI sans dépendances, pas de surface de dépendances supplémentaire).
3. **SQLite** comme stockage transactionnel unique (registre, missions, bus, mémoire, budget, approvals) — pas de service externe requis pour démarrer.
4. **1000 profils = données versionnées** (`supreme/divisions/div01..20.py`), générés déterministement vers `supreme/catalog/agents.json` ; le runtime lit le catalogue, pas des processus permanents.
5. **Aucun fournisseur IA supposé connecté.** Le routeur détecte l'environnement réel ; les missions nécessitant un LLM sont `bloquées` avec raison explicite si aucun fournisseur n'est disponible.
6. **Activation sur preuve** : un agent ne devient OPÉRATIONNEL qu'après exécution réelle réussie de sa mission représentative (outils déterministes locaux pour le sous-ensemble activable hors ligne ; les autres attendent un fournisseur).
7. **Tout le travail sur la branche Arena de session** ; promotion vers `omni-agents-framework` autonome bloquée par 403 → documentée, jamais contournée.
