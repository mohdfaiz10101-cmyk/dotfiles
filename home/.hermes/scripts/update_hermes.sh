#!/usr/bin/env bash
set -u

PYTHON=/usr/bin/python3

get_ver() {
  $PYTHON -m pip show hermes-agent | grep -i '^Version:' | awk '{print $2}'
}

CURRENT=$(get_ver)
if ! $PYTHON -m pip install --upgrade hermes-agent; then
  NEW=$(get_ver)
  STATUS='更新失败'
else
  NEW=$(get_ver)
  if [ "$CURRENT" = "$NEW" ]; then
    STATUS='已是最新版本'
  else
    STATUS='更新完成'
  fi
fi

RELEASE_INFO=$(curl -fsSL https://api.github.com/repos/NousResearch/hermes-agent/releases/latest || true)
RELEASE_TAG=$(printf '%s' "$RELEASE_INFO" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tag_name',''))" 2>/dev/null || true)
RELEASE_NAME=$(printf '%s' "$RELEASE_INFO" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('name',''))" 2>/dev/null || true)
RELEASE_BODY=$(printf '%s' "$RELEASE_INFO" | python3 -c "import sys,json; print((d.get('body','') or '')[:1000])" 2>/dev/null || true)

MSG="Hermes Agent $STATUS
版本: $CURRENT -> $NEW"
if [ -n "${RELEASE_TAG:-}" ]; then
  MSG="${MSG}
Release: ${RELEASE_TAG}"
fi
if [ -n "${RELEASE_NAME:-}" ]; then
  MSG="${MSG}
${RELEASE_NAME}"
fi
if [ -n "${RELEASE_BODY:-}" ]; then
  MSG="${MSG}

更新内容:
${RELEASE_BODY}"
fi

printf '%s' "$MSG" | curl -fsSL -H 'Title: Hermes 更新通知' --data-binary @- https://ntfy.sh/charlie-actions >/dev/null || true

# Restore local overrides that may be reset during Hermes upgrades.
if [ -x "${HOME}/.hermes/scripts/ensure_hermes_overrides.sh" ]; then
  "${HOME}/.hermes/scripts/ensure_hermes_overrides.sh" || true
fi
