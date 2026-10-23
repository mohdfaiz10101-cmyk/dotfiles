#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="${AIDER_OUT:-/tmp/aider-hermes-result.md}"
TASK_FILE="${AIDER_TASK_FILE:-${SCRIPT_DIR}/../workspace/aider-daily-task.txt}"

# Kill stale tmux session if exists
tmux kill-session -t aider-hermes 2>/dev/null || true

# Launch aider in background, don't wait for completion
nohup python3 "${SCRIPT_DIR}/aider-hermes.py" \
  --task-file "${TASK_FILE}" \
  --out "${OUT}" \
  > /tmp/aider-hermes-launch.log 2>&1 &

echo "aider launched in tmux, result will be at ${OUT}"
