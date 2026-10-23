#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_OUT="/tmp/aider-hermes-result.md"
DEFAULT_TASK="${SCRIPT_DIR}/../workspace/aider-daily-task.txt"
if [[ $# -eq 0 ]]; then
  if [[ -f "${DEFAULT_TASK}" ]]; then
    python3 "${SCRIPT_DIR}/aider-hermes.py" --task-file "${DEFAULT_TASK}" --out "${DEFAULT_OUT}"
  else
    python3 "${SCRIPT_DIR}/aider-hermes.py" --out "${DEFAULT_OUT}"
  fi
else
  python3 "${SCRIPT_DIR}/aider-hermes.py" "$@"
fi
