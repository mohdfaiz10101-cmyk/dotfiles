#!/usr/bin/env bash
set -u

PKG=/var/home/charlie/.nvm/versions/node/v23.11.1/lib/node_modules/hermes-web-ui/package.json
NPM_CACHE=/tmp/npm-cache

get_ver() {
  node -p "require(process.argv[1]).version" "$PKG"
}

CURRENT=$(get_ver)
if ! npm --cache "$NPM_CACHE" install -g hermes-web-ui@latest; then
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

NPM_LATEST=$(npm --cache "$NPM_CACHE" view hermes-web-ui@latest version)
RELEASE_INFO=$(curl -fsSL "https://api.github.com/repos/EKKOLearnAI/hermes-studio/releases/tags/v${NPM_LATEST}" || true)
RELEASE_TAG=$(printf '%s' "$RELEASE_INFO" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tag_name',''))" 2>/dev/null || true)
RELEASE_NAME=$(printf '%s' "$RELEASE_INFO" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('name',''))" 2>/dev/null || true)
RELEASE_BODY=$(printf '%s' "$RELEASE_INFO" | python3 -c "import sys,json; print((d.get('body','') or '')[:1000])" 2>/dev/null || true)

MSG="Hermes Studio $STATUS
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

printf '%s' "$MSG" | curl -fsSL -H 'Title: Hermes Studio 更新通知' --data-binary @- https://ntfy.sh/charlie-actions >/dev/null || true
