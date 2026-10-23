#!/usr/bin/env bash
set -euo pipefail
SKILL_DIR="${HERMES_HOME:-$HOME/.hermes}/skills/default-model-step-router"
VERIFY="${SKILL_DIR}/scripts/verify-default-model.sh"
LOCK="${SKILL_DIR}/scripts/lock-default-model.sh"

if ! bash "$VERIFY"; then
  echo "DRIFT DETECTED: auto-locking default model to step-router-v1"
  bash "$LOCK"
  bash "$VERIFY" || true
fi
