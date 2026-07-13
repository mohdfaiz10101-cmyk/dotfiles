{ config, pkgs, lib, ... }:
{ fonts.fontconfig.enable = true; home.packages = with pkgs; [ nerd-fonts.hack nerd-fonts.fira-code nerd-fonts.jetbrains-mono noto-fonts noto-fonts-cjk-sans noto-fonts-cjk-serif noto-fonts-color-emoji maple-mono.NF-CN ]; }
