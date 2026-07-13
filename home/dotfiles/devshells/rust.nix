{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "dev-rust";
  buildInputs = with pkgs; [
    rustup pkg-config openssl cmake
  ];
  shellHook = ''
    echo "[dev] rust toolchain ready"
    echo "  run: rustup default stable"
  '';
}
