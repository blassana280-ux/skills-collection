# Changelog OMNIBRAIN SUPREME

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
- **126 tests SUPREME** (+ 105 V4 = 231 verts). CI dédiée Python 3.11/3.12/3.13.
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
