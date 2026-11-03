# Guide d'installation

## Prérequis

- Python 3.11+, Node 22 (uniquement pour les tests de l'interface).
- Aucune clé API, aucune base externe et aucun abonnement ne sont obligatoires
  pour démarrer : SQLite + file en mémoire + index local + synthèse extractive.

## Installation locale (serveur ou poste de travail)

```bash
git clone https://github.com/blassana280-ux/skills-collection.git
cd skills-collection/omni-research-100      # ou le dépôt autonome, racine du projet
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# ÉDITER .env : au minimum OMNI_AUTH_SECRET, OMNI_ADMIN_PASSWORD,
# OMNI_USER_PASSWORD, OMNI_OMNIBRAIN_API_KEY
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Vérifications :

```bash
curl http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"change-me-admin"}'
# Interface : http://localhost:8000  — OpenAPI : http://localhost:8000/docs
```

## Installation avec Docker (stack complète)

```bash
cp .env.example .env
docker compose up --build -d
docker compose logs -f app
```

La stack démarre l'application, PostgreSQL, Redis, Qdrant et SearXNG. Voir
`DEPLOYMENT.md`. Pour un démarrage **sans** services externes :

```bash
docker build -t omni-research-100 .
docker run --rm -p 8000:8000 --env-file .env \
  -e OMNI_DATABASE_URL=sqlite:///./data/omni_research.db \
  omni-research-100
```

## Tests et vérification

```bash
.venv/bin/python -m pytest -q                       # 68 tests
node --test tests/test_web_ui.test.js             # 5 tests
.venv/bin/python scripts/verify_offline.py        # bout en bout hors ligne
.venv/bin/python scripts/gen_profiles.py --check  # intégrité des 100 profils
.venv/bin/python scripts/audit_dependencies.py
```

Les résultats sont conservés dans `test-results/`.

## Comptes

Deux comptes sont créés au premier démarrage, avec mots de passe **hashés**
(PBKDF2-SHA256, 180 000 itérations) : `admin` (tous droits) et `researcher`
(recherche, lecture). Le compte `omnibrain` n'est pas un compte local : il
utilise la clé `X-OmniBrain-Key`. Aucun mot de passe en clair n'est stocké.
