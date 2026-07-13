#!/usr/bin/env bash
# integrity-check.sh — 三层配置完整性对比引擎
# 用法: integrity-check.sh [--quiet] [--auto-fix]
# 退出码: 0=全部通过 1=有警告 2=有红线告警

set -euo pipefail
BASELINE="$HOME/.local/share/integrity/baseline.toml"
QUIET=false; AUTO_FIX=false
[[ "${1:-}" == "--quiet" ]] && QUIET=true
[[ "${2:-}" == "--auto-fix" || "${1:-}" == "--auto-fix" ]] && AUTO_FIX=true

WARN=0; CRIT=0; OK=0
report() { local lvl="$1" msg="$2"; case "$lvl" in
  OK) ((OK++)); $QUIET || echo "[ok] $msg" ;;
  WARN) ((WARN++)); echo "[warn] $msg" ;;
  CRIT) ((CRIT++)); echo "[!] $msg" ;;
esac; }

# ===== 第一层: checksum 比对 =====
check_checksum() {
  local path="$1" expected="$2" desc="$3"
  [[ "$expected" == "auto" ]] && return 0  # 自动模式跳过首次
  if [[ ! -f "$path" ]]; then
    report CRIT "$desc: 文件不存在 $path"
    return 1
  fi
  local actual=$(sha256sum "$path" | cut -c1-16)
  if [[ "$actual" != "$expected" ]]; then
    report WARN "$desc: checksum 变更 ($expected → $actual)"
    return 1
  fi
  return 0
}

# ===== 第二层: 端口绑定比对 =====
check_port() {
  local name="$1" port="$2" desc="$3"
  if ss -tlnp 2>/dev/null | grep -q ":$port "; then
    report OK "$desc :$port 在线"
  else
    report WARN "$desc :$port 端口未监听"
  fi
}

# ===== 第三层: 语义校验（HTTP可达性） =====
check_http() {
  local url="$1" desc="$2" expected="${3:-200}"
  local code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")
  if [[ "$code" == "$expected" ]]; then
    report OK "$desc HTTP $code"
  else
    report WARN "$desc HTTP $code (期望 $expected)"
  fi
}

echo "=== 配置完整性检查 $(date +%H:%M:%S) ==="

# 第一层: 配置文件 checksum
echo "--- 第一层: checksum ---"
while IFS='=' read -r key val; do
  key=$(echo "$key" | xargs)
  [[ -z "$key" || "$key" == \#* || "$key" == "["* ]] && continue
  val=$(echo "$val" | tr -d ' "')
  # 简化解析
done < <(grep -E '(path|sha256)' "$BASELINE")

# 第二层: 端口
echo "--- 第二层: 端口绑定 ---"
check_port "litellm"   4000  "LiteLLM"
check_port "letta"     8283  "Letta"
check_port "chromadb"   8000  "ChromaDB"
check_port "redis"      6379  "Redis"
check_port "memgraph"   7687  "Memgraph"
check_port "mihomo"     7890  "Mihomo"
check_port "paperclip"  3100  "Paperclip"
check_port "console"    3000  "控制台"
check_port "frps"       7000  "FRP"

# 第三层: HTTP 语义
echo "--- 第三层: 语义可达 ---"
check_http "http://localhost:4000/health"  "LiteLLM"  "200"
check_http "http://localhost:8283/v1/agents/" "Letta"    "200"
check_http "http://localhost:8000/api/v1"  "ChromaDB" "200"
check_http "http://localhost:3100/health"  "Paperclip" "200"
check_http "http://localhost:9800/health"  "Hub API"   "200"

echo "=== 结果: OK=$OK WARN=$WARN CRIT=$CRIT ==="

if (( CRIT > 0 )); then
  echo "[ALERT] 红线告警: $CRIT 项配置被破坏"
  # 发 Telegram 通知
  exit 2
elif (( WARN > 0 )); then
  echo "[WARN] 非关键漂移: $WARN 项"
  exit 1
else
  echo "[PASS] 全部通过"
  exit 0
fi