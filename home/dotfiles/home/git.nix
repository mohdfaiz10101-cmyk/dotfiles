{ config, pkgs, lib, ... }:
{
  programs.git = {
    enable = true;
    userName = "Charlie";
    userEmail = "charlie@example.com";
    extraConfig = {
      init.defaultBranch = "main"; pull.rebase = true;
      push.autoSetupRemote = true; core.editor = "nvim";
    };
    aliases = {
      st = "status"; ad = "add ."; br = "branch"; co = "checkout";
      lg = "log --oneline --graph --all -20"; last = "log -1 HEAD";
      unstage = "reset HEAD --";
      amend = "commit --amend --no-edit";
    };
    ignores = [".DS_Store" "*.swp" "*.swo" "result" "result-*"];
  };
}
