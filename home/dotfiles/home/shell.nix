{ config, pkgs, lib, ... }:
{
  programs.zsh = {
    enable = true;
    autosuggestions.enable = true;
    syntaxHighlighting.enable = true;
    initExtraBeforeCompInit = "export PATH=\"$HOME/.local/bin:$PATH\"";
    shellAliases = {
      g = "git"; ga = "git add"; gc = "git commit"; gp = "git push";
      gl = "git log --oneline --graph -20"; gd = "git diff"; gs = "git status";
      nix-clean = "nix-collect-garbage -d";
      nix-update = "nix flake update ~/dotfiles";
      hm-switch = "home-manager switch --flake ~/dotfiles";
      ".." = "cd .."; "..." = "cd ../.."; c = "clear";
      cat = "bat --style=plain"; ports = "ss -tlnp";
      proxy-on = "export http_proxy=http://127.0.0.1:7890 https_proxy=http://127.0.0.1:7890";
      proxy-off = "unset http_proxy https_proxy";
    };
    history.size = 50000; history.save = 50000;
    history.ignoreDups = true; history.share = true;
  };

  programs.starship = {
    enable = true;
    settings = {
      add_newline = false;
      format = "$directory$git_branch$git_status$python$fill$time$line_break$character";
      character.success_symbol = "[>](bold green)";
      character.error_symbol = "[>](bold red)";
    };
  };

  programs.atuin = { enable = true; flags = [ "--disable-up-arrow" ]; };
}
