#!/usr/bin/env bash
# Reprise après incident : restaure une sauvegarde existante.
# ATTENTION : cette opération ÉCRASE les données courantes — confirmation requise.
set -euo pipefail
BACKUP="${1:-}"
if [[ -z "$BACKUP" || ! -f "$BACKUP" ]]; then
  echo "Usage: $0 <fichier.sql.gz>" >&2; exit 2
fi
read -r -p "Confirmer la restauration (écrasement) ? taper RESTAURER : " CONFIRM
if [[ "$CONFIRM" != "RESTAURER" ]]; then
  echo "Restauration annulée."; exit 3
fi
if command -v docker >/dev/null 2>&1 && docker compose ps postgres >/dev/null 2>&1; then
  gunzip -c "$BACKUP" | docker compose exec -T postgres psql -U omni -d omni_research
else
  gunzip -c "$BACKUP" | PGPASSWORD="${PGPASSWORD:-omni}" psql \
    -h "${PGHOST:-localhost}" -U "${PGUSER:-omni}" -d "${PGDATABASE:-omni_research}"
fi
echo "Restauration terminée : $BACKUP"
