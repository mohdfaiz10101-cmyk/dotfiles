# Migration Map: NixOS -> Fedora

| NixOS Source | Fedora Target | Type |
|---|---|---|
| modules/git.nix | home/git.nix | Home Manager |
| users.nix (zsh/alias) | home/shell.nix | Home Manager |
| users.nix (tmux) | home/cli.nix | Home Manager |
| packages.nix (CLI) | home/cli.nix | Home Manager |
| packages.nix (editors) | home/editors.nix | Home Manager |
| packages.nix (fonts) | home/common.nix | Home Manager |
| charlie.nix (Hyprland) | home/desktop.nix | Home Manager |
| charlie.nix (Kitty) | home/desktop.nix | Home Manager |
| packages.nix (browsers) | flatpak/apps.txt | Flatpak |
| packages.nix (Telegram) | flatpak/apps.txt | Flatpak |
| packages.nix (VSCode) | flatpak/apps.txt | Flatpak |
| desktop.nix (NVIDIA) | fedora/system-notes.md | Fedora native |
| networking.nix (firewall) | fedora/system-notes.md | Fedora native |
| virtualization.nix (Docker) | fedora/system-notes.md | Fedora native |
| storage.nix (fstab) | fedora/system-notes.md | Fedora native |
| boot.nix | N/A | Drop |
| nixos-ai-guard.nix | N/A | Drop |
