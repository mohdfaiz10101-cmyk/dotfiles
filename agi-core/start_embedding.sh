#!/run/current-system/sw/bin/bash
# Source shell profile to get PYTHONPATH from NixOS
# Only source .zshrc PYTHONPATH export logic
export HOME=/home/charlie
source <(grep -A5 'PYTHONPATH' /home/charlie/.zshrc 2>/dev/null | grep 'export PYTHONPATH')
exec /home/charlie/agi/.venv/bin/python3 /home/charlie/dotfiles/agi-core/embedding_server.py
