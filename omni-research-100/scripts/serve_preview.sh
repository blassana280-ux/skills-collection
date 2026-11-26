#!/usr/bin/env bash
# Serveur de preview local — DÉVELOPPEMENT UNIQUEMENT, jamais en production.
#
# Usage : ./scripts/serve_preview.sh [port]        (port 8000 par défaut)
#
# La configuration est lue depuis data/preview.env (ignoré par Git). Si le
# fichier est absent, il est créé avec des secrets aléatoires et les mots de
# passe de développement documentés dans .env.example (admin / change-me-admin).
# OMNI_FRAME_ANCESTORS autorise l'embarquement dans l'iframe du preview ; la
# application reste stricte (DENY / 'none') en l'absence de cette variable et
# refuse tout assouplissement quand OMNI_ENV=production.
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${1:-${OMNI_PORT:-8000}}"
ENV_FILE="${OR100_PREVIEW_ENV:-data/preview.env}"
UVICORN="${OR100_UVICORN:-../.venv/bin/uvicorn}"

if [[ ! -f "$ENV_FILE" ]]; then
  python3 - "$ENV_FILE" <<'PY'
import os, pathlib, secrets, sys
p = pathlib.Path(sys.argv[1])
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text("\n".join([
    "# Généré localement — ne jamais committer (data/ est ignoré par Git).",
    f"OMNI_AUTH_SECRET={secrets.token_urlsafe(48)}",
    "OMNI_ADMIN_PASSWORD=change-me-admin",
    "OMNI_USER_PASSWORD=change-me-user",
    f"OMNI_OMNIBRAIN_API_KEY={secrets.token_urlsafe(24)}",
    "OMNI_ENV=development",
    "OMNI_DATABASE_URL=sqlite:///./data/preview.db",
    "OMNI_SEARXNG_ENABLED=false",
    "OMNI_DNS_SSRF_CHECK=false",
    "OMNI_FRAME_ANCESTORS=*",
]) + "\n", encoding="utf-8")
os.chmod(p, 0o600)
PY
  echo "[preview] configuration créée : $ENV_FILE — connexion admin / change-me-admin" >&2
fi

if [[ ! -x "$UVICORN" ]]; then
  echo "[preview] uvicorn introuvable ($UVICORN) : exécuter 'make install'." >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a
export OMNI_ENV="${OMNI_ENV:-development}"
export OMNI_FRAME_ANCESTORS="${OMNI_FRAME_ANCESTORS:-*}"
export OMNI_SEARXNG_ENABLED="${OMNI_SEARXNG_ENABLED:-false}"
export OMNI_DNS_SSRF_CHECK="${OMNI_DNS_SSRF_CHECK:-false}"

exec "$UVICORN" app.main:app --host 0.0.0.0 --port "$PORT"
