# Architecture technique — OMNI-RESEARCH 100

## 1. Vue d'ensemble

```
                ┌──────────────────────────────────────────────────────┐
                │ Interface web (HTML/CSS/JS, PWA, responsive)         │
                │  app/web/*  → fetch sécurisé vers /api/*             │
                └───────────────────────┬──────────────────────────────┘
                                        │ JWT / X-OmniBrain-Key
┌───────────────────────────────────────▼──────────────────────────────────┐
│ FastAPI  app/main.py                                                     │
│  /api/auth  /api/missions  /api/agents  /api/providers  /api/settings   │
│  /api/omnibrain/v1/*       SSE /api/missions/{id}/events                │
│  middlewares : en-têtes de sécurité, CORS, gestion d'erreurs typées     │
└───────────────┬───────────────────────────────┬──────────────────────────┘
                │                               │
      ┌─────────▼──────────┐        ┌───────────▼───────────┐
      │ ResearchPipeline   │        │ ResearchMemory        │
      │ (app/brain/*)      │        │ PostgreSQL (vérité)   │
      └─────────┬──────────┘        │ Redis (tâches)        │
                │                   │ Qdrant (optionnel)    │
                │                   │ replis locaux réels   │
                │                   └───────────────────────┘
   ┌────────────┼───────────────────────────────────────────────┐
   │            │                                               │
   ▼            ▼                                               ▼
ProviderRouter  AgentRegistry + AgentRunner                 ReportGenerator
(5 connecteurs) (100 handlers / 31 noyaux)                 (6 gates + verdict)
   │                    │                                       │
   ▼                    ▼                                       ▼
SearXNG/Tavily/Brave/Exa/Firecrawl                    markdown + JSON + citations
```

## 2. Modules du cerveau (`app/brain/`)

| Module | Rôle réel |
|---|---|
| `planner.py` | Décompose la question, classe la catégorie, sélectionne les agents par pertinence déterministe, garantit la couverture des 10 divisions en MAXIMUM |
| `commander.py` | Machine à états (`queued → planning → searching → extracting → analyzing → verifying → synthesizing → reporting → completed / insufficient_evidence / failed / cancelled`), progression, annulation, limite globale de missions |
| `scheduler.py` | Vagues par division, dépendances, priorités, reprises, file d'attente morte |
| `executor.py` | `asyncio.Semaphore`, `asyncio.gather`, `asyncio.to_thread`, pic de concurrence **mesuré**, reprises, persistances des tâches et événements |
| `evidence_collector.py` | Normalisation, URL canonique, empreintes SHA-256, citations `[S#]`, rejets SSRF, statistiques d'indépendance |
| `claim_verifier.py` | Regroupement des énoncés, corroboration par domaines indépendants, passes renforcées (conflits numériques, signaux de contradiction) |
| `consensus.py` | Accord pondéré : confiance, nombre d'agents, diversité des domaines et des fournisseurs |
| `conflict_resolver.py` | Arbitrage OmniBrain : `preuves > exécution réelle > critères > id` ; égalité ⇒ `unresolved` |
| `synthesizer.py` | Réponse argumentée avec citations validées ; données web encapsulées dans `<<<UNTRUSTED_WEB_DATA>>>` |
| `report_generator.py` | Rapport markdown + JSON, table des preuves, 6 gates, verdict `READY`/`NEEDS_WORK` |
| `modes.py` | Paramètres FAST/DEEP/MAXIMUM et calcul honnête des ressources |
| `pipeline.py` | Orchestration complète, traçabilité, gestion d'annulation et d'erreurs |

## 3. Moteur Internet (`app/providers/`)

- `base.py` : contrat `BaseProvider`, `SearchQuery`, `SourceRecord`,
  `ExtractedPage`, canonicalisation d'URL, empreintes, `QuotaManager`,
  `CircuitBreaker`, états et erreurs typées.
- `searxng.py`, `tavily.py`, `brave.py`, `exa.py`, `firecrawl.py` : **vrais
  appels HTTP** (GET/POST, en-têtes d'authentification, parsing des réponses
  documentées). Aucune clé ⇒ `not_configured` et zéro source.
- `extractor.py` : parser HTML stdlib (`HTMLParser`), suppression des
  scripts/styles/formulaires, extraction titre/date/texte, neutralisation des
  injections.
- `router.py` : classement de la requête par catégorie, ordre de priorité par
  fournisseur, **recherche parallèle** (`gather`), **bascule automatique** en
  série si le parallèle échoue, quotas journaliers persistés, disjoncteur,
  déduplication (URL canonique), vérification HTTP des sources, conservation
  des preuves, extraction parallèle bornée.
- `registry.py` : registre extensible — `register()` ou
  `OMNI_PROVIDER_PLUGINS=package.module:Classe`.
- `models.py` : abstraction des modèles — `extractive` (locale, par défaut),
  `openai_compatible`, `anthropic`, `ollama`, avec repli explicite et
  `used_llm` rapporté.

## 4. Agents (`app/agents/`)

- `catalog_data.py` : 100 `AgentSpec` (id, division, mission, compétences,
  outils autorisés, configuration, noyau, focus, motif, seuils, schémas).
- `profiles.py` : **100 handlers Python distincts** (2633 lignes générées).
- `kernels.py` : 31 noyaux d'analyse réels (phrases, regex, nombres + unités,
  dates, chronologie, entropie de domaines, similarité/Jaccard, clusters,
  hedging, négations, contradictions, citations textuelles, n-grammes,
  entités, fraîcheur, provenance, lacunes, co-occurrences, conflits numériques,
  stance, longueur, affirmations, graphe de citations, valeurs aberrantes,
  langue, paires clé/valeur, licences, versions, crédibilité, types de source,
  corrélation).
- `registry.py` : validation (100/10×10), sélection par pertinence, export au
  format `registry/agents.json` d'OmniBrain, alignement des actions dangereuses.
- `runner.py` : validation d'entrée, liste blanche d'outils (`ToolFacade`),
  exécution en thread, enrichissement optionnel par un modèle configuré,
  sortie structurée et horodatée.

Génération reproductible : `python scripts/gen_profiles.py` (ou `--check` en CI).

## 5. Mémoire (`app/core/db.py`, `memory.py`)

Source de vérité SQLAlchemy : `missions`, `tasks`, `sources`, `evidence`,
`claims`, `contradictions`, `reports`, `audit_logs`, `error_logs`, `metrics`,
`provider_usage`, `research_cache`, `events`, `settings`, `users`.

- PostgreSQL en production (`postgresql+psycopg://…`), SQLite en
  développement/tests. Même code d'accès (`Store`).
- Redis : `RedisQueue` (optionnel) ; repli réel `InProcessQueue`.
- Qdrant : `QdrantVectorIndex` HTTP (optionnel) ; repli réel
  `LocalVectorIndex` (cosinus 64 dimensions, vectorisation déterministe).
- Réutilisation : exacte par empreinte de requête + sémantique par similarité.
- Rétention : purge explicite, confirmée et auditée (voir `RETENTION.md`).
- Sauvegarde : `POST /api/backup` (SQLite), `deploy/backup_postgres.sh`
  (`pg_dump`), `deploy/restore_postgres.sh` (reprise après incident).

## 6. Sécurité

Voir `SECURITY.md`. Points structurants : JWT signé + clé API OmniBrain, RBAC
4 rôles, rate limiting, validation Pydantic stricte, garde SSRF (syntaxe +
DNS avant tout fetch), neutralisation des injections de prompts, contenu web
toujours `untrusted`, aucun `innerHTML` dans l'UI, CSP stricte, rédaction des
secrets dans les journaux et livrables, refus des actions irréversibles.

## 7. Gates et verdict (alignement OmniBrain)

`completeness`, `evidence`, `execution`, `arbitration`, `secrets`, `trace` +
`real_provider` (spécifique à cette plateforme). `READY` exige **toutes** les
gates ; avec un double de test hors ligne, `real_provider=false` ⇒
`NEEDS_WORK`. Règle héritée d'OmniBrain : « READY sans provider réel doit
rester impossible ».

## 8. Concurrence honnête

`MAXIMUM` planifie 100 agents. `ParallelExecutor` n'en exécute jamais plus de
`OMNI_MAX_PARALLEL_AGENTS` à la fois. Le pic est mesuré par un compteur sous
verrou et publié (`peak_concurrency_measured`) avec le nombre d'agents mis en
file (`queued_agents`). Les vagues sont persistées avec leur durée réelle.
