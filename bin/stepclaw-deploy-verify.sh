#!/usr/bin/env bash
# StepClaw × OpenCode 部署验证（2026-05-12）

echo "=== FRP 通道验证 ==="
for port in 19890 19891 19892; do
    code=$(curl -s --connect-timeout 3 -o /dev/null -w "%{http_code}" "http://100.91.93.99:$port")
    echo "  100.91.93.99:$port → HTTP $code"
done

echo ""
echo "=== 本地服务验证 ==="
for port in 8080 9800 8283; do
    code=$(curl -s --connect-timeout 2 -o /dev/null -w "%{http_code}" "http://127.0.0.1:$port")
    echo "  127.0.0.1:$port → HTTP $code"
done

echo ""
echo "=== FRP 代理状态 ==="
journalctl --user -u frpc --since "2 min ago" 2>/dev/null | grep "proxy added\|start proxy success" | tail -8

echo ""
echo "=== 同步脚本 ==="
ls -la ~/bin/ai-config-sync-*.sh

echo ""
echo "=== systemd timer ==="
systemctl --user is-active ai-config-sync-pull.timer

echo ""
echo "=== GitHub 仓库 ==="
cd ~/ai-config-sync && git remote -v 2>/dev/null || echo "  未配置远程仓库（需要运行: gh repo create 或设置 GITHUB_TOKEN）"

echo ""
echo "=== 完成 ==="
