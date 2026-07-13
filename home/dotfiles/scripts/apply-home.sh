#!/usr/bin/env bash
set -euo pipefail
HOST="${1:-fedora-laptop}"
case "$HOST" in fedora-laptop|fedora-desktop|vm) ;; *) echo "Usage: $0 <fedora-laptop|fedora-desktop|vm>"; exit 1 ;; esac
echo "Applying Home Manager for host: $HOST"
cd "$(dirname "$0")/.."
. "$HOME/.nix-profile/etc/profile.d/nix.sh" 2>/dev/null || true
home-manager switch --flake ".#${HOST}"
echo "Done. Check: home-manager generations"
