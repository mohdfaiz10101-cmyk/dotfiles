{
  description = "Fedora portable user environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    home-manager.url = "github:nix-community/home-manager";
    home-manager.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, home-manager, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
    in {
      homeConfigurations = {
        "fedora-laptop" = home-manager.lib.homeManagerConfiguration {
          inherit pkgs;
          modules = [
            ./home/common.nix ./home/cli.nix ./home/shell.nix
            ./home/git.nix ./home/ssh.nix ./home/editors.nix
            ./home/desktop.nix ./hosts/fedora-laptop.nix
          ];
        };
        "fedora-desktop" = home-manager.lib.homeManagerConfiguration {
          inherit pkgs;
          modules = [
            ./home/common.nix ./home/cli.nix ./home/shell.nix
            ./home/git.nix ./home/ssh.nix ./home/editors.nix
            ./home/desktop.nix ./hosts/fedora-desktop.nix
          ];
        };
        "vm" = home-manager.lib.homeManagerConfiguration {
          inherit pkgs;
          modules = [
            ./home/common.nix ./home/cli.nix ./home/shell.nix
            ./home/git.nix ./home/ssh.nix ./home/editors.nix
            ./hosts/vm.nix
          ];
        };
      };
      devShells.${system} = {
        default = import ./devshells/base.nix { inherit pkgs; };
        node = import ./devshells/node.nix { inherit pkgs; };
        python = import ./devshells/python.nix { inherit pkgs; };
        rust = import ./devshells/rust.nix { inherit pkgs; };
      };
      packages.${system}.default = import ./packages/default.nix { inherit pkgs; };
    };
}
