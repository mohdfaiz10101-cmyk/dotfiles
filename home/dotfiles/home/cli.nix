{ config, pkgs, lib, ... }:
{
  home.packages = with pkgs; [
    fd ripgrep bat eza fzf zoxide tmux btop ncdu du-dust
    procs bandwhich rsync unzip p7zip nmap mtr iperf3 socat
  ];

  programs.tmux = {
    enable = true;
    extraConfig = "set -g mouse on\nset -g status-interval 1\nbind | split-window -h\nbind - split-window -v\nbind S setw synchronize-panes";
    terminal = "screen-256color";
  };

  programs.zoxide = { enable = true; enableZshIntegration = true; };
  programs.fzf = { enable = true; enableZshIntegration = true; };
  programs.bat = { enable = true; config.theme = "Catppuccin-mocha"; };

  programs.zsh.shellAliases = {
    ls = "eza --icons --group-directories-first";
    ll = "eza -l --icons --group-directories-first";
    la = "eza -la --icons --group-directories-first";
    lt = "eza --tree --level=2 --icons";
  };
}
