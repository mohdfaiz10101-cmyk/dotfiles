#!/usr/bin/env bash
# ops-infra bootstrap.sh — 部署运维基础设施到新系统
# 用法: bash ~/dotfiles/ops-infra/bootstrap.sh

set -euo pipefail

OPS_INFRA="$HOME/dotfiles/ops-infra"
BIN_DIR="$HOME/.local/bin"
STATE_DIR="$HOME/.local/state/ops-infra"
SYSTEMD_DIR="$HOME/.config/systemd/user"

echo "=== ops-infra 部署 ==="
echo ""

# 1. 创建状态目录
mkdir -p "$STATE_DIR" "$BIN_DIR" "$SYSTEMD_DIR"

# 2. 部署核心脚本到 ~/.local/bin
echo "[1/4] 部署核心脚本..."

ln -sf "$OPS_INFRA/health/scorer.sh"   "$BIN_DIR/health-scorer"
ln -sf "$OPS_INFRA/runbook/engine.sh"  "$BIN_DIR/runbook-engine"
ln -sf "$OPS_INFRA/incident/reporter.sh" "$BIN_DIR/incident-reporter"

chmod +x "$OPS_INFRA/health/scorer.sh"
chmod +x "$OPS_INFRA/runbook/engine.sh"
chmod +x "$OPS_INFRA/incident/reporter.sh"

# 3. 部署systemd timer
echo "[2/4] 部署systemd timer..."

cat > "$SYSTEMD_DIR/health-scorer.service" << 'EOF'
[Unit]
Description=Ops-Infra 统一健康评分
After=network.target docker.service

[Service]
Type=oneshot
ExecStart=%h/.local/bin/health-scorer
StandardOutput=journal
Environment="PATH=/run/current-system/sw/bin:%h/.local/bin"
EOF

cat > "$SYSTEMD_DIR/health-scorer.timer" << 'EOF'
[Unit]
Description=统一健康评分定时器 (每15分钟)
After=network.target

[Timer]
OnCalendar=*:0/15
RandomizedDelaySec=30
Persistent=true

[Install]
WantedBy=timers.target
EOF

cat > "$SYSTEMD_DIR/runbook-engine.service" << 'EOF'
[Unit]
Description=Ops-Infra Runbook自愈引擎
After=network.target docker.service health-scorer.service

[Service]
Type=oneshot
ExecStart=%h/.local/bin/runbook-engine --dry-run
StandardOutput=journal
Environment="PATH=/run/current-system/sw/bin:%h/.local/bin"
EOF

cat > "$SYSTEMD_DIR/runbook-engine.timer" << 'EOF'
[Unit]
Description=Runbook自愈引擎定时器 (每30分钟)
After=network.target

[Timer]
OnCalendar=*:0/30
RandomizedDelaySec=60
Persistent=true

[Install]
WantedBy=timers.target
EOF

cat > "$SYSTEMD_DIR/incident-reporter.service" << 'EOF'
[Unit]
Description=Ops-Infra 每周故障报告
After=network.target

[Service]
Type=oneshot
ExecStart=%h/.local/bin/incident-reporter
StandardOutput=journal
Environment="PATH=/run/current-system/sw/bin:%h/.local/bin"
EOF

cat > "$SYSTEMD_DIR/incident-reporter.timer" << 'EOF'
[Unit]
Description=每周故障报告定时器 (周一 09:00)
After=network.target

[Timer]
OnCalendar=Mon *-*-* 09:00:00
RandomizedDelaySec=300
Persistent=true

[Install]
WantedBy=timers.target
EOF

# 4. 启用timer
echo "[3/4] 启用systemd timer..."
systemctl --user daemon-reload

for timer in health-scorer.timer runbook-engine.timer incident-reporter.timer; do
    systemctl --user enable --now "$timer" 2>/dev/null && echo "  ✅ $timer" || echo "  ⚠️ $timer (已有或失败)"
done

# 5. 验证
echo ""
echo "[4/4] 验证部署..."

echo "  核心脚本:"
for script in health-scorer runbook-engine incident-reporter; do
    if [ -x "$BIN_DIR/$script" ]; then
        echo "    ✅ $script"
    else
        echo "    ❌ $script 缺失"
    fi
done

echo "  定时器:"
systemctl --user list-timers --no-pager 2>/dev/null | grep -E "health-scorer|runbook-engine|incident-reporter" || echo "    (待首次触发)"

echo ""
echo "=== 部署完成 ==="
echo ""
echo "手动命令:"
echo "  health-scorer             # 即时健康评分"
echo "  runbook-engine --dry-run  # 预览自愈动作"
echo "  runbook-engine            # 执行自愈"
echo "  incident-reporter         # 生成周报"
echo ""
echo "新服务接入: 复制 ~/dotfiles/ops-infra/health/template.sh"