#!/usr/bin/env bash
set -euo pipefail
echo "=== Bootstrap Fedora User Environment ==="

echo "[1/4] Installing Fedora native dependencies..."
sudo dnf install -y git curl wget flatpak wl-clipboard gnupg2 zsh fd-find ripgrep bat fzf zoxide eza tmux neovim 2>/dev/null || echo "  Some packages may already be installed"

echo "[2/4] Installing Nix (single-user)..."
if ! command -v nix &>/dev/null; then
  curl -L https://nixos.org/nix/install | sh -s -- --no-daemon
  . "$HOME/.nix-profile/etc/profile.d/nix.sh"
else
  echo "  Nix already installed: $(nix --version)"
fi

echo "[3/4] Enabling flakes..."
mkdir -p ~/.config/nix
grep -q "experimental-features" ~/.config/nix/nix.conf 2>/dev/null || echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf

echo "[4/4] Bootstrap complete!"
echo ""
echo "Next steps:"
echo "  . ~/.nix-profile/etc/profile.d/nix.sh"
echo "  ./scripts/apply-home.sh fedora-laptop"
echo "  ./scripts/install-flatpaks.sh"
