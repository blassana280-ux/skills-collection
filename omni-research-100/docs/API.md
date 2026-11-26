# Documentation API

Base : `/api`. OpenAPI interactif : `/docs`, schéma : `/openapi.json`.
Toutes les routes (sauf `/api/health` et `/api/auth/login`) exigent
`Authorization: Bearer <JWT>` ou, pour l'adaptateur OmniBrain,
`X-OmniBrain-Key: <clé>`.

## Authentification

| Méthode | Chemin | Corps | Résultat |
|---|---|---|---|
| POST | `/api/auth/login` | `{"username","password"}` | `access_token`, `role`, `expires_in` |
| GET | `/api/auth/me` | — | acteur courant |
| GET | `/api/auth/permissions` | — | matrice RBAC |

Rôles : `admin` (tout), `researcher` (créer/lire/annuler, tester fournisseurs),
`viewer` (lecture), `omnibrain` (soumission + lecture + annulation via clé).

## Missions

| Méthode | Chemin | Description |
|---|---|---|
| POST | `/api/missions` | Crée et lance. Corps : `{"query": "…", "mode": "fast\|deep\|maximum", "language": "fr", "max_sources": 24, "options": {}}` → `202` + `mission_id` |
| GET | `/api/missions` | Liste (`?status=…&mode=…&limit=…`) |
| GET | `/api/missions/{id}` | État, progression, plan, tâches, événements |
| DELETE | `/api/missions/{id}` | Annulation réelle (`cancelled: true/false`) |
| GET | `/api/missions/{id}/events` | **SSE** (`?last_id=0&timeout=60`) : rejoue la trace puis diffuse ; `event: done` en fin |
| GET | `/api/missions/{id}/agents` | Tâches des agents, statut, vague, durée, sortie structurée, limite de concurrence |
| GET | `/api/missions/{id}/sources` | Sources, empreintes, `verified`, drapeaux d'injection, `untrusted` |
| GET | `/api/missions/{id}/claims` | Affirmations, statut, confiance, domaines indépendants |
| GET | `/api/missions/{id}/contradictions` | Contradictions, résolution, lot gagnant, justification |
| GET | `/api/missions/{id}/report` | `markdown`, `structured`, `verdict`, `citation_count` |
| GET | `/api/history` | Historique + recherches réutilisables |

États : `queued, planning, searching, extracting, analyzing, verifying,
synthesizing, reporting, completed, insufficient_evidence, failed, cancelled`.
Verdicts : `READY` (6 gates + fournisseur réel) ou `NEEDS_WORK`.

Exemple complet :

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"change-me-admin"}' | jq -r .access_token)
curl -s -X POST localhost:8000/api/missions -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"query":"Dernières versions de l API et failles CVE","mode":"deep"}'
curl -s localhost:8000/api/missions/<id>/report -H "Authorization: Bearer $TOKEN"
```

## Agents

`GET /api/agents` (100 profils, filtre `?division=WEB&limit=…`),
`GET /api/agents/divisions`, `GET /api/agents/validation`,
`GET /api/agents/export/omnibrain` (format `registry/agents.json`),
`GET /api/agents/{id}`.

## Fournisseurs

`GET /api/providers` (états, compteurs, quotas), `GET /api/providers/quota`,
`POST /api/providers/{name}/test` (appel réel borné, `{"query":"…"}`),
`PATCH /api/providers/{name}?enabled=true|false`.

## Système et réglages

| Méthode | Chemin | Droit |
|---|---|---|
| GET | `/api/health` | public |
| GET | `/api/settings` | `settings:read` (aucun secret renvoyé) |
| PATCH | `/api/settings` | `settings:write` : concurrence, sources, débit, rétention, fournisseurs désactivés, quotas |
| GET | `/api/metrics` | `metrics:read` : agrégats, usage fournisseurs, erreurs |
| GET | `/api/audit` | `audit:read` |
| POST | `/api/backup` | `settings:write` : copie SQLite |
| POST | `/api/retention/purge` | admin + `{"older_than_days":30,"confirm":"PURGE"}` — **destructif, jamais automatique** |

## Adaptateur OmniBrain v1

Voir `OMNIBRAIN.md`. Préfixe `/api/omnibrain/v1`, en-têtes
`X-OmniBrain-Key` et `X-OmniBrain-Contract: 1.0` (toute autre version ⇒ 422).

## Codes d'erreur

Toutes les erreurs sont typées et JSON : `validation_error` (422),
`authentication_error` (401), `authorization_error` (403), `not_found` (404),
`rate_limited` / `quota_exceeded` / `capacity_exceeded` (429),
`provider_unavailable` (503), `mission_cancelled` (409),
`insufficient_evidence` (422), `unsafe_url` (400), `internal_error` (500).
Le détail des exceptions internes n'est jamais renvoyé au client.

## Limites

- `OMNI_MAX_QUERY_LENGTH` (600), `OMNI_MAX_SOURCES_PER_MISSION`,
  `OMNI_MAX_EXTRACTIONS_PER_MISSION`, `OMNI_MAX_PARALLEL_AGENTS`,
  `OMNI_MAX_CONCURRENT_MISSIONS`, `OMNI_RATE_LIMIT_PER_MINUTE`.
- Le contenu des sources est toujours `untrusted` : les instructions injectées
  sont neutralisées et signalées dans `injection_flags`.
