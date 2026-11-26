#!/usr/bin/env bash
# Enrôlement sécurisé d'une clé fournisseur — À EXÉCUTER SUR LA MACHINE OÙ SUPREME
# TOURNE RÉELLEMENT (Android/Termux, poste Linux, ou votre serveur).
#
#   ./ops/enroll-mistral.sh            # enregistrement + vérification + découverte
#   ./ops/enroll-mistral.sh --replace  # remplace une clé déjà enregistrée
#   ./ops/enroll-mistral.sh --check    # statut seul, aucune saisie
#
# Garanties :
#   - la clé n'est JAMAIS un argument, ni dans l'historique shell, ni dans un pipe ;
#   - saisie deux fois sans écho via getpass (terminal privé obligatoire) ;
#   - fichier 0600 dans un répertoire 0700, hors dépôt et gitignoré ;
#   - aucune trace de clé dans la sortie, les journaux ou les rapports ;
#   - `set -x` interdit ici : ne jamais l'ajouter ;
#   - vérification = GET /v1/models, GRATUIT, sans génération ;
#   - AUCUNE inférence payante n'est déclenchée par ce script.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"
PYTHON="${SUPREME_PYTHON:-python3}"
PROVIDER="${SUPREME_PROVIDER:-mistral}"
MODE="enroll"
case "${1:-}" in
  --replace) MODE="replace" ;;
  --check)   MODE="check" ;;
  "")        ;;
  *) echo "usage: $0 [--replace|--check]" >&2; exit 2 ;;
esac

say() { printf '%s\n' "$*"; }
hr()  { printf '%s\n' "------------------------------------------------------------"; }

hr
say "ENRÔLEMENT FOURNISSEUR : $PROVIDER"
say "Machine : $(uname -s -m) · Python : $($PYTHON --version 2>&1)"
say "Répertoire de travail : $HERE"
hr

# 1) Terminal privé obligatoire : refuse pipe, chat, journal, redirection.
if [[ "$MODE" != "check" && ! -t 0 ]]; then
  say "REFUS : aucun terminal privé détecté (stdin n'est pas un TTY)."
  say "La saisie d'une clé est interdite hors terminal interactif, pour qu'elle ne"
  say "puisse jamais transiter par un pipe, un journal ou une conversation."
  say "Sur Android : ouvrez Termux et relancez ce script directement."
  exit 3
fi

# 2) Le stockage doit être hors dépôt et ignoré par Git.
VAR_DIR="${SUPREME_VAR_DIR:-$HERE/var/supreme}"
say "Stockage prévu : $VAR_DIR/secrets/$PROVIDER.key"
if git check-ignore -q "$VAR_DIR" 2>/dev/null || [[ "$VAR_DIR" != "$HERE/"* ]]; then
  say "OK : emplacement ignoré par Git ou externe au dépôt."
else
  say "REFUS : $VAR_DIR est suivi par Git. Choisissez un SUPREME_VAR_DIR hors dépôt."
  exit 4
fi

# 3) Joignabilité réseau réelle AVANT toute saisie : inutile d'enregistrer une clé
#    dans un environnement qui ne peut pas joindre le fournisseur.
say ""
say "Test de joignabilité (GET sans clé, gratuit, sans inférence)…"
if ! "$PYTHON" - <<'PYEOF'
import json, os, sys, urllib.error, urllib.request
provider = os.environ.get("SUPREME_PROVIDER", "mistral")
hosts = {"mistral": "https://api.mistral.ai/v1/models",
         "openai": "https://api.openai.com/v1/models",
         "deepseek": "https://api.deepseek.com/v1/models",
         "openrouter": "https://openrouter.ai/api/v1/models"}
url = hosts.get(provider)
if not url:
    print(json.dumps({"provider": provider, "reachable": None, "note": "hôte non pré-déclaré"}))
    sys.exit(0)
try:
    urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=20).close()
    print(json.dumps({"url": url, "reachable": True, "http_status": 200}))
    sys.exit(0)
except urllib.error.HTTPError as exc:
    # 401/403 = le fournisseur a répondu : le réseau passe, l'auth est attendue.
    print(json.dumps({"url": url, "reachable": True, "http_status": exc.code,
                      "note": "réponse du fournisseur sans clé : réseau passant"}))
    sys.exit(0)
except Exception as exc:
    print(json.dumps({"url": url, "reachable": False, "error": f"{type(exc).__name__}: {exc}"[:160],
                      "note": "blocage réseau, PAS un échec d'authentification"}))
    sys.exit(1)
PYEOF
then
  hr
  say "ARRÊT : cet environnement ne joint pas $PROVIDER."
  say "Y enregistrer la clé ne permettrait AUCUNE vérification réelle."
  say "Exécutez ce script sur la machine qui hébergera réellement SUPREME"
  say "(Android/Termux ou votre serveur), pas dans un sandbox à egress restreint."
  exit 5
fi

# 4) Statut courant, sans secret.
say ""
say "Statut actuel du credential (sans secret) :"
"$PYTHON" -m supreme providers --status | "$PYTHON" -c \
  "import json,sys; d=json.load(sys.stdin); print(json.dumps([p for p in d.get('providers',[]) if p.get('name')==('$PROVIDER')], ensure_ascii=False, indent=1))"

if [[ "$MODE" == "check" ]]; then
  hr; say "Mode --check : aucune saisie, aucune modification."; exit 0
fi

# 5) Saisie masquée. La clé n'apparaît dans aucune commande ni variable shell.
hr
say "SAISIE MASQUÉE — la clé ne s'affichera pas et ne sera pas journalisée."
say "Collez-la dans le terminal puis Entrée ; elle sera demandée deux fois."
say "N'utilisez jamais le chat, un fichier du dépôt ou un historique shell."
hr
if [[ "$MODE" == "replace" ]]; then
  "$PYTHON" -m supreme providers --connect "$PROVIDER" --replace
else
  "$PYTHON" -m supreme providers --connect "$PROVIDER"
fi

# 6) Audit des permissions réellement appliquées.
say ""
say "Audit du fichier enregistré :"
"$PYTHON" - <<'PYEOF'
import json, os
from supreme import credentials as C
provider = os.environ.get("SUPREME_PROVIDER", "mistral")
path = C.secret_path(provider)
meta = C.status(provider)
report = {"provider": provider, "configured": meta.get("configured"), "source": meta.get("source"),
          "path": str(path), "exists": path.is_file()}
if path.is_file():
    report["file_mode"] = oct(path.stat().st_mode & 0o777)
    report["dir_mode"] = oct(path.parent.stat().st_mode & 0o777)
    report["private"] = (path.stat().st_mode & 0o077) == 0
    report["owner_is_me"] = path.stat().st_uid == os.getuid()
    report["symlink"] = path.is_symlink()
print(json.dumps(report, ensure_ascii=False, indent=1))
assert not report.get("symlink"), "lien symbolique refusé"
assert report.get("private"), "permissions trop larges"
PYEOF

# 7) Vérification RÉELLE et découverte des modèles (GET gratuit, sans génération).
hr
say "VÉRIFICATION RÉELLE + DÉCOUVERTE DES MODÈLES (aucune inférence)"
hr
set +e
"$PYTHON" -m supreme providers --verify "$PROVIDER"
VERIFY_RC=$?
set -e
hr
if [[ $VERIFY_RC -ne 0 ]]; then
  say "Vérification en échec (code $VERIFY_RC). Le fournisseur N'EST PAS connecté."
  say "La clé est enregistrée localement, mais aucun appel authentifié n'a réussi."
  say "Causes possibles : clé invalide/révoquée, quota, réseau, horloge système."
  say "Aucune inférence n'a été tentée. Corrigez puis relancez : $0 --check"
  exit 6
fi

say ""
say "Modèles découverts et persistés (contexte et capacités réels) :"
"$PYTHON" -m supreme mistral status | "$PYTHON" -c \
  "import json,sys; d=json.load(sys.stdin); print(json.dumps({'credential': d.get('credential'), 'verification': d.get('verification'), 'discovered_models': d.get('discovered_models'), 'control': d.get('control')}, ensure_ascii=False, indent=1))"

hr
say "ÉTAPES SUIVANTES — toutes humaines, aucune n'est exécutée par ce script :"
say " 1. Choisir un modèle découvert ci-dessus."
say " 2. Relever les prix OFFICIELS (console du fournisseur) puis les attester :"
say "      $PYTHON -m supreme providers --set-prices $PROVIDER --model MODELE \\"
say "        --input-per-million X --output-per-million Y --source https://SOURCE_OFFICIELLE \\"
say "        --confirm 'JE CONFIRME LES PRIX'"
say " 3. Si le contexte n'est pas exposé par l'API, l'attester depuis la doc officielle :"
say "      $PYTHON -m supreme providers --attest-context $PROVIDER --model MODELE \\"
say "        --context-tokens N --source https://SOURCE_OFFICIELLE --confirm 'JE CONFIRME LE CONTEXTE'"
say " 4. Estimer le budget : $PYTHON ops/budget-plan.py --input-per-million X --output-per-million Y"
say " 5. SEULEMENT ENSUITE, autoriser une fenêtre d'inférence bornée (payante) :"
say "      $PYTHON -m supreme providers --authorize $PROVIDER --budget-usd 0.25 --max-calls 5 \\"
say "        --hours 1 --approved-by VOUS --confirm 'AUTORISER INFERENCE'"
hr
say "Rappel : ce script n'a déclenché AUCUNE inférence payante."
say "Révocation locale : $PYTHON -m supreme providers --revoke $PROVIDER --confirm 'REVOQUER INFERENCE'"
say "Révoquez aussi la clé dans la console du fournisseur en cas de doute."
