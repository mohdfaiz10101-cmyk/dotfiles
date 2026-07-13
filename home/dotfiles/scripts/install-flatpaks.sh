#!/usr/bin/env bash
set -euo pipefail
LIST="$(dirname "$0")/../flatpak/apps.txt"
[ -f "$LIST" ] || { echo "ERROR: $LIST not found"; exit 1; }
echo "Installing Flatpak applications..."
while IFS= read -r app; do
  [[ "$app" =~ ^# ]] && continue
  [[ -z "$app" ]] && continue
  echo "  $app"
  flatpak install -y flathub "$app" 2>/dev/null || echo "    [SKIP]"
done < "$LIST"
echo "Done."
