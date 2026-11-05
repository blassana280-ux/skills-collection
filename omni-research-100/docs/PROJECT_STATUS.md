# État précis du projet — reprise sans recommencer

Date : 2026-11-03 (UTC). Classification exhaustive : `docs/FINAL_DELIVERY.md`.
Branche de session :
`arena/63999462-skills-collection` du dépôt
`blassana280-ux/skills-collection`. Code produit dans `omni-research-100/`.

## 0 quater. Reprise du preview du 2026-11-05 (session Arena)

- **Inspection d'abord** : le processus `uvicorn` (PID 5758) tournait déjà sur
  `0.0.0.0:8000`, `health ok`, 100 agents. Blocage réel identifié : la page
  renvoyait `X-Frame-Options: DENY` et `frame-ancestors 'none'`, donc l'aperçu
  Arena ne pouvait pas l'afficher.
- **Réparation** : `OMNI_FRAME_ANCESTORS` rend l'embarquement configurable,
  strict par défaut, refusant toute valeur malformée et **ignoré en
  production**. Nouveau lanceur `scripts/serve_preview.sh` (+ cible
  `make preview`) et configuration locale `data/preview.env` ignorée par Git.
  Aucun secret réel publié : mots de passe de développement documentés dans
  `.env.example`.
- **3 bugs découverts et corrigés** : iframe bloquée ; `length_stats([])`
  omettait `total_words` (DEEP-03 en `KeyError` avec 0 source) ; rotation de
  mot de passe sans effet au redémarrage (401). 8 tests de non-régression.
- **Vérifications rejouées** : **87 pytest + 16 Node = 103 tests, 0 échec**,
  pipeline hors ligne, conformité OmniBrain 6/6, audit des dépendances,
  catalogue 100/100, **38/38 contrôles HTTP** sur l'application relancée
  (login, SSE réel, cycle OmniBrain complet), aucun `agent_failed` dans les
  nouveaux journaux. Processus de preview : `omni-research-100-a975a204`.
- Aucune fusion, aucune modification de `main`, aucune suppression, aucun
  secret publié, aucune dépense. Le dépôt privé cible reste inaccessible
  (403) au jeton de cette session : inchangé.

## 0. Livraison du 2026-11-04 — dépôt privé dédié LIVRÉ

> Les affirmations de cette section proviennent de l'agent de reprise (Mistral).
> La vérification indépendante réalisable depuis CETTE session est consignée au
> §0 bis : l'existence du dépôt est confirmée, son contenu et ses PR ne sont pas
> accessibles au jeton de cette session.

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

## 0 bis. Vérification croisée du 2026-11-04 (session Arena d'origine)

Contrôle demandé après l'intervention de Mistral. Rapport complet :
`test-results/cross_check_2026-11-04.json`.

| Point | Résultat vérifié |
|---|---|
| Existence du dépôt cible | **Confirmée indirectement** : `git ls-remote` cible → `Write access to repository not granted / 403`, alors qu'un nom inexistant → `Repository not found / 404` ; API avec jeton → `403 Resource not accessible by integration` (avant création : 404) ; sans jeton → 404, normal pour un dépôt privé |
| Accès au dépôt cible | **BLOQUÉ** pour ce jeton : 403 sur `GET /repos/...`, `/branches`, `/branches/main/protection`, `/actions/runs`, PRs. Droits de l'installation toujours sans `administration` |
| Commits de l'agent de reprise | `c4bd3d5`, `b3be423` — **1 seul fichier modifié** : `docs/PROJECT_STATUS.md`. Aucun code produit altéré |
| CI de la branche de session | **Verte** : runs `41749092607`, `41749617698`, `41753670783` |
| PR #2 | **OPEN, non fusionnée** ; aucune fusion effectuée |
| Suite de tests rejouée ici | **87 pytest + 16 Node, 0 échec** ; `verify_offline.py`, `verify_omnibrain_contract.py` (6/6) et `gen_profiles.py --check` tous verts |
| Intégrité de la source locale | 124 fichiers suivis, 13 modules `app/brain`, 3 scripts `.sh` exécutables — conforme à ce qui a dû être répliqué |
| **Non vérifiable ici** | 124 fichiers répliqués, SHA d'arbres, 4 branches `feat/01..04`, 4 PR #1–#4, CI du dépôt autonome, corrections des modules/permissions, absence de code sur `main` |

`scripts/verify_delivery_repo.py` a été ajouté : il consigne
`test-results/delivery_repo_check.json` (`status: BLOQUÉ`, 6 champs non
vérifiés) et, dès que le jeton aura accès au dépôt, listera branches, 4 PR,
CI, protection de `main` et SHA de l'arbre. Une seule commande suffira :
`make verify-delivery`.

**Pour lever ce dernier angle mort** : reconnecter GitHub dans cette session
Arena (le jeton est antérieur à la création du dépôt), puis relancer
`gh pr list --repo blassana280-ux/omni-research-100`,
`gh run list --repo blassana280-ux/omni-research-100` et
`gh api repos/blassana280-ux/omni-research-100`. Aucune autre intervention
n'est demandée ; aucune opération sensible n'a été effectuée.

## 0 ter. Vérifications complémentaires du 2026-11-04 (session Arena)

- **Application réelle vérifiée en HTTP** : `scripts/verify_live_api.py` →
  **38/38 contrôles OK** (`test-results/live_api_full.json`) : authentification,
  refus d'accès anonyme, réglages, métriques, audit, sauvegarde, refus de purge
  destructive, 100 agents, fournisseurs, cycle de mission complet, **flux SSE
  avec événements réellement lus**, rapport, contrat/modes/version/queue
  OmniBrain et cycle de soumission. Cette étape est désormais rejouée en CI.
- **Interface exécutée dans un vrai DOM** : `tests/test_web_ui_dom.test.js`
  (11 tests jsdom) exécute le `app/web/app.js` réel : connexion, 3 modes,
  lancement, SSE authentifié, agents, sources, contradictions, rapport anti-XSS,
  historique, fournisseurs, paramètres, déconnexion.
- **Garde DNS SSRF et manifests Docker** : 6 tests
  (`tests/test_deployment_and_ssrf.py`) avec résolveur contrôlé, validation
  structurelle de `docker-compose.yml`/`Dockerfile`/SearXNG et `bash -n` des
  scripts de sauvegarde. La résolution DNS en conditions réelles reste non
  vérifiée.
- **3 bugs découverts et corrigés** : `_mode()` rejetait un `mode` racine
  (`str(Mode.FAST)` → `"Mode.FAST"`) ; la garde de version OmniBrain ne
  couvrait que `POST /missions` ; le résultat du bouton « Tester réellement »
  disparaissait au re-rendu. Tests de non-régression ajoutés.
- Suite portée à **87 tests Python + 16 tests Node, 0 échec**.

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
- **Tests** : 87 Python + 16 Node + 1 pipeline hors ligne, **0 échec**,
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

Le dépôt cible **existe désormais** (privé, créé manuellement le 2026-11-04) :
depuis cette session, `GET /repos/blassana280-ux/omni-research-100` renvoie
**403 Resource not accessible by integration** (contre 404 avant sa création et
404 pour un nom de dépôt inexistant). Le jeton d'installation GitHub App de
cette session n'a donc pas accès au nouveau dépôt : **son contenu, ses 4 PR et
sa CI ne peuvent pas être vérifiés ici**. La branche de session et la PR #2
restent la source vérifiable. `main`/`master` n'a jamais été modifié
directement et aucune PR n'a été fusionnée.

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
