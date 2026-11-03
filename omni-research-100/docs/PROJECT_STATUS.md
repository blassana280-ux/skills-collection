# État précis du projet — reprise sans recommencer

Date : 2026-11-03 (UTC). Branche de session :
`arena/63999462-skills-collection` du dépôt
`blassana280-ux/skills-collection`. Code produit dans `omni-research-100/`.

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
- **Tests** : 68 Python + 5 Node + 1 pipeline hors ligne, **0 échec**,
  résultats dans `test-results/` ; 8 bugs découverts et corrigés
  (`docs/TEST_RESULTS.md`).
- **CI / Docker / docs** : 2 workflows, Dockerfile, docker-compose 5 services,
  scripts de sauvegarde/restauration, audit des dépendances, 13 documents,
  `.env.example`, `Makefile`.
- **OmniBrain** : contrat réel inspecté en lecture seule, adaptateur versionné,
  export des agents, file JSONL compatible, permissions alignées, 6 tests.

## 2. Éléments BLOQUÉS (ne pas prétendre le contraire)

| Élément | Cause exacte | Intervention requise |
|---|---|---|
| Création du dépôt privé `blassana280-ux/omni-research-100` | `gh repo create blassana280-ux/omni-research-100 --private …` → **`GraphQL: Resource not accessible by integration (createRepository)`** : le jeton GitHub connecté n'a pas le droit de créer des dépôts | Accorder le scope d'administration/création de dépôt à la connexion GitHub d'Arena, **ou** créer manuellement un dépôt privé **vide** (sans README automatique) `blassana280-ux/omni-research-100`. Aucune autre intervention n'est demandée |
| Protection de `main` | `GET /repos/blassana280-ux/skills-collection/branches/master/protection` → **403 Resource not accessible by integration** ; de plus, modifier des permissions globales fait partie des opérations soumises à autorisation explicite | Droit d'administration + autorisation explicite de l'utilisateur |
| Fusion d'une PR | Interdite sans accord explicite | Autorisation explicite |
| Déploiement payant | Interdit sans accord | Autorisation explicite |

Le dépôt cible **n'existe pas** : `GET /repos/blassana280-ux/omni-research-100`
→ 404. Le livrable est donc versionné dans le dépôt de session, sur la branche
dédiée, avec une PR ouverte non fusionnée. `main`/`master` n'a jamais été
modifié directement.

## 3. Éléments IMPLÉMENTÉS MAIS NON VÉRIFIÉS (à faire après déblocage)

1. Appels live aux 5 API de recherche (clés absentes, réseau sortant limité à
   github.com / api.github.com / codeload.github.com / registry.npmjs.org /
   pypi.org / files.pythonhosted.org). Vérifier avec
   `POST /api/providers/{name}/test` et une clé réelle.
2. Fournisseurs de modèles OpenAI-compatible / Anthropic / Ollama.
3. Exécution de `docker compose up` avec PostgreSQL, Redis, Qdrant, SearXNG
   (binaires absents du sandbox).
4. Contrôle DNS SSRF en conditions réelles (`OMNI_DNS_SSRF_CHECK=true`).
5. UI dans un navigateur Android/desktop réel.
6. Interopérabilité inter-processus avec un orchestrateur OmniBrain externe
   (aucun dépôt OmniBrain cloné ni modifié, par consigne).
7. Résultat CI GitHub Actions sur le runner (à lire via `gh run list`).

## 4. Procédure de reprise (après création du dépôt privé)

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
