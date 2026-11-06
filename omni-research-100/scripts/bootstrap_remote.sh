#!/usr/bin/env bash
# Reprise AUTOMATIQUE après création du dépôt privé cible.
#
#   ./scripts/bootstrap_remote.sh --check   # vérifie l'éligibilité, n'écrit rien
#   ./scripts/bootstrap_remote.sh           # exécute la mise en place complète
#
# Garanties : aucun force-push, aucune fusion, aucune suppression, aucun code
# produit poussé sur `main`, aucune modification des dépôts OmniBrain.
# `main` reçoit UNIQUEMENT un commit vide d'initialisation (GitHub exige au
# moins un commit pour qu'une branche par défaut existe et soit protégeable).
set -euo pipefail

OWNER="${OWNER:-blassana280-ux}"
REPO="${REPO:-omni-research-100}"
SRC="${SRC:-/home/user/skills-collection/omni-research-100}"
DEST="${DEST:-/home/user/omni-research-100}"
CHECK=0
[[ "${1:-}" == "--check" ]] && CHECK=1

say() { printf '%s\n' "$*"; }
fail() { say "BLOQUÉ : $*"; exit 2; }

say "== 1. Le dépôt cible existe-t-il ? =="
if ! gh api "repos/$OWNER/$REPO" --jq .full_name >/dev/null 2>&1; then
  fail "$OWNER/$REPO n'existe pas (404). Créer le dépôt privé VIDE manuellement, puis relancer."
fi
FULL=$(gh api "repos/$OWNER/$REPO" --jq .full_name)
PRIVATE=$(gh api "repos/$OWNER/$REPO" --jq .private)
DEFAULT=$(gh api "repos/$OWNER/$REPO" --jq .default_branch)
say "  $FULL (private=$PRIVATE, default=$DEFAULT)"

say "== 2. Est-il réellement vide ? =="
if gh api "repos/$OWNER/$REPO/commits" --jq 'length' >/dev/null 2>&1; then
  fail "le dépôt contient déjà des commits : aucun écrasement ni force-push ne sera effectué."
fi
say "  dépôt vide : OK (aucune donnée à écraser)"

say "== 3. Droits du jeton =="
PERMS=$(gh api user/installations --jq '.installations[0].permissions' 2>/dev/null || echo '{}')
if echo "$PERMS" | grep -q '"administration"'; then
  say "  administration présent : protection de main tentée"
  CAN_PROTECT=1
else
  say "  administration ABSENT : protection de main restera BLOQUÉE (signalée, pas contournée)"
  CAN_PROTECT=0
fi

say "== 4. Arborescence produit =="
[[ -f "$SRC/app/main.py" ]] || fail "source produit introuvable : $SRC"
say "  $SRC : $(find "$SRC" -type f -not -path '*/.venv/*' -not -path '*/__pycache__/*' | wc -l) fichiers"

if [[ "$CHECK" -eq 1 ]]; then
  say ""
  say "== MODE --check : aucune écriture effectuée =="
  say "Plan : cloner → initialiser main (commit vide) → protéger main si permis →"
  say "       4 branches empilées feat/01..04 avec commits cohérents → 4 PRs NON fusionnées."
  exit 0
fi

say "== 5. Clonage =="
[[ -e "$DEST" ]] && fail "$DEST existe déjà : abandon sans écrasement"
git clone "https://github.com/$OWNER/$REPO.git" "$DEST"
cd "$DEST"
git checkout -B main
git commit --allow-empty -m "chore: initialiser main (aucun code produit)"
git push -u origin main

if [[ "$CAN_PROTECT" -eq 1 ]]; then
  say "== 6. Protection de main =="
  gh api -X PUT "repos/$OWNER/$REPO/branches/main/protection" \
    -F required_status_checks='{"strict":true,"contexts":["quality"]}' \
    -F enforce_admins=true \
    -F required_pull_request_reviews='{"required_approving_review_count":1}' \
    -F restrictions=null || say "  protection refusée : statut BLOQUÉ consigné, aucune contournement"
else
  say "== 6. Protection de main : BLOQUÉE (pas de droit administration) =="
fi

say "== 7. Copie de l'arborescence produit =="
rsync -a \
  --exclude='.venv/' --exclude='__pycache__/' --exclude='.pytest_cache/' \
  --exclude='data/' --exclude='*.db' --exclude='.env' \
  "$SRC/" "$DEST/"

# 4 branches empilées : chaque PR a une base explicite, aucune n'est fusionnée.
declare -a BRANCHES=("feat/01-core-memory" "feat/02-agents-providers-brain" "feat/03-api-omnibrain-ui" "feat/04-tests-ci-docs")
declare -a GROUPS=(
  ".env.example .gitignore pyproject.toml requirements.txt app/__init__.py app/core"
  "app/agents app/providers app/brain app/runtime.py scripts/gen_profiles.py docs/AGENTS_CATALOG.md"
  "app/api app/main.py app/web"
  "tests test-results docs README.md Makefile Dockerfile docker-compose.yml deploy .github scripts"
)
declare -a TITLES=(
  "01 — socle, sécurité, schémas et mémoire persistante"
  "02 — 100 agents, 5 connecteurs Internet et cerveau de recherche"
  "03 — API sécurisée, adaptateur OmniBrain v1 et interface PWA"
  "04 — tests, CI, Docker, sauvegardes et documentation"
)
BASE="main"
for i in 0 1 2 3; do
  say "== 8.$((i+1)). ${BRANCHES[$i]} =="
  git checkout -B "${BRANCHES[$i]}" "$BASE"
  # shellcheck disable=SC2086
  git add -- ${GROUPS[$i]}
  git commit -m "feat(or100): ${TITLES[$i]}"
  git push -u origin "${BRANCHES[$i]}"
  gh pr create --base "$BASE" --head "${BRANCHES[$i]}" \
    --title "OMNI-RESEARCH 100 — ${TITLES[$i]}" \
    --body "Branche dédiée, aucun code produit sur main, PR NON fusionnée. Voir docs/FINAL_DELIVERY.md."
  BASE="${BRANCHES[$i]}"
done

say ""
say "TERMINÉ : 4 PRs ouvertes et non fusionnées, main initialisé sans code produit."
say "Protection de main : $([[ "$CAN_PROTECT" -eq 1 ]] && echo 'tentée (vérifier le résultat)' || echo 'BLOQUÉE — droit administration absent')"
