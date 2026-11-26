# Configuration des API — aucun abonnement payant obligatoire

**Principe** : une clé absente n'empêche pas le démarrage. Le connecteur est
préparé, déclaré `not_configured` dans `GET /api/providers`, documenté ici, et
les autres fournisseurs disponibles restent actifs. **Aucun résultat de
recherche n'est simulé** : sans fournisseur joignable, la mission retourne
`insufficient_evidence` avec un rapport l'expliquant.

Toutes les variables sont dans `.env.example`. Copier vers `.env`, qui est
exclu de Git.

## 1. SearXNG — gratuit, auto-hébergé, sans clé (recommandé)

```bash
OMNI_SEARXNG_ENABLED=true
OMNI_SEARXNG_URL=http://searxng:8080     # ou http://localhost:8080 en local
OMNI_QUOTA_SEARXNG=0                      # 0 = illimité
```

Le `docker-compose.yml` fournit une instance SearXNG avec
`deploy/searxng-settings.yml` (format `json` activé). Sans Docker :

```bash
docker run -d --name searxng -p 8080:8080 \
  -v "$PWD/deploy/searxng-settings.yml:/etc/searxng/settings.yml" \
  searxng/searxng:latest
```

Endpoint appelé : `GET {URL}/search?q=…&format=json&language=…`.
Vérification : `GET /healthz`.

## 2. Tavily

```bash
OMNI_TAVILY_API_KEY=tvly-...
OMNI_TAVILY_BASE_URL=https://api.tavily.com
OMNI_QUOTA_TAVILY=100
```

Endpoint : `POST /search` (`api_key`, `query`, `search_depth`, `max_results`).
Réponses parsées : `results[].{title,url,content,score,published_date}`.

## 3. Brave Search

```bash
OMNI_BRAVE_API_KEY=...
OMNI_BRAVE_BASE_URL=https://api.search.brave.com
OMNI_QUOTA_BRAVE=100
```

Endpoint : `GET /res/v1/web/search` avec `X-Subscription-Token`.
Réponses parsées : `web.results[].{title,url,description,page_age}`.

## 4. Exa

```bash
OMNI_EXA_API_KEY=...
OMNI_EXA_BASE_URL=https://api.exa.ai
OMNI_QUOTA_EXA=100
```

Endpoint : `POST /search` avec `x-api-key`, `contents.text`.
Réponses parsées : `results[].{title,url,text,score,publishedDate}`.

## 5. Firecrawl (recherche + extraction)

```bash
OMNI_FIRECRAWL_API_KEY=fc-...
OMNI_FIRECRAWL_BASE_URL=https://api.firecrawl.dev/v1
OMNI_QUOTA_FIRECRAWL=100
```

Endpoints : `POST /search` (résultats) et `POST /scrape` (Markdown d'une page).
Sans Firecrawl, l'extraction utilise `DirectExtraction` (HTTP + parser HTML
stdlib), avec les mêmes gardes SSRF et anti-injection.

## 6. Fournisseurs de modèles (tous optionnels)

La synthèse fonctionne **sans aucun modèle** : `OMNI_LLM_PROVIDER=extractive`
effectue une composition déterministe des affirmations vérifiées et le rapport
indique explicitement `used_llm=false`.

| Valeur | Variables | Appel |
|---|---|---|
| `extractive` | aucune | calcul local |
| `openai_compatible` | `OMNI_OPENAI_API_KEY`, `OMNI_OPENAI_BASE_URL`, `OMNI_OPENAI_MODEL` | `POST /chat/completions` |
| `anthropic` | `OMNI_ANTHROPIC_API_KEY`, `OMNI_ANTHROPIC_BASE_URL`, `OMNI_ANTHROPIC_MODEL` | `POST /v1/messages` |
| `ollama` | `OMNI_OLLAMA_BASE_URL`, `OMNI_OLLAMA_MODEL` | `POST /api/generate` |

Tout échec d'un fournisseur configuré entraîne un **repli explicite** vers la
synthèse extractive, tracé dans `synthesis.model_fallback` et dans les limites
du rapport. Les données web sont envoyées dans un bloc
`<<<UNTRUSTED_WEB_DATA>>>` ; aucune instruction d'une page n'est suivie.

## 7. Quotas, bascule et tests

- `OMNI_QUOTA_*` : nombre d'appels de recherche par 24 h, persisté dans la
  table `provider_usage`. `0` = illimité. Dépassement ⇒ `quota_exceeded` et
  bascule vers un autre fournisseur.
- `OMNI_PROVIDER_FAILURE_COOLDOWN_SECONDS` : disjoncteur après 3 échecs.
- `GET /api/providers` : état réel (configuré, désactivé, cooldown, dégradé),
  compteurs, dernière erreur, quotas.
- `POST /api/providers/{name}/test` : **appel réel** borné à 3 résultats.
  Sans clé : `{"status":"not_configured","sources":[]}`.
- `PATCH /api/providers/{name}?enabled=false` : désactive un fournisseur.
- Ajouter un fournisseur : implémenter `BaseProvider` puis
  `registry.register(...)` ou `OMNI_PROVIDER_PLUGINS=mon.module:MaClasse`.

## 8. Limite de ce contexte d'exécution

Pour vérifier réellement les 5 connecteurs sur une machine connectée :
`python scripts/verify_providers_live.py "ma requête"`. Le rapport
`test-results/providers_live.json` indique `live_verified` ; un connecteur non
configuré reste à **0 source** et aucune donnée d'exemple n'est injectée.

Le sandbox de construction n'avait **aucune clé API** et un réseau sortant
limité à `github.com`, `api.github.com`, `codeload.github.com`,
`registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org`. Les appels réels
n'ont donc pas pu être vérifiés ici : les connecteurs sont implémentés, leur
construction de requête et leur parsing sont **testés** avec
`httpx.MockTransport`, et le statut honnête est
« IMPLÉMENTÉ MAIS NON VÉRIFIÉ (appel live) ».
