#!/usr/bin/env bash
set -euo pipefail
BASE="/var/home/charlie/phone-sync"
SCRIPTS="$BASE/scripts"
LOGDIR="$BASE/logs"
mkdir -p "$LOGDIR"
LOG="$LOGDIR/run-sync.log"
log() { printf '%s %s\n' "$(date '+%F %T')" "$*" >> "$LOG"; }
log "sync start"
PULLED="$($SCRIPTS/pull_phone_latest.sh 2>>"$LOG")" || { log "pull failed"; exit 1; }
log "pulled $PULLED"
python3 "$SCRIPTS/import_phone_snapshots.py" >> "$LOG" 2>&1
python3 "$SCRIPTS/detect_package_changes.py" >> "$LOG" 2>&1 || true
log "sync done"
printf '%s\n' "$PULLED"
