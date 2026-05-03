#!/run/current-system/sw/bin/bash
# Weekly system health check script
# Runs every Monday 8:00 via systemd user timer

REPORT="/home/charlie/health-report.txt"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Services to check (systemd user units)
USER_SERVICES=(unified-search hyperchat wechat-web launcher ollama xray litellm cockpit ttyd tailscaled syncthing)

# Ports to check
PORTS=(9000 9097 9098 9875 11434 4000 9090 7681 8384 47990)

# Disk usage warning threshold (%)
DISK_THRESHOLD=90

{
  echo "========================================"
  echo "  系统健康检查报告"
  echo "  生成时间: ${TIMESTAMP}"
  echo "========================================"
  echo ""

  # --- 1. 关键服务状态 ---
  echo "── 1. 关键服务状态 ──"
  echo ""
  for svc in "${USER_SERVICES[@]}"; do
    # Check user service first, fall back to system service
    status=$(systemctl --user is-active "${svc}.service" 2>/dev/null)
    if [[ "$status" == "active" ]]; then
      echo "  [OK]   ${svc}"
    else
      # Try system-level service
      sys_status=$(systemctl is-active "${svc}.service" 2>/dev/null)
      if [[ "$sys_status" == "active" ]]; then
        echo "  [OK]   ${svc} (system)"
      else
        echo "  [FAIL] ${svc} — 状态: ${status:-unknown}"
      fi
    fi
  done
  echo ""

  # --- 2. 磁盘空间 ---
  echo "── 2. 磁盘空间 ──"
  echo ""
  disk_warning=0
  while IFS= read -r line; do
    # Skip header
    if [[ "$line" == Filesystem* ]]; then
      echo "  ${line}"
      continue
    fi
    usage=$(echo "$line" | awk '{print $5}' | tr -d '%')
    if [[ -n "$usage" ]] && [[ "$usage" =~ ^[0-9]+$ ]] && (( usage >= DISK_THRESHOLD )); then
      echo "  [!!!] ${line}"
      disk_warning=1
    else
      echo "  ${line}"
    fi
  done < <(df -h --output=source,size,used,avail,pcent,target -x tmpfs -x devtmpfs -x efivarfs 2>/dev/null || df -h)
  if (( disk_warning )); then
    echo ""
    echo "  ⚠ 警告: 存在磁盘使用率超过 ${DISK_THRESHOLD}% 的分区！"
  fi
  echo ""

  # --- 3. 内存使用 ---
  echo "── 3. 内存使用 ──"
  echo ""
  free -h | while IFS= read -r line; do
    echo "  ${line}"
  done
  echo ""
  # Show top 5 memory consumers
  echo "  内存占用 Top 5 进程:"
  ps aux --sort=-%mem | head -6 | while IFS= read -r line; do
    echo "  ${line}"
  done
  echo ""

  # --- 4. 最近 Coredump ---
  echo "── 4. 最近 Coredump ──"
  echo ""
  coredumps=$(coredumpctl list --no-pager --since "7 days ago" 2>/dev/null)
  if [[ -z "$coredumps" ]]; then
    echo "  最近 7 天无 coredump 记录"
  else
    echo "$coredumps" | head -20 | while IFS= read -r line; do
      echo "  ${line}"
    done
    total=$(echo "$coredumps" | tail -n +2 | wc -l)
    if (( total > 20 )); then
      echo "  ... 共 ${total} 条，仅显示前 20 条"
    fi
  fi
  echo ""

  # --- 5. Docker 容器状态 ---
  echo "── 5. Docker 容器状态 ──"
  echo ""
  if command -v docker &>/dev/null; then
    containers=$(docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null)
    if [[ -z "$containers" ]]; then
      echo "  无运行中的 Docker 容器"
    else
      echo "$containers" | while IFS= read -r line; do
        echo "  ${line}"
      done
    fi
  else
    echo "  Docker 未安装或不可用"
  fi
  echo ""

  # --- 6. 端口监听检查 ---
  echo "── 6. 端口监听检查 ──"
  echo ""
  for port in "${PORTS[@]}"; do
    if ss -tlnp 2>/dev/null | grep -q ":${port} "; then
      proc=$(ss -tlnp 2>/dev/null | grep ":${port} " | awk '{print $NF}' | head -1)
      echo "  [OK]   端口 ${port} — ${proc}"
    else
      echo "  [FAIL] 端口 ${port} — 未监听"
    fi
  done
  echo ""

  # --- Summary ---
  echo "========================================"
  echo "  检查完成 — ${TIMESTAMP}"
  echo "========================================"

} > "${REPORT}" 2>&1

echo "健康检查完成，报告已写入 ${REPORT}"
