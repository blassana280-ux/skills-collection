#!/usr/bin/env bash
# Sauvegarde PostgreSQL (source de vérité). Aucune suppression de données.
set -euo pipefail
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${1:-./data/backups/omni-${STAMP}.sql.gz}"
mkdir -p "$(dirname "$OUT")"
if command -v docker >/dev/null 2>&1 && docker compose ps postgres >/dev/null 2>&1; then
  docker compose exec -T postgres pg_dump -U omni -d omni_research | gzip > "$OUT"
else
  PGPASSWORD="${PGPASSWORD:-omni}" pg_dump -h "${PGHOST:-localhost}" \
    -U "${PGUSER:-omni}" -d "${PGDATABASE:-omni_research}" | gzip > "$OUT"
fi
echo "Sauvegarde écrite : $OUT ($(wc -c < "$OUT") octets)"
