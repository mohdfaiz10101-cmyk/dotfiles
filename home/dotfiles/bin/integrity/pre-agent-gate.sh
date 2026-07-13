#!/usr/bin/env bash
# pre-agent-gate.sh — Agent 启动前自动注入记忆上下文
# 集成到 opencode pre-agent hook
# 用法: pre-agent-gate.sh <agent_name>
# 输出: JSON 格式的记忆注入块，追加到 agent 系统提示词

set -euo pipefail
AGENT="${1:-unknown}"
RULES="$HOME/.local/share/integrity/gate-rules.yaml"
MEMORY_DIR="$HOME/.claude/projects/-home-charlie/memory"

# 从 gate-rules 查该 agent 需要注入哪些记忆域
get_domains() {
  grep -A1 "agent:.*${AGENT}" "$RULES" 2>/dev/null | grep "domains:" | cut -d: -f2- | tr ',' ' ' || echo "default"
}

# 检索相关记忆
recall_memory() {
  local domain="$1"
  case "$domain" in
    preferences)
      grep "^\[preferences\]" -A20 "$HOME/.local/share/integrity/baseline.toml" 2>/dev/null | grep "=" | head -10
      ;;
    lessons)
      tail -30 "$MEMORY_DIR/lessons-learned.md" 2>/dev/null | grep "^\- \[" | head -5
      ;;
    infrastructure)
      echo "关键端口: LiteLLM:4000, Letta:8283, ChromaDB:8000"
      echo "代理: mihomo:7890/7891, GLOBAL=自动选择"
      ;;
    constraints)
      cat "$HOME/.local/share/integrity/baseline.toml" 2>/dev/null | grep -A2 "^\[constraints" | head -10
      ;;
    *)
      echo "Charlie偏好: USB线在Windows, 不再委派CC, 所有操作立刻生效"
      ;;
  esac
}

OUTPUT=""
OUTPUT+="## 已知上下文 (自动注入)\n"
OUTPUT+="> 以下来自 memory gate，agent 不需要自己查记忆\n\n"

# 始终注入关键偏好
OUTPUT+="### 用户偏好\n"
recall_memory "preferences" | while IFS= read -r line; do
  [[ -n "$line" ]] && OUTPUT+="- $line\n"
done
OUTPUT+="\n"

# 注入最近教训
OUTPUT+="### 最近踩坑\n"
recall_memory "lessons" | while IFS= read -r line; do
  [[ -n "$line" ]] && OUTPUT+="- $(echo "$line" | cut -c3- | head -c120)\n"
done
OUTPUT+="\n"

echo -e "$OUTPUT"