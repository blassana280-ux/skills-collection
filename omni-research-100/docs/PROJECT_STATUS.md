# État précis du projet — reprise sans recommencer

Date : 2026-11-03 (UTC). Classification exhaustive : `docs/FINAL_DELIVERY.md`.
Branche de session :
`arena/63999462-skills-collection` du dépôt
`blassana280-ux/skills-collection`. Code produit dans `omni-research-100/`.

## 0. Livraison du 2026-11-04 — dépôt privé dédié LIVRÉ

- Le dépôt privé https://github.com/blassana280-ux/omni-research-100 EXISTE
  (créé manuellement par l'utilisateur) et contient l'intégralité du produit :
  124 fichiers produit répliqués depuis cette branche de session via l'API
  GitHub (vérifié par comparaison des SHA d'arbres git source/destination).
- `bootstrap_remote.sh` ne pouvant pas s'exécuter dans l'environnement de
  livraison (ni git, ni python local), il a été répliqué via l'API :
  `main` initialisé par un commit technique `.gitkeep` (un commit strictement
  vide est impossible via l'API Contents) — AUCUN code produit sur `main` ;
  4 branches empilées `feat/01..04` ; 4 PR ouvertes NON fusionnées
  (#1, #2, #3, #4) ; aucun force-push, aucune fusion, aucune suppression.
- Deux écarts de réplication détectés par la CI du nouveau dépôt et corrigés :
  1. six modules de `app/brain` manquaient (`claim_verifier`, `commander`,
     `consensus`, `conflict_resolver`, `evidence_collector`,
     `__init__`) — restaurés sur feat/02, feat/03 et feat/04 ;
  2. bits exécutables (mode git 100755) des scripts `.sh` perdus (l'API
     Contents crée toujours 100644) — restaurés par
     `git update-index --chmod=+x` committé dans l'arbre.
- CI du dépôt autonome : verte sur la PR #4 avec les mêmes étapes que la CI du
  dépôt conteneur (détails dans le dépôt livré :
  `docs/PROJECT_STATUS.md`, `docs/TEST_RESULTS.md`).
- Protection de `main` du nouveau dépôt : **BLOQUÉE** (aucun outil de
  protection exposé par le connecteur + pas de droit `administration`) ;
  jamais contournée.
- Les vérifications §3 (fournisseurs live, Docker, navigateur réel, DNS SSRF,
  interopérabilité inter-processus OmniBrain) restent IMPLÉMENTÉES MAIS NON
  VÉRIFIÉES.

## 1. Terminé et vérifié

- **100 agents** / 10 divisions / 100 handlers / 31 noyaux, générés de façon
  reproductible (`scripts/gen_profiles.py --check` vert), exécutés avec 100
  empreintes distinctes. Catalogue : `docs/AGENTS_CATALOG.md`.
- **Moteur Internet** : 5 connecteurs HTTP réels + plugin registry + routage,
  parallélisme, bascule, quotas, disjoncteur, déduplication, vérification,
  extraction bornée, conservation des preuves, abstraction de modèles.
- **Cerveau** : 11 modules, 3 modes, MAXIMUM = 100 agents planifiés avec
  concurrence réelle mesurée et bornée, arbitrage OmniBrain, 6+1 gates.
- **Mémoire** : 15 tables, événements rejouables, audit, métriques, quotas,
  cache réutilisable, sauvegarde et purge confirmée ; replis locaux réels.
- **API** : auth/RBAC/rate-limit, missions + SSE, agents, fournisseurs,
  réglages, métriques, sauvegarde, rétention, adaptateur OmniBrain v1.
- **UI** : responsive/PWA, 7 vues réelles, SSE authentifié + polling de repli,
  aucune donnée fictive, aucun `innerHTML`.
- **Tests** : 71 Python + 5 Node + 1 pipeline hors ligne, **0 échec**,
  résultats dans `test-results/` ; 8 bugs découverts et corrigés
  (`docs/TEST_RESULTS.md`).
- **CI / Docker / docs** : 2 workflows — **CI verte** sur la PR #2 (run `41727343863`, 1 min 03 s) après correction d'un fichier de résultats exclu par le `.gitignore` racine ; Dockerfile, docker-compose 5 services,
  scripts de sauvegarde/restauration, audit des dépendances, 13 documents,
  `.env.example`, `Makefile`.
- **Application réelle** : `uvicorn` lancé sur `0.0.0.0:8000` (aperçu Arena, aucune infrastructure payante) ; health, UI, login, providers, validation des 100 agents et mission réelle vérifiés par HTTP — sans clé, `insufficient_evidence` avec **0 source** et rapport `NEEDS_WORK` (`test-results/live_app_smoke.json`).
- **OmniBrain** : contrat réel inspecté en lecture seule, adaptateur versionné,
  export des agents, file JSONL compatible, permissions alignées, 6 tests,
  **et contrôle de conformité automatique 6/6 contre les 4 fichiers sources
  réels** (`scripts/verify_omnibrain_contract.py`, rejoué en CI).

## 2. Éléments BLOQUÉS (ne pas prétendre le contraire)

| Élément | Cause exacte | Intervention requise |
|---|---|---|
| Création du dépôt privé `blassana280-ux/omni-research-100` | **Résolue le 2026-11-04** : dépôt créé manuellement par l'utilisateur, puis rempli via l'API GitHub (voir section 0) | — (résolue) |
| Protection de `main` | `GET /repos/blassana280-ux/skills-collection/branches/master/protection` → **403 Resource not accessible by integration** ; de plus, modifier des permissions globales fait partie des opérations soumises à autorisation explicite | Droit d'administration + autorisation explicite de l'utilisateur |
| Fusion d'une PR | Interdite sans accord explicite | Autorisation explicite |
| Déploiement payant | Interdit sans accord | Autorisation explicite |

Le dépôt cible **n'existe pas** : `GET /repos/blassana280-ux/omni-research-100`
→ 404. Le livrable est donc versionné dans le dépôt de session, sur la branche
dédiée, avec une PR ouverte non fusionnée. `main`/`master` n'a jamais été
modifié directement.

## 3. Éléments IMPLÉMENTÉS MAIS NON VÉRIFIÉS (à faire après déblocage)

1. Appels live aux 5 API de recherche : `test-results/providers_live.json`
   indique `live_verified: []` (4 `not_configured`, SearXNG `error` DNS),
   obtenu par `scripts/verify_providers_live.py`. Réseau sortant limité à
   github.com / api.github.com / codeload.github.com / registry.npmjs.org /
   pypi.org / files.pythonhosted.org). Vérifier avec
   `POST /api/providers/{name}/test` et une clé réelle.
2. Fournisseurs de modèles OpenAI-compatible / Anthropic / Ollama.
3. Exécution de `docker compose up` avec PostgreSQL, Redis, Qdrant, SearXNG
   (binaires absents du sandbox).
4. Contrôle DNS SSRF en conditions réelles (`OMNI_DNS_SSRF_CHECK=true`).
5. UI dans un navigateur Android/desktop réel.
6. Interopérabilité inter-processus avec un orchestrateur OmniBrain externe
   (aucun dépôt OmniBrain cloné ni modifié, par consigne). La conformité au
   contrat, elle, est vérifiée automatiquement.
7. ~~Résultat CI GitHub Actions~~ → **fait** : runs `41727343863`, `41727882197`, `41729820449`, `41730222327` et
   `41733501383` verts sur la PR #2.

## 4. Procédure de reprise (après création du dépôt privé)

**Automatisée** : `scripts/bootstrap_remote.sh` (avec `--check` pour un diagnostic
sans écriture). Il refuse de s'exécuter si le dépôt est absent ou non vide,
n'effectue aucun force-push, aucune fusion, aucune suppression, protège `main`
uniquement si le droit existe, crée **4 branches empilées** avec commits
cohérents et **4 PR non fusionnées**. Son `--check` a été exécuté : il a
correctement refusé avec `BLOQUÉ : ... n'existe pas (404)`.

```bash
cd /home/user/skills-collection/omni-research-100
./scripts/bootstrap_remote.sh --check   # diagnostic
./scripts/bootstrap_remote.sh           # après création manuelle du dépôt vide
```

Équivalent manuel (si le script n'est pas utilisé) :

```bash
# 1. Créer le dépôt privé vide (utilisateur) OU reconnecter GitHub avec le scope
# 2. Cloner et initialiser main SANS y travailler
git clone https://github.com/blassana280-ux/omni-research-100.git /home/user/omni-research-100
cd /home/user/omni-research-100
git checkout -b main ; git commit --allow-empty -m "chore: initialiser main" ; git push -u origin main
# 3. Protéger main (nécessite les droits) : exiger PR + statut CI
gh api -X PUT repos/blassana280-ux/omni-research-100/branches/main/protection \
  -F required_status_checks='{"strict":true,"contexts":["quality"]}' \
  -F enforce_admins=true -F required_pull_request_reviews='{"required_approving_review_count":1}' \
  -F restrictions=null
# 4. Copier l'arborescence produit depuis la branche de session
rsync -a --exclude='.venv' --exclude='__pycache__' --exclude='.pytest_cache' \
  /home/user/skills-collection/omni-research-100/ /home/user/omni-research-100/
# 5. Créer des branches dédiées, commits cohérents, PRs NON fusionnées
git checkout -b feat/core-and-agents ; git add app/core app/agents app/brain ... ; git commit ...
git push origin feat/core-and-agents ; gh pr create --base main --head feat/core-and-agents ...
```

Le dossier `.github/workflows/ci.yml` du produit est déjà prévu pour fonctionner
à la racine du dépôt autonome ; le workflow du dépôt conteneur utilise
`working-directory: omni-research-100`.

**Variante API (environnement sans git)** : si l'environnement de reprise ne
dispose pas de `git`, répliquer `bootstrap_remote.sh` via l'API GitHub
(connecteur) — commit initial minimal sur `main`, branches empilées
`feat/01..04`, 4 PR non fusionnées — et consigner les écarts (commit vide
impossible via l'API Contents, protection `main` BLOQUÉE).

## 5. Règles à ne pas oublier

- Ne jamais simuler un résultat de recherche réel ; `READY` impossible sans
  fournisseur réel.
- Ne jamais modifier `main` directement, ne jamais fusionner sans accord,
  ne jamais contourner une protection GitHub.
- Ne pas modifier les dépôts OmniBrain existants.
- Aucune suppression de données sans confirmation explicite.
- Classer chaque fonctionnalité selon :
  `OPÉRATIONNELLE ET TESTÉE` / `IMPLÉMENTÉE MAIS NON VÉRIFIÉE` /
  `PARTIELLE` / `BLOQUÉE`.
