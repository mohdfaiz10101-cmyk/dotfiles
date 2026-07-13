{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "dev-base";
  buildInputs = with pkgs; [
    git jq yq-go ripgrep fd bat
    gnumake gcc pkg-config openssl
  ];
  shellHook = ''
    echo "[dev] base shell ready"
  '';
}
