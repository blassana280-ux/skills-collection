# Dépannage

## `ModuleNotFoundError: fastapi` / `jwt` / `yaml`

Recréer l'environnement : `python3 -m venv .venv && .venv/bin/pip install -r
requirements.txt`. Sur Debian/Ubuntu, `pip3 install --user` peut être bloqué
par PEP 668 : utiliser le venv.

## La mission se termine en `insufficient_evidence`

C'est le comportement **normal** quand aucun fournisseur n'est joignable.
Vérifier `GET /api/providers` :

- `not_configured` → renseigner la clé dans `.env` (voir `API_KEYS.md`) ;
- `degraded` / `cooldown` → disjoncteur : attendre
  `OMNI_PROVIDER_FAILURE_COOLDOWN_SECONDS` ou corriger la clé ;
- `quota_exceeded` → augmenter `OMNI_QUOTA_*` ou attendre la fenêtre 24 h ;
- tous `disabled` → `PATCH /api/providers/{name}?enabled=true`.

Pour SearXNG : `curl "$OMNI_SEARXNG_URL/healthz"` puis
`curl "$OMNI_SEARXNG_URL/search?q=test&format=json"` — le format JSON doit
être activé (`deploy/searxng-settings.yml`).

## Le verdict est `NEEDS_WORK` malgré un rapport complet

C'est volontaire : la gate `real_provider` exige des sources issues d'un
fournisseur réel. Les doubles de test hors ligne (`test_double=True`) et les
données d'exemple ne peuvent jamais produire `READY`. Consulter
`report.gates` pour la gate manquante.

## `/docs` renvoie 401 ou l'UI affiche « non connecté »

Le token a expiré (`OMNI_TOKEN_TTL_SECONDS`). Se reconnecter. Vérifier que
`OMNI_AUTH_SECRET` est identique entre deux redémarrages, sinon tous les
jetons existants sont invalidés.

## SSE : aucun événement dans le navigateur

- Le reverse proxy doit désactiver `proxy_buffering` et allonger
  `proxy_read_timeout` (voir `DEPLOYMENT.md`).
- L'UI utilise `fetch` + `ReadableStream` (EventSource ne peut pas envoyer
  l'en-tête `Authorization`). En cas d'échec, elle **replie sur un polling
  réel** de 1,5 s ; le pied de page l'indique.
- `?last_id=` permet de rejouer les événements manqués depuis la table
  `events`.

## Erreur 429 `capacity_exceeded` au lancement

Trop de missions concurrentes : attendre ou augmenter
`OMNI_MAX_CONCURRENT_MISSIONS` **après** avoir vérifié la mémoire/CPU.
`OMNI_MAX_PARALLEL_AGENTS` borne la concurrence des agents, pas le nombre
d'agents planifiés.

## « 100 agents » mais pic de concurrence à 8

Attendu et documenté : `MAXIMUM` planifie/mobilise les 100, l'infrastructure
n'en exécute simultanément que `OMNI_MAX_PARALLEL_AGENTS`. Le rapport publie
`peak_concurrency_measured` et `queued_not_simultaneous`.

## PostgreSQL / Redis / Qdrant injoignables

Laisser `OMNI_DATABASE_URL`, `OMNI_REDIS_URL`, `OMNI_QDRANT_URL` vides pour
les replis locaux (SQLite, file asyncio, index cosinus local). Vérifier les
healthchecks : `docker compose ps`, `docker compose logs postgres`.

## Injection détectée dans une source

`injection_flags` est renseigné sur la source ; le texte affiché contient
`[INSTRUCTION_NEUTRALISEE:…]`. La source reste consultable mais ses
instructions ne sont jamais suivies. Aucune exécution de code n'est possible.

## Interface / Android

- Page blanche : vérifier `GET /api/health` depuis le **téléphone** (pas
  `localhost`, qui désigne le téléphone). Utiliser l'IP LAN du serveur.
- « Ajouter à l'écran d'accueil » indisponible : PWA exige HTTPS (ou
  `localhost`) ; placer un reverse proxy TLS.
- Données périmées : le service worker ne cache que la coquille. Forcer le
  rechargement, ou `Déconnexion` puis reconnexion.

## Résultats de tests divergents

```bash
.venv/bin/python scripts/gen_profiles.py --check   # profils générés synchronisés
.venv/bin/python -m pytest -q
node --test tests/test_web_ui.test.js
.venv/bin/python scripts/verify_offline.py
```

`test-results/` contient les traces de la dernière exécution locale ; la CI
conserve les siennes en artefact.
