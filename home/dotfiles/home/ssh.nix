{ config, pkgs, lib, ... }:
{
  programs.ssh = {
    enable = true;
    matchBlocks = {
      "github.com" = { hostname = "github.com"; user = "git"; identityFile = "~/.ssh/id_ed25519"; };
      "*.tailscale" = { forwardAgent = true; compression = true; };
    };
    extraConfig = "Host *\n  ServerAliveInterval 60\n  ConnectTimeout 10\n  StrictHostKeyChecking accept-new";
  };
}
