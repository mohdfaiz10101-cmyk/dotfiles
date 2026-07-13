{ pkgs ? import <nixpkgs> {} }:
{ inherit (pkgs) git ripgrep fd bat eza fzf zoxide neovim tmux; }
