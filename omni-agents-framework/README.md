# 🧠 OmniBrain Agent Framework

> Réseau d'agents IA spécialisés, orchestrés en parallèle par un routeur déterministe.
> **Zéro dépendance runtime** — Python 3.11+ standard library, exécutable partout.

OmniBrain est l'orchestrateur central du compte `blassana280-ux`. Il transforme
une demande utilisateur en une escouade d'agents spécialisés, mobilisés en
**une seule vague parallèle**, avec des briefs autonomes, des contrats
d'interface et des gates qualité. L'utilisateur final ne voit qu'un seul
interlocuteur et un seul livrable.

## Pourquoi ce framework

Le manifeste `AGENTS.md` décrivait un réseau dont les fiches agents vivaient
dans un dépôt inaccessible. Ce dépôt rend le réseau **réel, exécutable et
testable** :

| Avant | Après |
|---|---|
| Un fichier `AGENTS.md` pointeur vers des chemins indisponibles | **115 fiches agents** (12 cœur + 103 catalogue) en 10 escouades, validées en CI |
| Routage implicite, non reproductible | Matrice déclarative `matrix.toml` + catalogue TOML généré, moteur déterministe |
| Parallélisation prescrite, jamais outillée | `omnibrain plan` génère briefs et contrats en une vague |
| « NEEDS WORK » par défaut, sans contrôle | `omnibrain gates` évalue les 4 gates avec code de retour CI |

## Démarrage rapide

```bash
# Aucune dépendance à installer (Python 3.11+)
python3 -m omnibrain validate                       # valide tout le réseau (115 agents)
python3 -m omnibrain squads                         # bilan par escouade
python3 -m omnibrain list --squad security --terse  # filtrer une escouade
python3 -m omnibrain classify "refonte complète de l'API et des tests"
python3 -m omnibrain route "audit sécurité OWASP de l'API"
python3 -m omnibrain plan examples/task-complex.md -o plan.md
python3 -m omnibrain gates livrable.md

# Depuis n'importe quel répertoire, sans installation :
./bin/omnibrain validate
```

Installation optionnelle en commande globale : `pip install -e .` (fournit la commande `omnibrain`).
Pour localiser le dépôt hors de son arborescence : variable `OMNIBRAIN_HOME`.

## Exécution parallèle de plusieurs demandes

`omnibrain/parallel.py` lance plusieurs plans dans des **processus indépendants**
(`ProcessPoolExecutor`), chacun produisant sa vague de briefs sans séquençage :

```bash
python3 scripts/demo-parallele.py                # workers = nombre de CPU
python3 scripts/demo-parallele.py --workers 5    # un processus par demande
```

Résultat mesuré sur les 5 demandes d'`examples/` avec le réseau complet :
**35 briefs émis en wave 0, 19 agents mobilisés par les exemples, les 93
autres vérifiés routables sur leurs mots-clés, x1.83 d'accélération** sur
2 CPU. La démo affiche le temps parallèle vs séquentiel et l'accélération.
Note honnête : le routage est microsécond, donc sur des micro-tâches le
spawn de processus peut coûter plus cher que le gain quand on force trop de
workers ; l'auto-calibration par défaut reste devant, et le gain devient
décisif quand les agents exécutent de vrais travaux (outils, E/S, génération).

## Les 5 temps d'OmniBrain

1. **CLASSER** — `simple` (1 agent), `moyenne` (1-3), `complexe` (escouade 4-8).
   Score explicable : domaines matchés, connecteurs multi-tâches, lexique de
   complexité, taille, domaines à risque.
2. **MOBILISER** — la matrice `matrix.toml` sélectionne les agents par
   mots-clés FR/EN avec détection aux frontières de mot (un acronyme comme
   `ci` ne se déclenche plus dans `associés`).
3. **DISPATCHER** — une **seule vague parallèle** : brief autonome par agent,
   contexte isolé, contrats d'interface émis seulement si producteur et
   consommateur sont tous deux dans l'escouade.
4. **SURVEILLER** — 4 gates : G1 complétude, G2 preuve fraîche, G3 revue
   adverse, G4 intégration. Verdict par défaut : **NEEDS WORK**.
5. **ASSEMBLER** — un livrable unique + rapport d'orchestration
   (`templates/orchestration-report.md`).

### Renforts obligatoires

- Tout domaine code (UI, backend, data) en niveau moyenne/complexe → `qa-test`
- Demande complexe → `adversarial-reviewer` (sinon alerte bloquante)
- Domaines à risque → expert dédié imposé : `security`, `devops-sre`, `ohada-finance`
- L'orchestrateur `omnibrain` ne rejoint jamais une escouade

## Structure du dépôt

```
├── matrix.toml                  # 12 agents cœur + classification + contrats
├── catalog/catalog-100.toml     # 103 agents catalogue (GÉNÉRÉ, ne pas éditer)
├── tools/                       # sources du catalogue : catalog_*.py + generate_agents.py
├── omnibrain/                   # moteur (classifier, router, dispatcher, gates, parallel, cli)
├── specialized/                 # 115 fiches agents au format frontmatter Markdown
├── skills/omnibrain-orchestration/SKILL.md   # skill compatible spécification Agent Skills
├── templates/                   # briefs, contrats d'interface, rapport type
├── examples/                    # demandes simple / moyenne / complexe
└── tests/                       # suite unittest stdlib (python -m unittest)
```

## Les 115 agents en 10 escouades

Les **12 agents cœur** (`matrix.toml`) :

| Agent | Domaine | Risque |
|---|---|---|
| 🧠 `omnibrain` | orchestration | — |
| 🎨 `frontend-ui` | UI, frontend | |
| ⚙️ `backend-api` | backend, API | |
| 📊 `data-ai` | données, IA/ML/RAG | |
| 🧪 `qa-test` | tests, recette | |
| 🚀 `devops-sre` | CI/CD, SRE, cloud | **risque** |
| 🛡️ `security` | OWASP, IAM, RGPD | **risque** |
| 🔍 `adversarial-reviewer` | contre-expertise (gate G3) | |
| ⚖️ `ohada-finance` | SYSCOHADA/AUDCIF, fiscalité UEMOA | **risque** |
| 📣 `marketing-growth` | croissance, marque, funnel | |
| 🔎 `research-intel` | veille, sources, preuve fraîche | |
| 🧭 `product-delivery` | cadrage, roadmap, backlog | |

Les **103 agents catalogue** (`tools/catalog_*.py`, générés dans `specialized/`) :

| Escouade | Effectif | Exemples |
|---|---:|---|
| Ingénierie logicielle | 16 | iOS, Android, cross-platform, USSD/SMS, microservices, GraphQL, DBA, Rust, Go, Python, Java, PHP, .NET, legacy, intégrations |
| Data & IA | 12 | ML, MLOps, NLP, vision, recommandation, séries temporelles, RAG, LLM Ops, prompts, bases vectorielles, BI, dataviz |
| Cloud & Infrastructure | 10 | AWS, GCP, Azure, Kubernetes, Terraform, réseau, observabilité, commandement d'incident, FinOps, plateforme interne |
| Sécurité (tous à risque) | 11 | pentest, AppSec, sécurité cloud, DevSecOps, threat intel, DFIR, IAM, cryptographie, GRC, analyse malware, bug bounty |
| QA & Tests | 5 | automatisation, performance, sécurité, accessibilité, mobile |
| Design & UX | 8 | recherche UX, product design, design system, UX writing, motion, identité, illustration, accessibilité |
| Produit & Gestion | 9 | business analyst, PM, Scrum, programme, analytique produit, pricing, success client, sales enablement, conduite du changement |
| Marketing & Croissance | 10 | SEO, contenu, social, e-mail, paid ads, communauté, influence, stratégie de marque, growth, RP |
| Finance & Juridique | 12 | comptabilité, fiscalité, audit, paie, contrôle, FP&A, trésorerie, sociétés, contrats, PI, données personnelles, achats |
| Secteurs ouest-africains | 7 | mobile money/fintech, conformité remise, agritech, solaire, health tech, localisation bambara, edtech |

## Ajouter un agent

**Agent cœur** (règles de routage centrales) :

1. Créer `specialized/specialized-<id>-agent.md` avec le frontmatter
   (`id`, `name`, `description` obligatoires) en suivant une fiche existante.
2. Déclarer l'agent dans `matrix.toml` (`[[agents]]`) avec ses mots-clés et artefacts.
3. Ajouter les `[[contracts]]` éventuels.

**Agent catalogue** (la voie normale pour les 100+) :

1. Ajouter une `AgentSpec` dans le module `tools/catalog_*.py` de son escouade.
2. Régénérer : `python3 tools/generate_agents.py` (fiche Markdown + `catalog/catalog-100.toml`).
3. La CI vérifie que les artefacts générés sont bien à jour (`--check` implicite via `git diff`).

Dans les deux cas : lancer `python3 -m omnibrain validate` et la suite de tests.

## Compatible Agent Skills

`skills/omnibrain-orchestration/SKILL.md` respecte la spécification Agent
Skills (frontmatter `name`/`description`, divulgation progressive) : le même
workflow est chargeable dans tout client compatible (Claude Code, Codex,
Cursor, Gemini CLI, etc.).

## Écosystème du compte

OmniBrain réutilise sans réinventer : pour une compétence absente, chercher
d'abord dans les collections forkées `agent-skills-index`,
`awesome-agent-skills`, `antigravity-skills`, puis étendre la matrice.
La carte complète des 40 forks du compte et leur cas d'usage :
[`docs/reseau-depots.md`](docs/reseau-depots.md).

## Tests et CI

```bash
python3 -m unittest discover -s tests -v   # validation, routage, parallélisme, catalogue
python3 tools/generate_agents.py --check   # intégrité des 103 spécifications
```

L'action `.github/workflows/validate.yml` exécute sur chaque poussée et pull
request : validation du réseau, cohérence des artefacts générés, tests sur
Python 3.11/3.12/3.13, et la démo d'exécution parallèle.

## Licence

MIT — voir [LICENSE](LICENSE).

---

## OmniBrain v4 — mémoire, graphe, sandbox, observabilité

Le réseau passe de **112 → 115 agents** (12 cœur + 103 catalogue, 10 escouades)
sans régression : les **50 tests v3** restent verts, **55 tests v4** s'ajoutent
(**105 tests au total**).

| Phase | Module | Commande de preuve |
| --- | --- | --- |
| 2.1 | `omni/memory/store.py` (SQLite : missions, escouades, résultats, échecs, recettes) | `python3 -m unittest tests.test_v4_memory -v` |
| 2.2 | `omni/memory/autofix.py` (2 échecs → branche `omnibrain/fix-<agent>` + PR) | `python3 -m unittest tests.test_v4_autofix -v` |
| 2.3 | `tools/optimize_prompts.py` (réflexion GEPA, journal par itération) | `python3 tools/optimize_prompts.py --iterations 3` |
| 3.1 | `omni/graph/` (spec → impl → revue adverse → tests → vérification, gates Lassana) | `python3 -m unittest tests.test_v4_graph -v` |
| 3.2 | `omni/sandbox/e2b_hook.py` (`runCode` E2B, fallback local tracé) | `python3 -m unittest tests.test_v4_sandbox -v` |
| 3.3 | `omni/sandbox/runtime.py` (scheduler borné, RBAC, logs persistants) | `python3 -m omni.sandbox --max-ticks 1` |
| 4.1 | `omni/telemetry/` (durées, tokens, taux d'échec → JSON + markdown) | `python3 -m unittest tests.test_v4_telemetry -v` |
| 4.2 | `tools/benchmark.py` (10 tâches figées, gains historisés) | `python3 tools/benchmark.py --no-write` |
| 4.3 | `tools/catalog_*.py` (3 agents : télémétrie, mémoire, gate humaine) | `python3 tools/generate_agents.py --check` |

```bash
python3 -m omnibrain validate                 # OK — 115 agents et 7 contrats validés
python3 -m unittest discover -s tests -v     # Ran 105 tests ... OK
python3 tools/benchmark.py --no-write        # hit_rate 1.0 sur 10 tâches figées
```

Documentation complète : `docs/V4.md`, `docs/PROMOTION-403.md`,
`docs/PROFILE-REPO-AGENTS.md`. Aucune dépendance externe (stdlib 3.11+),
aucun secret dans le dépôt, **aucune fusion automatique**.
