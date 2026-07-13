{ config, pkgs, lib, ... }:
{
  home.stateVersion = "25.05";
  home.packages = with pkgs; [
    curl wget git htop fastfetch jq yq-go rclone restic
    wl-clipboard translate-shell pandoc
    nerd-fonts.hack noto-fonts noto-fonts-cjk-sans
    noto-fonts-cjk-serif noto-fonts-color-emoji maple-mono.NF-CN
  ];
  programs.direnv.enable = true;
  programs.direnv.nix-direnv.enable = true;
  programs.mpv.enable = true;
  programs.gpg.enable = true;
  services.gpg-agent.enable = true;
  services.gpg-agent.pinentryPackage = pkgs.pinentry-gtk2;
  services.gpg-agent.enableSshSupport = true;
}
