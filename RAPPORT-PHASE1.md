# RAPPORT-PHASE1.md — OmniBrain v4 / débloquer l'existant

**Date :** 2026-11-05 · **Branche :** `arena/2644be5c-skills-collection` (base `9d91dad`) · **Escouade :** A01 SENTINELLE, A02 ARCHIVISTE, A06 REVUE ADVERSE, A07 QA, A08 RISQUE.
**Règle appliquée :** 0 fusion, 0 écriture sur `main`, 0 force. Toute décision de fusion reste à **Lassana**.

> ⚠ **Divergence de périmètre (signalée, pas contournée)** — la mission désigne
> `blassana280-ux/agentskills` / `omni-agents-framework/`, mais le checkout lié à
> cette session est `blassana280-ux/skills-collection`. Les livrables v4 sont
> donc commités **sur la branche Arena de `skills-collection`** ; la promotion
> vers les dépôts cibles est préparée et documentée (`docs/PROMOTION-403.md`),
> jamais poussée de force. Vérification : `git merge-base --is-ancestor 9d91dad HEAD` → OK.

---

## 1.1 — Audit PR #2 (`blassana280-ux/agentskills#2`)

| Champ | Valeur relevée |
| --- | --- |
| Titre | *Framework OmniBrain complet : routage multi-agents exécutable, 12 agents, gates qualité, CI* |
| État | `OPEN`, `isDraft=false`, `mergeable=MERGEABLE`, **`mergeStateStatus=CLEAN`** |
| Branches | `arena/fba5d524-agentskills` → `main` |
| HEAD | `12ce4e0` « Hygiène de routage du catalogue » (5 commits) |
| Fichiers | 100 (`AGENTS.md`, `.github/workflows/omnibrain.yml`, `omni-agents-framework/**`) |
| Contenu réel | 112 agents, 10 escouades, 50 tests, matrice TOML + générateur |
| CI | **6/6 `success`** (GitHub Actions), 0 échec, 0 en attente |
| Statut de commit | `state=pending`, `total_count=0` → aucun status externe requis |

**Preuve CI** (`gh api …/commits/12ce4e0…/check-runs`) : runs `40666413505` et
`40666421424`, chacun `validate (3.11)`, `validate (3.12)`, `validate (3.13)`
→ `conclusion=success`, `app=github-actions`. Vérification locale du HEAD :
`python3 -m unittest discover -s tests` → **Ran 50 tests … OK** ;
`python3 -m omnibrain validate` → `OK — 112 agents et 7 contrats validés`.

**Conflits avec la base** : `git merge-tree --write-tree main HEAD` →
`cfa05f3bae2093fdfcfc667236a5c7e2d4b0bf0e`, aucun `CONFLICT` → **clean**.

### Ordre de fusion recommandé (décision Lassana)

| Ordre | PR | État | Conflit détecté | Action |
| --- | --- | --- | --- | --- |
| 1 | **#2** | OPEN / CLEAN | aucun avec `main` | Fondation : la fusionner d'abord (112 agents, CI verte). |
| 2 | **#4** | OPEN / CLEAN *(vs `main`)* | **`CONFLICT (content)` sur `AGENTS.md` avec #2** (`merge-tree` → `afc5dfb6…`) | Rebaser sur le `main` post-#2 puis résoudre **à la main** : conserver l'`AGENTS.md` upstream restauré octet pour octet, déplacer la couche OmniBrain en section marquée. |
| 3 | **#3** | OPEN / CLEAN | `merge-tree` #2 + #3 → `c90845f2…` sans conflit (à re-vérifier après #4) | 70 agents de trading ; fusionner après #4. |
| 4 | **#1** | OPEN / CLEAN | hors périmètre OmniBrain (Nexus AI Hub) | Décision séparée. |

Variante : si la restauration de l'`AGENTS.md` upstream est prioritaire,
fusionner #4 **avant** #2 puis rebaser #2 — le conflit sur `AGENTS.md` demeure,
il change simplement de camp. `merge-tree` #3 + #4 → `7ec31b36…` (clean).

Commandes **à exécuter par Lassana** (aucune lancée ici) :

```bash
gh pr merge 2 -R blassana280-ux/agentskills --merge
# puis rebase/résolution manuelle de #4, puis :
gh pr merge 4 -R blassana280-ux/agentskills --merge
gh pr merge 3 -R blassana280-ux/agentskills --merge
```

---

## 1.3 — Audit des 37 PRs `omnibrain/agents-md-*`

Relevé sur les **46 dépôts du compte** : **37 PRs**, **37 dépôts distincts**,
**1 seul fichier modifié par PR : `AGENTS.md`** (jeu de fichiers vérifié :
`{('AGENTS.md',)}`).

- **36 MERGED** le 2026-11-04 entre `20:04:03Z` et `20:08:45Z`.
- **1 CLOSED sans fusion** : `omni-agents-framework#4` —
  `mergeable=CONFLICTING`, `mergeStateStatus=DIRTY`, `closedAt=20:03:52Z`,
  `mergedAt=null`, fichier `AGENTS.md`. Ce conflit est **avec la branche `main`
  de son propre dépôt**, pas avec la PR #2.
- `skills-collection#1` est l'une des 36 : son merge `9d91dad` est la base de
  cette branche Arena (vérifié par `git merge-base --is-ancestor`).

**Conflit avec la PR #2 : AUCUN.** Les 37 PRs touchent l'`AGENTS.md` racine de
37 dépôts différents ; la PR #2 vit dans `agentskills` et touche
`agentskills/AGENTS.md`, `.github/workflows/omnibrain.yml` et
`omni-agents-framework/**`. Aucun chemin commun, aucun dépôt commun → zéro
conflit par construction, confirmé par l'énumération des fichiers.

**Ordre de fusion : sans objet** (déjà exécuté). Pour la seule PR restante :
elle est déjà close ; si Lassana souhaite l'overlay sur le dépôt dédié, recréer
une PR rebasée sur le `main` actuel (qui a reçu #3 et #10 depuis), priorité
basse. Ne pas réouvrir ni fusionner en force.

### Résumé d'exécution pour Lassana

1. ✅ 36 overlays déjà intégrés → **rien à faire**.
2. ⚠ `omni-agents-framework#4` close `DIRTY` → **à recréer seulement si utile**,
   en conservant l'`AGENTS.md` du dépôt dédié comme autorité.
3. ✅ PR #2 indépendante des 37 → **fusionnable en premier** (§1.1).
4. ✅ Aucune fusion effectuée par l'escouade.

### Tableau des 37 PRs (preuve)

| # | Dépôt | PR | État | Fusion / clôture (UTC) | Merge SHA | Fichiers |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `agency-agents` | #3 | MERGED | 2026-11-04 20:04:03 | `d0f6e7ad8d68` | AGENTS.md |
| 2 | `awesome-agent-skills` | #1 | MERGED | 2026-11-04 20:04:09 | `70eae60cc71a` | AGENTS.md |
| 3 | `awesome-claude-code` | #1 | MERGED | 2026-11-04 20:04:15 | `056fbe1ceb23` | AGENTS.md |
| 4 | `awesome-gamedev-agent-skills` | #1 | MERGED | 2026-11-04 20:04:22 | `5e687a01d096` | AGENTS.md |
| 5 | `designer-skills` | #1 | MERGED | 2026-11-04 20:04:29 | `19ae0c3d5f68` | AGENTS.md |
| 6 | `cc-skills-golang` | #1 | MERGED | 2026-11-04 20:04:35 | `339d0aa19336` | AGENTS.md |
| 7 | `ResumeSkills` | #1 | MERGED | 2026-11-04 20:04:41 | `c297ec0d0cfb` | AGENTS.md |
| 8 | `awesome-claude-code-toolkit` | #1 | MERGED | 2026-11-04 20:04:48 | `251547849360` | AGENTS.md |
| 9 | `ai-agent-skills-collection` | #1 | MERGED | 2026-11-04 20:04:54 | `de97974c798d` | AGENTS.md |
| 10 | `xquads-squads` | #1 | MERGED | 2026-11-04 20:05:28 | `900c52c7cc00` | AGENTS.md |
| 11 | `agent-skills` | #1 | MERGED | 2026-11-04 20:05:38 | `88918bca2daa` | AGENTS.md |
| 12 | `agent-skills-index` | #1 | MERGED | 2026-11-04 20:05:44 | `69a2742eff63` | AGENTS.md |
| 13 | `antigravity-skills` | #1 | MERGED | 2026-11-04 20:05:50 | `c60b57b94580` | AGENTS.md |
| 14 | `skills` | #1 | MERGED | 2026-11-04 20:05:57 | `56e2b186aa54` | AGENTS.md |
| 15 | `skills-collection` | #1 | MERGED | 2026-11-04 20:06:03 | `9d91dad0279c` | AGENTS.md |
| 16 | `skills-` | #1 | MERGED | 2026-11-04 20:06:10 | `31f4777e5674` | AGENTS.md |
| 17 | `agent-skills-3` | #1 | MERGED | 2026-11-04 20:06:16 | `3a1ac98720b6` | AGENTS.md |
| 18 | `ai-engineering-hub` | #1 | MERGED | 2026-11-04 20:06:23 | `b5d6e9d556c7` | AGENTS.md |
| 19 | `awesome-llm-apps` | #1 | MERGED | 2026-11-04 20:06:37 | `6da81cc944cb` | AGENTS.md |
| 20 | `kilocode` | #1 | MERGED | 2026-11-04 20:06:49 | `077d2b73939b` | AGENTS.md |
| 21 | `builder` | #1 | MERGED | 2026-11-04 20:06:55 | `6c012fc74f34` | AGENTS.md |
| 22 | `video-use` | #1 | MERGED | 2026-11-04 20:07:02 | `5d2108670e00` | AGENTS.md |
| 23 | `Red-DiscordBot` | #1 | MERGED | 2026-11-04 20:07:08 | `ebb695a975f6` | AGENTS.md |
| 24 | `Qwen3.8` | #1 | MERGED | 2026-11-04 20:07:14 | `1804ff32526e` | AGENTS.md |
| 25 | `LLMLingua` | #1 | MERGED | 2026-11-04 20:07:21 | `dd00af89db8d` | AGENTS.md |
| 26 | `GPTCache` | #1 | MERGED | 2026-11-04 20:07:28 | `29c3fb2649bc` | AGENTS.md |
| 27 | `mem0` | #1 | MERGED | 2026-11-04 20:07:34 | `25cbc16e180f` | AGENTS.md |
| 28 | `cognee` | #1 | MERGED | 2026-11-04 20:07:40 | `293beb266107` | AGENTS.md |
| 29 | `Open-Agents` | #1 | MERGED | 2026-11-04 20:07:53 | `d3c701ca8a75` | AGENTS.md |
| 30 | `LMCache` | #1 | MERGED | 2026-11-04 20:08:03 | `78a34c02d1b0` | AGENTS.md |
| 31 | `hindsight` | #1 | MERGED | 2026-11-04 20:08:11 | `13194b829125` | AGENTS.md |
| 32 | `Prompt-Engineering-Guide` | #1 | MERGED | 2026-11-04 20:08:18 | `0880edc3b1bb` | AGENTS.md |
| 33 | `Context-Engineering` | #1 | MERGED | 2026-11-04 20:08:26 | `4dff21f92ce3` | AGENTS.md |
| 34 | `Awesome-Context-Engineering` | #1 | MERGED | 2026-11-04 20:08:32 | `e4adc8af46a0` | AGENTS.md |
| 35 | `how-claude-code-works` | #1 | MERGED | 2026-11-04 20:08:38 | `68493b0761d8` | AGENTS.md |
| 36 | `OmniRoute` | #1 | MERGED | 2026-11-04 20:08:45 | `8f47f562af36` | AGENTS.md |
| 37 | `omni-agents-framework` | #4 | CLOSED (non fusionnée) | 2026-11-04 20:03:52 | `fed7fdefe558` | AGENTS.md |

---

## 1.4 — Dépôt profil `.github` (routage au niveau du compte)

**Résultat API :**

```
POST /user/repos {"name":".github"} → 403 Resource not accessible by integration
GET  /repos/blassana280-ux/.github  → 404 Not Found
```

**Cause** : jeton d'installation GitHub App (`X-Oauth-Scopes` vide), permissions
**repository-scoped** ; la création d'un dépôt au niveau du compte exige un PAT
classique avec scope `repo` (ou l'ajout du dépôt à l'installation). L'API refuse,
conformément à la règle « documenter et passer à la suite ».

**Procédure manuelle exacte pour Lassana** (session GitHub personnelle, PAS le
jeton d'intégration) :

```bash
# 1. Créer le dépôt public de profil (nom obligatoire : .github)
gh repo create blassana280-ux/.github --public --description "Profil OmniBrain — routage des agents" --confirm
# 2. Cloner et déposer les deux fichiers
git clone https://github.com/blassana280-ux/.github.git profile-github && cd profile-github
cp ../skills-collection/omni-agents-framework/docs/PROFILE-REPO-AGENTS.md AGENTS.md
printf '# blassana280-ux\n\nRéseau OmniBrain : voir AGENTS.md et OMNIBRAIN.md.\n' > README.md
# 3. Branche + PR interne (jamais d'écriture directe sur main)
git switch -c omnibrain/profile-agents && git add AGENTS.md README.md
git commit -m "docs(profile): routage OmniBrain au niveau du compte"
git push -u origin omnibrain/profile-agents
gh pr create --base main --head omnibrain/profile-agents --title "Routage AGENTS.md au niveau du compte"
# 4. Fusion par Lassana, puis ajouter le nouveau dépôt à l'installation GitHub App
#    si le jeton d'intégration doit pouvoir le lire/écrire.
```

Le contenu prêt à copier est **`omni-agents-framework/docs/PROFILE-REPO-AGENTS.md`**.
Note honnête : GitHub n'interprète nativement que le `README.md` de profil ;
l'`AGENTS.md` de compte est une **convention de routage pour les agents IA**, pas
une fonctionnalité GitHub. Pour une couverture garantie dépôt par dépôt, utiliser
`python3 -m omni overlays --account blassana280-ux --apply` depuis le framework
(36 overlays déjà appliqués).

---

## 1.5 — Erreur 403 sur `omni-agents-framework` & promotion

Trois 403 **distincts** (détail complet : `omni-agents-framework/docs/PROMOTION-403.md`) :

| Cible | Historique | État 2026-11-05 |
| --- | --- | --- |
| `optimiser-mes-agents-IA` (lecture) | `403 Resource not accessible by integration` cité dans PR #2 / #4 | **Toujours 403** → référence à ne plus citer. |
| `omni-agents-framework` (écriture) | PR #2 : « token sans accès en écriture (403) » ; PR #4 : sonde sur 41 dépôts, 40 × 403, seul `agentskills` writable | **LEVÉ** : `permissions {admin,maintain,push,pull,triage} = true`, `pushed_at=2026-11-05T01:33:48Z`, PR #3 et #10 fusionnées. |
| `.github` (création de dépôt) | n/a | **Toujours 403** → §1.4. |

**Plan de promotion** (accès désormais accordé, mais **non exécuté** ici pour
respecter la branche de session et la règle « aucune fusion forcée ») :
`omnibrain/promote-v4` sur le dépôt dédié → copie de `omni/`, `omnibrain/`,
`tools/`, `tests/`, `specialized/`, `catalog/`, `matrix.toml`, `docs/` →
résolution des collisions (`AGENTS.md` à conserver, `omni/__init__.py` à
**fusionner** avec l'orchestrateur v1, `tests/__init__.py` à conserver) → PR →
CI verte → revue adverse/QA/risque → **fusion par Lassana**. Table de collisions
et commandes : `docs/PROMOTION-403.md`.

---

## Preuves & reproductibilité

```bash
gh pr view 2 -R blassana280-ux/agentskills --json state,mergeable,mergeStateStatus,headRefName
gh api repos/blassana280-ux/agentskills/commits/12ce4e0/check-runs --jq '.check_runs[]|[.name,.conclusion]|@tsv'
git merge-tree --write-tree <main> <pr2>            # cfa05f3… clean
git merge-tree --write-tree <pr2> <pr4>             # afc5dfb… CONFLICT AGENTS.md
gh pr list -R <repo> --state all --json number,headRefName,state,mergedAt
gh api repos/blassana280-ux/omni-agents-framework --jq '.permissions'
gh api -X POST user/repos -f name='.github'         # 403 documenté
```

Machine-readable : `omni-agents-framework/docs/PHASE1-EVIDENCE.json`.

**Verdict Phase 1 : PR #2 fusionnable (CLEAN, CI 6/6), 0 conflit avec les 37
PRs, 37/37 déjà closes, 2 actions manuelles pour Lassana (profil `.github`,
promotion) — aucune fusion effectuée.**
