#!/usr/bin/env bash
# letta-health-check.sh — Check Letta agent archival counts, auto-supplement from memory files
# Trigger: systemd timer every 6 hours
set -euo pipefail

LETTA_BASE="http://localhost:8283/v1"
LOG_PREFIX="[LETTA-HEALTH]"
MEMORY_DIR="$HOME/.claude/projects/-home-charlie/memory"

MIN_ARCHIVAL_SYSADMIN=50
MIN_ARCHIVAL_CODE=20

log() { echo "$LOG_PREFIX $(date '+%H:%M:%S') $*"; }

# Agent name -> ID mapping
AGENT_IDS=(
    "nixos-sysadmin:agent-8651643c-e753-47ed-9759-bd955c6ac240"
    "code-assistant:agent-02380eae-9ac2-45f4-b9b2-dabf40e0abea"
)

# Get archival memory count for an agent
get_archival_count() {
    local agent_id="$1"
    python3 -c "
import urllib.request, json
try:
    resp = urllib.request.urlopen('http://localhost:8283/v1/agents/$agent_id/archival-memory/', timeout=15)
    data = json.loads(resp.read().decode('utf-8', errors='replace'))
    print(len(data) if isinstance(data, list) else 0)
except Exception:
    print(0)
" 2>/dev/null
}

# Write one archival memory entry
write_archival() {
    local agent_id="$1"
    local content="$2"
    local tags="$3"
    # Escape content for JSON
    local escaped
    escaped=$(python3 -c "import json; print(json.dumps('$content'))" 2>/dev/null || echo '""')
    python3 -c "
import urllib.request, json
data = json.dumps({'content': '''$content''', 'tags': '$tags'.split(',')}).encode()
req = urllib.request.Request(
    'http://localhost:8283/v1/agents/$agent_id/archival-memory/',
    data=data,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    urllib.request.urlopen(req, timeout=15)
except Exception as e:
    print(f'写入失败: {e}')
" 2>/dev/null || true
}

# Dedup check: search existing archival for content overlap
already_exists() {
    local agent_id="$1"
    local keyword="$2"
    python3 -c "
import urllib.request, json
try:
    resp = urllib.request.urlopen('http://localhost:8283/v1/agents/$agent_id/archival-memory/', timeout=15)
    data = json.loads(resp.read().decode('utf-8', errors='replace'))
    for m in data:
        if '$keyword' in m.get('content', ''):
            print('yes')
            break
    else:
        print('no')
except Exception:
    print('no')
" 2>/dev/null
}

# --- Main ---

log "开始检查..."

if ! python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8283/v1/agents/', timeout=5)" 2>/dev/null; then
    log "Letta 不可用，退出"
    exit 1
fi

for entry in "${AGENT_IDS[@]}"; do
    IFS=':' read -r name agent_id <<< "$entry"

    count=$(get_archival_count "$agent_id")
    log "$name: ${count} 条"

    threshold=0
    source_file=""
    tag=""

    case "$name" in
        nixos-sysadmin)
            threshold=$MIN_ARCHIVAL_SYSADMIN
            source_file="$MEMORY_DIR/lessons-learned.md"
            tag="health-check,lessons-learned"
            ;;
        code-assistant)
            threshold=$MIN_ARCHIVAL_CODE
            source_file="$MEMORY_DIR/codebase-map.md"
            tag="health-check,codebase-map"
            ;;
    esac

    if [ "$count" -lt "$threshold" ] && [ -f "$source_file" ]; then
        log "$name 低于阈值 ($threshold)，补充中..."
        written=0
        while IFS= read -r line; do
            [ -z "$line" ] && continue
            [[ "$line" != "- "* ]] && continue
            # Extract first 20 chars as dedup keyword
            keyword="${line:2:30}"
            if [ "$(already_exists "$agent_id" "$keyword")" = "no" ]; then
                write_archival "$agent_id" "$line" "$tag"
                written=$((written + 1))
            fi
            [ "$written" -ge 20 ] && break
        done < <(tail -30 "$source_file" 2>/dev/null)
        log "$name 补充: ${written} 条"
    fi
done

log "检查完成"
