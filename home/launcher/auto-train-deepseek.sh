#!/usr/bin/env bash
# DeepSeek 自动训练脚本
# 定期从 lessons-learned.md 提取 Sonnet 案例并训练 LoRA

set -euo pipefail

LOG_FILE="/mnt/ai/tmp-nixbuild/deepseek-auto-train.log"
LOCK_FILE="/tmp/deepseek-training.lock"
MIN_SAMPLES=50
ADAPTER_DIR="/mnt/ai/deepseek-lora-adapters"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# 检查锁文件（防止重复训练）
if [ -f "$LOCK_FILE" ]; then
    log "训练正在进行中，跳过"
    exit 0
fi

trap "rm -f $LOCK_FILE" EXIT
touch "$LOCK_FILE"

log "=== 开始自动训练检查 ==="

# 1. 统计 Sonnet 案例数量
SONNET_CASES=$(grep -c "\[Sonnet\]" ~/.claude/projects/-home-charlie/memory/lessons-learned.md 2>/dev/null || echo "0")
log "当前 Sonnet 案例数：$SONNET_CASES"

if [ "$SONNET_CASES" -lt "$MIN_SAMPLES" ]; then
    log "案例不足（需要 ≥$MIN_SAMPLES），跳过训练"
    exit 0
fi

# 2. 检查是否有新案例（与上次训练对比）
LAST_TRAIN_COUNT=$(cat "$ADAPTER_DIR/last_train_count.txt" 2>/dev/null || echo "0")
NEW_CASES=$((SONNET_CASES - LAST_TRAIN_COUNT))

if [ "$NEW_CASES" -lt 10 ]; then
    log "新案例不足 10 个（当前 $NEW_CASES），跳过训练"
    exit 0
fi

log "发现 $NEW_CASES 个新案例，开始训练..."

# 3. 执行训练
cd /home/charlie/launcher
python3 deepseek-lora-training.py 2>&1 | tee -a "$LOG_FILE"

if [ $? -eq 0 ]; then
    log "✓ 训练完成"
    echo "$SONNET_CASES" > "$ADAPTER_DIR/last_train_count.txt"

    # 4. 自动部署到 LiteLLM
    log "部署 LoRA adapter 到 LiteLLM..."

    # 重启 LiteLLM 容器加载新 adapter
    cd /mnt/ai/ai-cluster/litellm
    docker compose restart litellm

    log "✓ 部署完成"

    # 5. 通知用户
    notify-send "DeepSeek 训练完成" "新增 $NEW_CASES 个案例，LoRA adapter 已更新" || true
else
    log "❌ 训练失败"
    exit 1
fi

log "=== 训练流程结束 ==="
