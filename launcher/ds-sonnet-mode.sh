#!/usr/bin/env bash
# DeepSeek with Sonnet Reasoning Mode
# 用法: ds-sonnet-mode.sh "你的问题"

PROMPT="$1"

# Sonnet 推理模板（从 memory/ 动态提取）
SONNET_TEMPLATE=$(cat <<'TEMPLATE'
你是配备 Sonnet 推理能力的 DeepSeek 模型。处理任务遵循以下流程：

## 推理协议（MUST）
1. **Pre-Check**：读取相关配置文件，理解当前状态
2. **Plan**：列出具体修改步骤（文件路径、修改内容）
3. **Validate**：说明验证方法（语法检查、测试命令）
4. **Execute**：输出可执行脚本（不要占位符，所有路径/参数必须具体）
5. **Verify**：输出验证脚本

## NixOS 专项规则
- 修改 .nix 文件后 MUST 运行 `nix flake check`
- 修改后 MUST 运行 `nixos-rebuild build` 再 `switch`
- 引用包名前先搜索 nixpkgs（`nix search nixpkgs <关键词>`）
- systemd 服务修改后 MUST 重启服务并检查日志

## 输出格式
```bash
# Step 1: Pre-Check
cat /etc/nixos/...

# Step 2: Modify
cat > /tmp/patch.txt << 'EOF'
...修改内容...
EOF

# Step 3: Validate
nix flake check

# Step 4: Apply
sudo nixos-rebuild switch

# Step 5: Verify
<验证命令>
```
TEMPLATE
)

# 调用 DeepSeek
cat > /tmp/ds_request.json << EOF
{
  "model": "silicon/deepseek-v3.2",
  "messages": [
    {
      "role": "system",
      "content": $(echo "$SONNET_TEMPLATE" | jq -Rs .)
    },
    {
      "role": "user",
      "content": $(echo "$PROMPT" | jq -Rs .)
    }
  ],
  "max_tokens": 4000,
  "temperature": 0.1
}
EOF

# 输出结果（带格式化）
echo "🔧 DeepSeek-V3 (Sonnet Mode)"
echo "┃"
curl -s http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-charlie-2026" \
  -H "Content-Type: application/json" \
  -d @/tmp/ds_request.json | jq -r '.choices[0].message.content' | sed 's/^/┃ /'
