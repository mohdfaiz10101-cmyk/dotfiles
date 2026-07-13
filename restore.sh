#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---dry-run}"
TARGET_HOME="${TARGET_HOME:-$HOME}"

case "$MODE" in
  --dry-run|--apply) ;;
  *) echo "usage: $0 [--dry-run|--apply]" >&2; exit 2 ;;
esac

copy_tree() {
  local src="$1" dst="$2"
  [ -e "$src" ] || return 0
  if [ "$MODE" = "--dry-run" ]; then
    printf '[dry-run] rsync %s -> %s\n' "$src" "$dst"
  else
    mkdir -p "$(dirname "$dst")"
    rsync -a "$src" "$dst"
  fi
}

copy_tree home/ "$TARGET_HOME/"

cat <<MSG
Restore mode: $MODE

User files were restored into: $TARGET_HOME

Next manual steps:
- Install packages from manifest/packages.txt with rpmi where suitable.
- Install Flatpaks from manifest/flatpaks.txt.
- Review manifest/systemd-user-units.txt before enabling user services.
- Recreate secrets manually: SSH private keys, GitHub auth, Codex auth.json,
  browser sessions, OAuth tokens, API keys, and local service env files.
MSG
