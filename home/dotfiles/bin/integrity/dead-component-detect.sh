#!/usr/bin/env bash
# dead-component-detect.sh — 全系统空壳检测
# 扫描: 端口→服务→实际功能→链路完整性
# 空壳定义: 端口在监听但 API 返回异常 / 服务 running 但实际不工作

set -euo pipefail
DEAD=0; ALIVE=0; SUSPECT=0

check() {
  local status="$1" name="$2" detail="$3"
  case "$status" in
    DEAD)  ((DEAD++));  echo "[DEAD]  $name — $detail" ;;
    ALIVE) ((ALIVE++)); ;;
    SUSPECT) ((SUSPECT++)); echo "[?]    $name — $detail" ;;
  esac
}

echo "=== 全系统空壳检测 $(date +%H:%M) ==="
echo ""

# ===== 1. 端口监听但无响应 =====
echo "--- 端口+API可达性 ---"
declare -A PROBES=(
  ["4000:LiteLLM"]="/health:200"
  ["8283:Letta"]="/v1/agents/:200"
  ["8000:ChromaDB"]="/api/v1:200"
  ["3100:Paperclip"]="/health:200"
  ["9800:Hub API"]="/health:200"
  ["9900:AGI GW"]="/health:200"
  ["3000:Console"]="/:200"
  ["6379:Redis"]="PING:+PONG"
  ["7890:Mihomo"]="/:200"
)

for entry in "${!PROBES[@]}"; do
  port="${entry%%:*}"
  name="${entry##*:}"
  spec="${PROBES[$entry]}"
  endpoint="${spec%%:*}"
  expected="${spec##*:}"
  
  if ! ss -tlnp 2>/dev/null | grep -q ":$port "; then
    check "DEAD" "$name" "端口 $port 未监听"
    continue
  fi
  
  case "$name" in
    Redis)
      resp=$(redis-cli -p "$port" PING 2>/dev/null || echo "FAIL")
      [[ "$resp" == "PONG" ]] && check "ALIVE" "$name" "PONG" || check "SUSPECT" "$name" "Redis无响应"
      ;;
    *)
      code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://localhost:${port}${endpoint}" 2>/dev/null || echo "000")
      if [[ "$code" == "$expected" || "$code" == "302" || "$code" == "301" ]]; then
        check "ALIVE" "$name" "HTTP $code"
      else
        check "SUSPECT" "$name" "端口监听但HTTP返回 $code (期望 $expected)"
      fi
      ;;
  esac
done

# ===== 2. systemd 服务状态 =====
echo ""
echo "--- systemd 服务状态 ---"
FAILED_SVC=$(systemctl --user list-units --state=failed --no-legend 2>/dev/null | wc -l)
if [[ "$FAILED_SVC" -gt 0 ]]; then
  systemctl --user list-units --state=failed --no-legend 2>/dev/null | while read -r line; do
    svc=$(echo "$line" | awk '{print $1}')
    check "DEAD" "$svc" "systemd服务失败"
  done
fi

# 检查关键服务
for svc in litellm.service letta.service agi-brain.service embedding-server.service; do
  if systemctl --user is-active "$svc" --quiet 2>/dev/null; then
    check "ALIVE" "$svc" "运行中"
  else
    check "DEAD" "$svc" "未运行"
  fi
done

# ===== 3. Docker 容器 =====
echo ""
echo "--- Docker 容器 ---"
docker ps --format "{{.Names}} {{.Status}} {{.Ports}}" 2>/dev/null | while read -r line; do
  name=$(echo "$line" | awk '{print $1}')
  status=$(echo "$line" | awk '{print $2}')
  if [[ "$status" == "Up" ]]; then
    check "ALIVE" "$name" "运行中"
  else
    check "DEAD" "$name" "$status"
  fi
done

# ===== 4. 已知死路径扫描 =====
echo ""
echo "--- 已知废弃端点 ---"
KNOWN_DEAD=(
  "7699:已废弃端口(StepClaw?)" 
)
for entry in "${KNOWN_DEAD[@]}"; do
  port="${entry%%:*}"
  desc="${entry##*:}"
  if ss -tlnp 2>/dev/null | grep -q ":$port "; then
    check "SUSPECT" "$desc" "端口仍在使用但已标记废弃"
  fi
done

# ===== 5. 前端面板后端检查 =====
echo ""
echo "--- 前端面板 → 后端链路 ---"
# Hub API 是否返回有效 JSON
hub_json=$(curl -s --max-time 3 "http://localhost:9800/api/op-tasks" 2>/dev/null || echo "")
if echo "$hub_json" | jq -e '.counts' >/dev/null 2>&1; then
  check "ALIVE" "Hub→op-tasks" "JSON有效"
else
  check "SUSPECT" "Hub→op-tasks" "返回无效JSON"
fi

# ===== 总结 =====
echo ""
echo "==========================================="
echo "结果: ALIVE=$ALIVE DEAD=$DEAD SUSPECT=$SUSPECT"
echo "==========================================="

if (( DEAD > 0 )); then
  echo ""
  echo "⚠️ 发现 $DEAD 个死组件需要处理:"
  echo "   1. disable 无效 systemd 服务"
  echo "   2. rm 废弃文件/端口占用"
  echo "   3. 清理 Docker 死容器"
fi

exit $DEAD