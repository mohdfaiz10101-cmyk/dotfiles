#!/usr/bin/env bash
# CC Switch GUI launcher for NixOS (AppImage needs appimage-run)
exec appimage-run /home/charlie/.local/bin/cc-switch "$@"
