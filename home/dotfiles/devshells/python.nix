{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "dev-python";
  buildInputs = with pkgs; [
    python313 python313Packages.pip
    python313Packages.virtualenv
    python313Packages.ipython
    python313Packages.black
    python313Packages.ruff
    python313Packages.mypy
    python313Packages.requests
    python313Packages.anthropic
  ];
  shellHook = ''
    echo "[dev] python $(python3 --version)"
  '';
}
