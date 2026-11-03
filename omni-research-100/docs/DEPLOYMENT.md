# Déploiement reproductible — Docker

Aucun déploiement sur infrastructure payante n'a été effectué (autorisation
requise). Ce guide décrit la procédure reproductible.

## 1. Stack fournie

`docker-compose.yml` : `app` (FastAPI/uvicorn), `postgres:16-alpine`
(source de vérité), `redis:7-alpine` (file de tâches), `qdrant/qdrant:v1.12.1`
(index vectoriel optionnel), `searxng/searxng:latest` (recherche gratuite,
sans clé). Volumes nommés persistants, healthcheck PostgreSQL, redémarrage
`unless-stopped`.

```bash
cp .env.example .env
# Renseigner OMNI_AUTH_SECRET, OMNI_ADMIN_PASSWORD, OMNI_USER_PASSWORD,
# OMNI_OMNIBRAIN_API_KEY, OMNI_SEARXNG_SECRET ; ajouter les clés souhaitées
docker compose up --build -d
docker compose ps
curl http://localhost:8000/api/health
```

L'application n'écoute que sur `0.0.0.0:8000`. Aucun port de base n'est
exposé publiquement par défaut (à ajouter volontairement si besoin).

## 2. Démarrage minimal (sans services externes)

```bash
docker run --rm -p 8000:8000 --env-file .env \
  -e OMNI_DATABASE_URL=sqlite:///./data/omni_research.db \
  -v "$PWD/data:/srv/omni/data" omni-research-100
```

`OMNI_REDIS_URL` et `OMNI_QDRANT_URL` vides déclenchent les replis locaux
réellement testés (`InProcessQueue`, `LocalVectorIndex`).

## 3. Secrets

- `.env` est exclu de Git (`.gitignore`). Ne jamais le publier.
- `GET /api/settings` applique `redact()` : secrets, clés, tokens et URL avec
  identifiants ne sont jamais renvoyés.
- Journalisation JSON avec rédaction automatique ; `redact_report()` nettoie
  aussi les rapports avant persistance.
- `OMNI_AUTH_SECRET` doit être aléatoire (≥ 32 octets), par ex.
  `python3 -c "import secrets;print(secrets.token_urlsafe(48))"`.

## 4. Sauvegardes

```bash
./deploy/backup_postgres.sh                       # → data/backups/omni-<UTC>.sql.gz
# SQLite : POST /api/backup avec un token admin
```

Recommandation : tâche cron quotidienne, conservation 30 jours hors site,
test de restauration mensuel. La sauvegarde ne supprime rien.

## 5. Reprise après incident

```bash
docker compose down            # arrêt, volumes conservés
./deploy/restore_postgres.sh data/backups/omni-<UTC>.sql.gz
docker compose up -d
```

La restauration demande une confirmation interactive `RESTAURER` et **écrase**
les données courantes (opération destructive soumise à autorisation humaine).
Les événements `events` étant rejouables, la trace d'une mission peut être
reconstruite ; les rapports sont conservés dans `reports`.

## 6. Reverse proxy HTTPS

Exemple Nginx : `proxy_pass http://127.0.0.1:8000;`,
`proxy_buffering off;` (indispensable pour le SSE),
`proxy_read_timeout 300s;`, en-têtes `X-Forwarded-*` et
`client_max_body_size 1m;`. Renseigner `OMNI_CORS_ORIGINS` si l'origine diffère.

## 7. CI GitHub Actions

`.github/workflows/omni-research-100-ci.yml` (dépôt conteneur) et
`.github/workflows/ci.yml` (dépôt autonome) exécutent : installation des
dépendances épinglées, intégrité des 100 profils générés, analyse des
dépendances + `pip-audit`, 68 tests Python (JUnit), 100 handlers, 5 tests
Node, vérification hors ligne de bout en bout, puis conservation des
résultats en artefact. Voir `TEST_RESULTS.md`.

## 8. Limites de ce contexte

`docker`, `psql`, `redis-server` et `qdrant` sont absents du sandbox de
construction : la stack Docker n'a **pas été exécutée ici**. Les fichiers sont
fournis et cohérents, mais classés « IMPLÉMENTÉ MAIS NON VÉRIFIÉ » pour
l'exécution des services. Les replis locaux, eux, sont exécutés et testés.
