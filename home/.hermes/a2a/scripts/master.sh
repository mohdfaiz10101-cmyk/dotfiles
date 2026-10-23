#!/usr/bin/env bash
set -euo pipefail
BASE="${A2A_HOME:-$HOME/.hermes/a2a}"
SCRIPT="$BASE/scripts"
cmd="${1:-help}"
shift || true

case "$cmd" in
  distill)
    python3 "$SCRIPT/distill.py" "$@"
    ;;
  rooms)
    python3 "$SCRIPT/sync-rooms.py" "$@"
    ;;
  list)
    python3 "$SCRIPT/approve.py" list "$@"
    ;;
  approve)
    python3 "$SCRIPT/approve.py" approve "$@"
    ;;
  reject)
    python3 "$SCRIPT/approve.py" reject "$@"
    ;;
  sync)
    python3 "$SCRIPT/sync.py" "$@"
    ;;
  skills)
    python3 "$SCRIPT/skill-change.py" "$@"
    ;;
  ask)
    python3 "$SCRIPT/ask.py" "$@"
    ;;
  status)
    python3 - <<'PY'
from pathlib import Path
from datetime import datetime, timezone
BASE = Path(__import__('os').environ.get('A2A_HOME', Path.home() / '.hermes/a2a'))
QUEUE = BASE / 'queue'
print('# A2A Status')
print()
for status in ['pending', 'approved', 'rejected', 'synced']:
    target = QUEUE / status
    if not target.exists():
        continue
    total = sum(1 for f in target.rglob('*.json') if f.is_file())
    print(f'## {status.upper()}: {total} items')
    for room_dir in sorted([d for d in target.iterdir() if d.is_dir()]):
        count = sum(1 for f in room_dir.iterdir() if f.suffix == '.json')
        if count:
            print(f'  {room_dir.name}: {count}')
    print()
for name in ['.last-scan', '.last-skill-scan']:
    p = QUEUE / name
    if p.exists():
        ts = float(p.read_text().strip() or '0')
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        print(f'## {name}: {dt}')
    else:
        print(f'## {name}: never')
print()
PY
    ;;
  summary)
    python3 - <<'PY'
from pathlib import Path
from datetime import datetime, timezone
BASE = Path(__import__('os').environ.get('A2A_HOME', Path.home() / '.hermes/a2a'))
KNOWLEDGE = BASE / 'knowledge'
today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
print(f'# A2A Master Summary - {today}\n')
for room_dir in sorted(KNOWLEDGE.iterdir()):
    if not room_dir.is_dir():
        continue
    kfile = room_dir / f'{today}.md'
    if not kfile.exists():
        print(f'## {room_dir.name}: no updates today')
        continue
    text = kfile.read_text()
    lines = [l for l in text.splitlines() if l.startswith('## [')]
    print(f'## {room_dir.name}: {len(lines)} updates')
    for l in lines[:8]:
        print(f'  {l}')
    print()
PY
    ;;
  *)
    cat <<'USAGE'
Usage: a2a {distill|list|approve|reject|sync|skills|ask|status|summary} [args]

  distill [--room <room>] [--since-hours 24]
  list [--room <room>]
  approve <id>
  reject <id> [--reason "..."]
  sync [--room <room>]
  skills
  ask <query> [--room <room>]
  status
  summary

Examples:
  a2a distill --room ops --since-hours 24
  a2a list --room coding
  a2a approve abc123
  a2a sync --room creative
  a2a ask "DuckDNS"
  a2a status
USAGE
    exit 1
    ;;
esac
