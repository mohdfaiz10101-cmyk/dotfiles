#!/usr/bin/env bash
# safe-rebuild.sh — 安全 NixOS rebuild，保护代理不中断
# 用法: ~/launcher/safe-rebuild.sh [额外的 nixos-rebuild 参数]

set -euo pipefail

FLAKE="/etc/nixos#charlie"
PROXY_TEST_URL="https://api.anthropic.com"
PROXY_ADDR="127.0.0.1:7890"

echo "=== 安全 Rebuild 流程 ==="

# Step 1: 检查当前代理状态
echo "[1/4] 检查代理连通性..."
if curl -sf -x http://${PROXY_ADDR} --connect-timeout 5 -o /dev/null ${PROXY_TEST_URL}; then
    echo "  [OK] 代理正常"
else
    echo "  [WARN] 代理当前不可用，继续 rebuild..."
fi

# Step 2: 记录当前活跃的代理服务
ACTIVE_PROXY=""
if systemctl is-active --quiet xray; then
    ACTIVE_PROXY="xray"
elif systemctl is-active --quiet mihomo; then
    ACTIVE_PROXY="mihomo"
fi
echo "[2/4] 当前代理服务: ${ACTIVE_PROXY:-none}"

# Step 3: 先 build 验证
echo "[3/4] 执行 nixos-rebuild build（不影响运行中的系统）..."
sudo nixos-rebuild build --flake ${FLAKE} "$@"
if [ $? -ne 0 ]; then
    echo "  [FAIL] Build 失败，中止操作"
    exit 1
fi
echo "  [OK] Build 成功"

# Step 4: 执行 switch
echo "[4/4] 执行 nixos-rebuild switch..."
sudo nixos-rebuild switch --flake ${FLAKE} "$@"
SWITCH_RC=$?

# Step 5: 验证代理（switch 后）
echo ""
echo "=== 验证 ==="

# 等待服务稳定
sleep 2

# 检查代理服务状态
if [ -n "$ACTIVE_PROXY" ]; then
    if systemctl is-active --quiet "$ACTIVE_PROXY"; then
        echo "[OK] ${ACTIVE_PROXY} 服务运行中"
    else
        echo "[WARN] ${ACTIVE_PROXY} 未运行，尝试恢复..."
        sudo systemctl start "$ACTIVE_PROXY"
        sleep 2
        if systemctl is-active --quiet "$ACTIVE_PROXY"; then
            echo "[OK] ${ACTIVE_PROXY} 恢复成功"
        else
            echo "[FAIL] ${ACTIVE_PROXY} 恢复失败！"
            echo "  手动修复: sudo systemctl status ${ACTIVE_PROXY}"
        fi
    fi
fi

# 检查端口
if ss -tlnp | grep -q ":7890"; then
    echo "[OK] 端口 7890 正常监听"
else
    echo "[FAIL] 端口 7890 未监听！"
fi

# 检查代理连通性
if curl -sf -x http://${PROXY_ADDR} --connect-timeout 10 -o /dev/null ${PROXY_TEST_URL}; then
    echo "[OK] 代理连通性正常 (anthropic.com 可达)"
else
    echo "[WARN] 代理连通性异常，Claude Code 可能需要重启"
    echo "  诊断: ~/launcher/glm-proxy-fix.sh"
fi

echo ""
echo "=== Rebuild 完成 (exit code: ${SWITCH_RC}) ==="
echo "提示: 代理配置变更需手动重启: sudo systemctl restart xray"

exit ${SWITCH_RC}
