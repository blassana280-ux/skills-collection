# Erreurs 403 — diagnostic précis & plan de promotion

Date du relevé : **2026-11-05**. Trois 403 distincts sont en jeu ; les confondre
conduirait à de fausses conclusions. Ils viennent d'un **jeton d'installation
GitHub App** : l'en-tête `X-Oauth-Scopes` est **vide** (pas de PAT classique),
les permissions sont accordées **dépôt par dépôt**, pas au niveau du compte.

| # | Cible / opération | Relevé | État 2026-11-05 | Interprétation |
| --- | --- | --- | --- | --- |
| A | `GET /repos/blassana280-ux/optimiser-mes-agents-IA` | `403 Resource not accessible by integration` (PR #2 et PR #4 d'`agentskills`, 2026-10-28/29) | **Toujours 403** (re-vérifié) | dépôt hors périmètre de l'installation ; la fiche `specialized-omnibrain-orchestrator-agent.md` n'a jamais été lue. Ne plus citer. |
| B | Écriture sur `blassana280-ux/omni-agents-framework` | PR #2 : « le token d'intégration n'a pas d'accès en écriture (403) » ; PR #4 : sonde sur 41 dépôts → 40 × 403 | **TOUJOURS 403 pour le jeton actuel** (correction A06) : `permissions` annonce `push/admin=true`, mais `git push --dry-run` → `403 Permission denied`, `POST /pulls` → 403, `POST /releases` → 403 | l'objet `permissions` décrit les droits de l'utilisateur, **pas** ceux délégués à l'installation GitHub App. Les PR #3/#10 ont été fusionnées par une autre identité. Promotion impossible sans PAT `repo` ou extension de l'installation. |
| C | `POST /user/repos` (`name=.github`) | `403 Resource not accessible by integration` ; `GET /repos/blassana280-ux/.github` → `404` | **Toujours 403** | création d'un dépôt au niveau du compte non couverte par une installation repository-scoped → procédure manuelle (`RAPPORT-PHASE1.md` §1.4). |

Commandes de preuve :

```bash
gh api repos/blassana280-ux/omni-agents-framework --jq '{permissions,default_branch,pushed_at}'
gh api repos/blassana280-ux/optimiser-mes-agents-IA          # 403
gh api -X POST user/repos -f name='.github'                  # 403
gh api -i user | grep -i x-oauth-scopes                      # vide
git push --dry-run https://github.com/blassana280-ux/omni-agents-framework.git HEAD:refs/heads/<branche>  # 403
git push --dry-run origin arena/2644be5c-skills-collection    # OK (témoin)
```

### Correction de revue adverse (2026-11-05)

La version initiale de ce document concluait « LEVÉ » à partir de l'objet
`permissions` de l'API. Preuve d'écriture réelle ci-dessus : **le 403 subsiste**
pour le jeton d'intégration. Ne jamais déduire un droit d'écriture de
`permissions.push=true` seul : toujours sonder (`git push --dry-run`,
`POST` à payload invalide).

## Plan de promotion du framework (à exécuter dès que l'accès est réellement accordé)

**Aucune promotion n'a été poussée par l'agent** : la branche de session est
`arena/2644be5c-skills-collection`, et toute fusion reste à Lassana. Procédure à
exécuter manuellement depuis un clone du dépôt dédié :

```bash
git clone https://github.com/blassana280-ux/omni-agents-framework.git
cd omni-agents-framework
git switch -c omnibrain/promote-v4
# Depuis le checkout Arena de skills-collection :
cp -a ../skills-collection/omni-agents-framework/{omni,omnibrain,tools,tests,specialized,catalog,matrix.toml,examples,scripts,bin,skills,templates,docs} .
# …voir le tableau de collisions ci-dessous avant de valider
git add -A && git commit -m "feat(omnibrain): promouvoir la couche v4"
git push -u origin omnibrain/promote-v4
gh pr create --base main --head omnibrain/promote-v4 --title "OmniBrain v4" --body "Décision de fusion : Lassana"
```

### Collisions à résoudre (revue adverse A06)

| Chemin | État dans le dépôt dédié | Décision |
| --- | --- | --- |
| `AGENTS.md` | racine du dépôt dédié, source de vérité locale (`8f2922f4…`) ≠ `omni-agents-framework/AGENTS.md` de la PR #2 (`a88c7474…`) | **Conserver** la racine du dépôt dédié ; ajouter les commandes v4 dans une section marquée `<!-- omnibrain-overlay:v4 -->`. Ne pas écraser. |
| `omni/__init__.py` | existe (orchestrateur v1, 20 agents, 69 tests) | **Fusionner** : conserver les exports existants et **ajouter** ceux de `memory/graph/sandbox/telemetry`. Ne jamais remplacer. |
| `omni/memory.py` | module simple (portées run/shared, TTL) | **Conserver** ; le nouveau `omni/memory/` est un paquet distinct, sans collision de nom de module. |
| `tests/__init__.py`, `tests/helpers.py` | existent (suite 69 tests) | **Conserver** ; copier uniquement `test_v4_*.py` et les tests v3 (aucun nom en double, vérifié). |
| `README.md`, `OMNIBRAIN.md`, `registry/` | existent | **Conserver** ; référencer `docs/V4.md` depuis OMNIBRAIN.md sans réécrire la spécification. |
| `tools/`, `specialized/`, `catalog/`, `omnibrain/` | absents du dépôt dédié | copier tels quels (115 agents, 103 fiches générées, 7 contrats). |

### Porte de sortie

1. CI du dépôt dédié verte sur Python 3.11/3.12/3.13 (`python3 -m omni registry`,
   `python3 -m unittest discover -s tests -v`, `python3 -m omnibrain validate`).
2. `git diff --exit-code -- catalog specialized` après régénération.
3. Revue adverse + QA + expert risque ; gates HITL approuvées par Lassana.
4. **Fusion par Lassana uniquement** (`gh pr merge <num> --merge`) ; jamais
   d'écriture directe sur `main`.
