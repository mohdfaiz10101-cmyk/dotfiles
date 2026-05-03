#!/usr/bin/env bash
# 智能路由脚本（2026 社区最佳实践）
# 自动选择最佳模型：DeepSeek > GLM > Claude

PROMPT="$1"

# 检测任务类型
detect_task_type() {
    local prompt="$1"

    # 架构设计关键词
    if echo "$prompt" | grep -qiE "架构|设计|方案对比|技术选型|security|architecture"; then
        echo "architecture"
        return
    fi

    # 代码关键词
    if echo "$prompt" | grep -qiE "代码|code|编程|函数|debug|bug|algorithm|实现"; then
        echo "code"
        return
    fi

    # 中文对话关键词
    if echo "$prompt" | grep -qE "[\u4e00-\u9fa5]{5,}"; then
        echo "chinese"
        return
    fi

    # 默认：通用任务
    echo "general"
}

TASK_TYPE=$(detect_task_type "$PROMPT")

case $TASK_TYPE in
    architecture)
        echo "[路由] 架构设计 → Claude Opus（最强推理）" >&2
        MODEL="claude-opus-4.6"
        ;;
    code)
        echo "[路由] 代码任务 → DeepSeek V3.2（代码专家，便宜10倍）" >&2
        bash ~/launcher/ds-sonnet-mode.sh "$PROMPT"
        exit 0
        ;;
    chinese)
        echo "[路由] 中文对话 → GLM-4-Flash（免费）" >&2
        glm "$PROMPT"
        exit 0
        ;;
    general)
        echo "[路由] 通用任务 → DeepSeek V3.2（性价比最高）" >&2
        bash ~/launcher/ds-sonnet-mode.sh "$PROMPT"
        exit 0
        ;;
esac

# Fallback：调用 Claude
claude --model opus "$PROMPT"
