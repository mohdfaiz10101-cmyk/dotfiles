{ config, pkgs, lib, ... }:
{ home.username = "charlie"; home.homeDirectory = "/home/charlie"; home.packages = with pkgs; [ steam-run lutris obs-studio virt-manager ]; programs.git.userName = "Charlie"; programs.git.userEmail = "charlie@desktop.local"; }
