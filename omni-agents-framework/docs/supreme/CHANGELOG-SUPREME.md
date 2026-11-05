# Changelog OMNIBRAIN SUPREME

## 1.1.0 — 2026-11-05 (multi-modèles réel, sécurité, dashboard)
### Ajouté
- **Intégration multi-modèles RÉELLE** (`supreme/providers.py`) : client HTTP stdlib pour
  openai-compatible (OpenAI, **Mistral/Vide**, DeepSeek, Groq, OpenRouter, compatible personnalisé),
  Anthropic, Gemini, Ollama. `complete()` = vrai appel HTTP, aucune réponse simulée.
- **Mistral/Vide prioritaire** (`priority=1`) ; ajout Groq + compatible OpenAI personnalisé.
- Routeur `complete()` avec **fallback multi-fournisseurs + budget réel** ; `configured_models()`
  (le routage cible les fournisseurs configurés, l'appel réel sert de preuve de disponibilité).
- Orchestrateur : les **agents LLM s'exécutent réellement** via le routeur si fournisseur configuré ;
  bloqués honnêtement sinon. Conseil : **vraies analyses indépendantes** (budget borné).
- **Sécurité des clés** : env ou fichier gitignoré `0600` ; jamais journalisées, expurgées des
  erreurs, jamais dans l'URL. CLI `providers` (`--check`, `--init-secrets`).
- **Audit sécurité** (`test_supreme_security_audit.py`) : anti-fuite dépôt, isolation 1020 profils,
  anti-injection, actions protégées, stdlib only, validation entrées.
- **Dashboard mobile** : onglets Coûts + Sécurité, fournisseurs enrichis (configuré ≠ opérationnel),
  contrôle des missions (relancer/annuler). API `/api/providers`, `/api/alerts`, `/api/security`.
- Documentation `PROVIDERS.md` (connexion sécurisée sans exposer de secret).
- **Mémoire (Phase F)** : recherche contextuelle **TF-IDF cosinus locale réelle** (`mode='tfidf'`),
  sans fournisseur — rappel large par tokens + re-ranking cosinus. Embeddings neuronaux toujours
  signalés indisponibles sans fournisseur (honnête).
- Documentation `ECOSYSTEM.md` (organisation dépôts/PR #5 vs #2, infrastructure hybride honnête).
### Tests
- +23 fournisseurs, +15 audit sécurité, +12 API observabilité, +3 TF-IDF → **297 tests verts** (105 V4 + 192 SUPREME).
### Honnêteté
- **0 fournisseur IA réel connecté** à ce stade (aucune clé, egress sandbox limité). Les tests
  fournisseurs utilisent un **stub HTTP local** (local réel, PAS un fournisseur IA réel).
  Mistral/Vide ne sera déclaré opérationnel qu'après un appel API réel réussi.

## 1.0.0 — 2026-11-05
### Ajouté
- Couche SUPREME complète au-dessus d'OmniBrain V4 (stdlib, SQLite).
- 20 divisions × 50 spécialistes = **1000 profils complets** + 20 chefs de division.
- 27 champs obligatoires + 7 évaluations par profil ; contrôles anti-doublons/clones.
- Agent Registry SQLite, Agent Factory (création/version/rollback/suppression contrôlée).
- Mission Planner + Task Decomposer (DAG), orchestrateur (états, idempotence, reprises,
  annulation, parallélisme, backpressure).
- Communication Bus (ACL, anti-usurpation, dédup, ack, file morte, historique).
- Memory Engine 4 niveaux / 8 types (FTS5, graphe, provenance, confiance, versions, TTL,
  contradictions, ACL, rédaction secrets, anti-injection, suppression contrôlée).
- Model Router (détection réelle, routage, fallback, confidentialité) + Multi-Model Council
  (décision par preuves, budget borné). 0 fournisseur configuré → indisponible honnête.
- Policy Engine (4 niveaux de risque, approbations humaines, RBAC V4 réutilisé).
- Security Supervisor (moindre privilège, anti-injection, rédaction, validation entrées).
- Evaluation Engine (7 tests/profil, activation sur preuve réelle).
- Learning + Self-Improvement (stratégies versionnées, gain mesuré, rollback, noyau protégé).
- Cost Controller (quotas provider/agent/division/mission, alertes, coupure, historique).
- Observability (logs structurés, métriques, 15 KPIs réels, null si indisponible).
- Backup & Recovery (SQLite à chaud, intégrité, restauration).
- API Gateway (auth par jeton, rôles) + tableau de bord mobile (données réelles).
- Reporting Engine (missions, divisions, global, markdown).
- 41 outils déterministes réels + Skill Registry (860 skills documentaires indexés).
- **192 tests SUPREME** (+ 105 V4 = 297 verts). CI dédiée Python 3.11/3.12/3.13.
- Documentation complète + suivi durable (CONTINUITY.md).

### Réutilisé (V4, non réécrit)
- `omni/memory/store.py` (rédaction secrets), `omni/sandbox/runtime.py` (RBAC),
  `omni/sandbox/e2b_hook.py` (sandbox), `omni/telemetry` (patron), `tools/optimize_prompts.py` (patron).

### Limites documentées
- Aucun fournisseur IA connecté (clés absentes, réseau sandbox limité).
- Recherche sémantique par embeddings inactive (FTS5 lexical réel).
- Promotion vers `omni-agents-framework` autonome bloquée (403 jeton GitHub App).

## 1.0.1 — 2026-11-05 (durcissement concurrence)
- **Correctif thread-safety** : workers DAG et requêtes API utilisent désormais une connexion
  SQLite par thread (WAL) au lieu de partager la connexion principale. Élimine les erreurs
  `database is locked` sous charge multi-missions / API multi-thread.
- 2 tests de régression ajoutés (missions parallèles, API concurrente) → **126 tests SUPREME / 231 total**.
- Documentation : décomptes réels (41 outils, 231 tests) corrigés.

## 1.0.2 — 2026-11-05 (sécurité : jeton API + journal d'accès)
- **Rotation de jeton sûre** : `python3 -m supreme rotate-token` / `api.rotate_token()` génère un
  jeton 256 bits (`secrets.token_urlsafe(32)`), l'écrit en `0600` (atomique), ne renvoie jamais le
  secret (métadonnées + empreinte SHA-256 tronquée uniquement).
- **Jeton jamais affiché** : suppression de tout `print` du jeton au démarrage (`api.py` + CLI) ;
  seul le chemin du fichier est imprimé.
- **Journal d'accès expurgé** : `var/supreme/access.log` (`0600`, gitignoré) — méthode, chemin,
  statut, IP ; `?token=…` → `REDACTED` ; ni jeton, ni en-têtes, ni corps journalisés.
- Permissions `0600` renforcées à chaque chargement du jeton.
- 13 tests de sécurité API ajoutés (journal expurgé, rotation, révocation, permissions, non-affichage)
  → **192 tests SUPREME / 297 total**.
- Procédure de rotation/révocation documentée dans `SECURITY.md`.
