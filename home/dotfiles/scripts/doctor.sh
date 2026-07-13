#!/usr/bin/env bash
set -euo pipefail
echo "=== Dotfiles Doctor ==="

ok() { echo "  [OK] $1"; }
fail() { echo "  [FAIL] $1"; }

command -v nix &>/dev/null && ok "nix $(nix --version)" || fail "nix - run bootstrap-fedora.sh"
command -v home-manager &>/dev/null && ok "home-manager" || fail "home-manager - run apply-home.sh first"
nix flake show ~/dotfiles &>/dev/null 2>&1 && ok "flake valid" || fail "flake invalid"
command -v flatpak &>/dev/null && ok "flatpak $(flatpak --version)" || fail "flatpak"
[ -f ~/.ssh/id_ed25519 ] && ok "SSH key" || fail "SSH key missing - ssh-keygen -t ed25519"
git config --global user.name &>/dev/null && ok "git: $(git config --global user.name)" || fail "git config"
curl -s --connect-timeout 3 https://github.com &>/dev/null && ok "network OK" || fail "network - check proxy"
echo "Done."
