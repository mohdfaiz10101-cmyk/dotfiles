{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "dev-node";
  buildInputs = with pkgs; [
    nodejs_22 nodePackages.pnpm
    nodePackages.typescript
    nodePackages.typescript-language-server
    nodePackages.prettier
    nodePackages.eslint
  ];
  shellHook = ''
    echo "[dev] node $(node --version)"
  '';
}
