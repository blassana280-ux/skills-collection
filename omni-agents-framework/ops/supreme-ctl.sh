#!/usr/bin/env bash
# Opérations SUPREME — démarrage/arrêt/sauvegarde/restauration/vérification.
# Sans dépendance externe, sans root, sans réseau. Idempotent.
#
#   ./ops/supreme-ctl.sh start|stop|status|backup|restore|verify|logs|install-units
#
# Le déploiement par défaut est LOCAL (loopback). Aucune exposition publique n'est
# activée par ce script : SUPREME_BIND reste 127.0.0.1 sauf décision humaine explicite.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

VAR_DIR="${SUPREME_VAR_DIR:-$HERE/var/supreme}"
RUN_DIR="$VAR_DIR/run"
LOG_DIR="$VAR_DIR/logs"
PID_API="$RUN_DIR/api.pid"
PID_WORKER="$RUN_DIR/worker.pid"
PID_LEARN="$RUN_DIR/learn.pid"
PID_GUARDIAN="$RUN_DIR/guardian.pid"
BIND="${SUPREME_BIND:-127.0.0.1}"
PORT="${SUPREME_PORT:-8765}"
PYTHON="${SUPREME_PYTHON:-python3}"
WORKERS="${SUPREME_WORKERS:-1}"

mkdir -p "$RUN_DIR" "$LOG_DIR"
chmod 700 "$VAR_DIR" "$RUN_DIR" "$LOG_DIR" 2>/dev/null || true

_alive() { [[ -f "$1" ]] && kill -0 "$(cat "$1")" 2>/dev/null; }

_spawn() { # name pidfile command...
  local name="$1" pidfile="$2"; shift 2
  if _alive "$pidfile"; then echo "$name déjà actif (pid $(cat "$pidfile"))"; return 0; fi
  nohup "$@" >>"$LOG_DIR/$name.log" 2>&1 &
  echo $! >"$pidfile"
  echo "$name démarré (pid $(cat "$pidfile"))"
}

_stop() { # name pidfile
  local name="$1" pidfile="$2"
  if ! _alive "$pidfile"; then echo "$name arrêté"; rm -f "$pidfile"; return 0; fi
  local pid; pid="$(cat "$pidfile")"
  kill -TERM "$pid" 2>/dev/null || true
  for _ in $(seq 1 30); do _alive "$pidfile" || break; sleep 0.5; done
  if _alive "$pidfile"; then echo "$name ne s'est pas arrêté proprement (pid $pid) — SIGKILL refusé par ce script"; return 1; fi
  rm -f "$pidfile"; echo "$name arrêté proprement"
}

case "${1:-status}" in
  start)
    "$PYTHON" -m supreme catalog --check >/dev/null
    "$PYTHON" -m supreme sync >/dev/null
    _spawn api "$PID_API" "$PYTHON" -m supreme serve --port "$PORT" --host "$BIND"
    for i in $(seq 1 "$WORKERS"); do
      _spawn "worker$i" "$RUN_DIR/worker$i.pid" "$PYTHON" -m supreme worker \
        --interval 1 --lease-seconds 30 --heartbeat-seconds 5 --worker-id "svc-worker-$i"
    done
    _spawn learn "$PID_LEARN" "$PYTHON" -m supreme learn --periodic --interval 900 \
      --lease-seconds 60 --heartbeat-seconds 10 --scheduler-id service
    _spawn guardian "$PID_GUARDIAN" "$PYTHON" -m supreme guardian --periodic --interval 900 \
      --lease-seconds 60 --heartbeat-seconds 10 --scheduler-id service
    echo "Liaison : $BIND:$PORT (local par défaut ; aucune exposition publique)"
    ;;
  stop)
    _stop guardian "$PID_GUARDIAN" || true
    _stop learn "$PID_LEARN" || true
    for f in "$RUN_DIR"/worker*.pid; do [[ -e "$f" ]] || continue; _stop "$(basename "$f" .pid)" "$f" || true; done
    _stop api "$PID_API" || true
    ;;
  status)
    for pair in "api:$PID_API" "worker:$PID_WORKER" "learn:$PID_LEARN" "guardian:$PID_GUARDIAN"; do
      name="${pair%%:*}"; pidfile="${pair#*:}"
      if _alive "$pidfile"; then echo "$name: actif (pid $(cat "$pidfile"))"; else echo "$name: arrêté"; fi
    done
    for f in "$RUN_DIR"/worker*.pid; do
      [[ -e "$f" ]] || continue
      if _alive "$f"; then echo "$(basename "$f" .pid): actif (pid $(cat "$f"))"; fi
    done
    "$PYTHON" -m supreme status
    ;;
  backup)
    "$PYTHON" -m supreme backup
    ;;
  restore)
    [[ -n "${2:-}" ]] || { echo "usage: $0 restore <backup_id> [CONFIRMER RESTAURATION]"; exit 2; }
    [[ "${3:-}" == "CONFIRMER RESTAURATION" ]] || { echo "Restauration = écrasement. Ajoutez 'CONFIRMER RESTAURATION'. Une sauvegarde de sécurité sera créée."; exit 2; }
    "$PYTHON" - "$2" <<'PY'
import sys
from supreme.backup import BackupManager
print(BackupManager().restore(sys.argv[1]))
PY
    ;;
  verify)
    "$PYTHON" -m supreme catalog --check
    "$PYTHON" -m supreme audit
    "$PYTHON" -m supreme guardian
    ;;
  logs)
    tail -n 50 "$LOG_DIR"/*.log 2>/dev/null || echo "aucun journal"
    ;;
  install-units)
    # Unités systemd utilisateur (sans root). Aucun démarrage automatique ici.
    target="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
    mkdir -p "$target"
    for unit in ops/systemd/*.service ops/systemd/*.timer; do
      sed -e "s|@FRAMEWORK@|$HERE|g" -e "s|@PYTHON@|$PYTHON|g" "$unit" >"$target/$(basename "$unit")"
      echo "installé : $target/$(basename "$unit")"
    done
    echo "Activer ensuite manuellement : systemctl --user daemon-reload && systemctl --user enable --now supreme-api.service supreme-worker@1.service supreme-learn.service supreme-guardian.service supreme-backup.timer"
    ;;
  *)
    echo "usage: $0 {start|stop|status|backup|restore|verify|logs|install-units}"; exit 2
    ;;
esac
