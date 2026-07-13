{ config, pkgs, lib, ... }:
{ home.username = "charlie"; home.homeDirectory = "/home/charlie"; home.packages = with pkgs; [ powertop acpi ]; programs.git.userName = "Charlie"; programs.git.userEmail = "charlie@laptop.local"; }
