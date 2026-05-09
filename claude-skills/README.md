---
name: skills-readme
description: Claude Skills Management System 说明文档
---

# Claude Skills Management System

**Git + Letta MCP 融合方案** — Skill 自动更新与全局共享系统

## 概述

本系统提供了完整的 Skill 管理流程，支持：

1. **Git 版本控制** — 所有 Skill 变更自动提交到 Git，便于版本跟踪
2. **Letta MCP 索引** — 将 Skill 内容索引到 Letta，支持语义检索和全局共享
3. **自动更新** — 检测问题 pattern，自动追加 troubleshooting 内容
4. **定时同步** — Systemd Timer 每天自动执行同步

## 文件结构

```
~/.claude/skills/
├── .git/                          # Git 仓库
├── .gitignore                     # Git 忽略规则
├── skill-sync.sh                  # 主同步脚本（Git + Letta）
├── skill-to-letta.py             # Letta 索引脚本
├── skill-update-hook.py           # 自动更新 Hook
├── test-skills.sh                 # 测试脚本
├── README.md                      # 本文件
├── discord-bot-diagnostics/       # Skill 示例
│   ├── skill.json                 # Skill 元数据
│   └── SKILL.md                   # Skill 文档
└── ...（其他 skills）
```

## 组件说明

### 1. skill-sync.sh

**用途**：主同步脚本，执行两步操作

```bash
bash ~/.claude/skills/skill-sync.sh
```

**功能**：
- 检测 Git 变更，自动提交到 Git
- 调用 `skill-to-letta.py` 索引到 Letta
- 生成执行日志（`~/.claude/skills/.sync.log`）

**输出**：
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Skill Sync Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Git Status: 3 changes
Total Skills: 25
Log: /home/charlie/.claude/skills/.sync.log
```

### 2. skill-to-letta.py

**用途**：将所有 Skill 的 SKILL.md 内容索引到 Letta MCP

```bash
python3 ~/.claude/skills/skill-to-letta.py
```

**功能**：
- 遍历所有 Skill 目录
- 读取 skill.json（元数据）和 SKILL.md（内容）
- 调用 Letta API 将内容写入归档记忆（archival memory）
- 支持语义搜索（triggers 作为标签）

**环境变量**：
- `LETTA_API_URL` — Letta 服务地址（默认：http://localhost:8283）
- `LETTA_API_KEY` — Letta API Key（默认：letta）

**输出**：
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Letta Indexing Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Indexed: 25
Failed: 0
Skipped: 5
```

### 3. skill-update-hook.py

**用途**：检测用户问题，自动追加 troubleshooting 内容

```bash
python3 ~/.claude/skills/skill-update-hook.py "Discord bot not responding"
```

**功能**：
- 扫描所有 Skill 的 trigger patterns
- 匹配用户消息
- 在 SKILL.md 的 Troubleshooting 部分追加新条目
- 提交到 Git

**支持的 trigger patterns**：

每个 Skill 在 skill.json 中定义 triggers：

```json
{
  "auto_update": {
    "enabled": true,
    "trigger_patterns": [
      "discord bot.*429",
      "bot.*not responding",
      "quota.*exhausted"
    ],
    "update_strategy": "append_troubleshooting"
  }
}
```

## Skill 元数据格式（skill.json）

标准的 Skill 配置文件：

```json
{
  "name": "discord-bot-diagnostics",
  "version": "1.0.0",
  "author": "Claude MPM",
  "description": "诊断和自动修复 Discord Bot 问题",
  "triggers": [
    "discord bot",
    "bot status",
    "429 error"
  ],
  "category": "diagnostics",
  "tags": ["discord", "systemd", "api"],
  "prerequisites": {
    "services": ["discord-bot.service"],
    "files": ["~/hub/discord-bot.py"],
    "commands": ["systemctl", "journalctl"]
  },
  "auto_update": {
    "enabled": true,
    "trigger_patterns": [
      "discord bot.*429",
      "bot.*not responding"
    ],
    "update_strategy": "append_troubleshooting"
  },
  "global_share": {
    "enabled": true,
    "share_url": "https://skills.claude-mpm.dev/discord-bot-diagnostics",
    "access": "public",
    "sync_interval": "daily"
  }
}
```

## Systemd Timer 配置

**启用自动同步**：

```bash
# 查看 timer 状态
systemctl --user status skill-sync.timer

# 查看 timer 执行日志
journalctl --user -u skill-sync.service -n 20

# 手动触发 timer（立即执行一次）
systemctl --user start skill-sync.service

# 禁用 timer
systemctl --user disable skill-sync.timer
```

**Timer 配置**：
- **执行频率**：每天 03:00 AM（可自定义 `OnCalendar`）
- **Persistent**：若错过执行时间，启动后会补偿执行
- **超时时间**：30 分钟（防止 Letta 连接超时）

## 测试

### 1. 测试 Git 同步

```bash
# 在任意 skill 目录修改文件
echo "test" >> ~/.claude/skills/discord-bot-diagnostics/SKILL.md

# 运行同步脚本
bash ~/.claude/skills/skill-sync.sh

# 检查 Git 日志
cd ~/.claude/skills && git log --oneline -5
```

### 2. 测试 Letta 索引

```bash
# 检查 Letta 是否在线
curl -s http://localhost:8283/v1/status

# 运行索引脚本
python3 ~/.claude/skills/skill-to-letta.py

# 检查日志
tail -20 ~/.claude/skills/.sync.log
```

### 3. 测试自动更新 Hook

```bash
# 触发自动更新（模拟用户报告问题）
python3 ~/.claude/skills/skill-update-hook.py "Discord bot not responding to messages in #cc channel"

# 检查 SKILL.md 是否更新
tail -20 ~/.claude/skills/discord-bot-diagnostics/SKILL.md
```

### 4. 运行完整测试

```bash
bash ~/.claude/skills/test-skills.sh
```

## 工作流程

### 日常使用流程

1. **问题发生**：用户报告问题（如"Discord bot not responding"）
2. **Hook 触发**：系统调用 `skill-update-hook.py` 检测 trigger
3. **自动更新**：匹配的 Skill 自动追加 troubleshooting 条目
4. **Git 提交**：变更提交到 Git，记录版本历史
5. **定时同步**：每天 3:00 AM，`skill-sync.sh` 运行：
   - Git commit 未提交的变更
   - Letta 重新索引所有 Skill
6. **全局共享**：其他 AI 通过 Letta 搜索 Skills

### 多 AI 共享流程

1. **Claude 更新 Skill**（追加 troubleshooting）
   ```
   Discord bot 问题 → skill-update-hook.py 触发
   → discord-bot-diagnostics 更新
   → Git 提交 + Letta 索引
   ```

2. **其他 AI 查询 Skill**（通过 Letta）
   ```
   其他 AI: "我需要处理 Discord bot 错误"
   → Letta 搜索相关 Skill
   → 返回 discord-bot-diagnostics 的最新内容
   ```

3. **技能库演进**
   ```
   月积累 → 每个 Skill 积累多个 troubleshooting 条目
   → Skill 知识库日益完善
   → 下次相同问题出现时，已有现成解决方案
   ```

## Letta MCP 集成

### 检索（其他 AI 使用）

```python
# Letta search
letta_search(
    agent_id="agent-caad9ac5-2a89-4d69-ab74-08379cce48f2",
    query="discord bot 429 error",
    limit=5
)
# 返回：[discord-bot-diagnostics skill 内容]
```

### 存储（自动运行）

```python
# Letta store（在 skill-to-letta.py 中调用）
letta_store(
    agent_id="agent-caad9ac5-2a89-4d69-ab74-08379cce48f2",
    text="[Skill:discord-bot-diagnostics v1.0.0] ...",
    tags=["skill", "discord-bot-diagnostics", "discord bot", "429 error", ...]
)
```

## 故障排除

### skill-sync.sh 失败

**检查 Git 配置**：
```bash
cd ~/.claude/skills && git config user.name && git config user.email
```

**检查权限**：
```bash
ls -la ~/.claude/skills/.git
```

**查看日志**：
```bash
cat ~/.claude/skills/.sync.log
```

### skill-to-letta.py 失败

**检查 Letta 连接**：
```bash
curl -s http://localhost:8283/v1/status | jq
```

**检查 API Key**：
```bash
echo "LETTA_API_KEY=${LETTA_API_KEY:-letta}"
```

**查看详细错误**：
```bash
python3 -u ~/.claude/skills/skill-to-letta.py 2>&1 | head -50
```

### skill-update-hook.py 未匹配

**检查 trigger patterns**：
```bash
cat ~/.claude/skills/discord-bot-diagnostics/skill.json | jq '.auto_update.trigger_patterns'
```

**调试匹配逻辑**：
```bash
python3 -c "
import re
message = 'Discord bot not responding'
patterns = ['discord bot', 'bot status', '429 error']
for p in patterns:
    if re.search(p, message.lower()):
        print(f'Match: {p}')
"
```

## 最佳实践

### 1. Skill 命名规范

```
mpm-* : MPM 系统 skill
discord-* : Discord 相关
gemini-* : Gemini API 相关
ai-* : AI 工具相关
```

### 2. 触发 Patterns 设计

```json
"triggers": [
  "exact_keyword",           // 精确关键词
  "pattern.*related",        // 正则模式
  "multi word.*pattern"      // 多词模式
]
```

### 3. 版本管理

```
version: X.Y.Z
- X: 主功能更新
- Y: troubleshooting 条目增加
- Z: bug 修复
```

每次大更新时：
```bash
# 更新 skill.json 中的 version
# 在 SKILL.md 尾部添加版本历史
# git commit -m "feat(skill-name): v1.1.0 - 新增 N 个 troubleshooting"
```

## 性能优化

### 缓存机制

Letta 使用归档记忆（archival memory），支持向量化语义搜索，自动缓存结果。

### 批量操作

```bash
# 批量索引所有 skills
python3 ~/.claude/skills/skill-to-letta.py

# 批量 Git 同步
cd ~/.claude/skills && git add . && git commit -m "batch sync"
```

### 并行执行

Systemd Timer 不支持并行执行同一 service，但可以创建多个 timer：

```bash
# 创建快速同步 timer（每 6 小时）
cp ~/.config/systemd/user/skill-sync.timer ~/.config/systemd/user/skill-sync-quick.timer
# 修改 OnCalendar=*:0/6:00
```

## 后续扩展

### 1. LLM 生成 Troubleshooting

当前 `skill-update-hook.py` 使用模板生成条目。未来可集成 LLM：

```python
# 集成 Claude API
entry = claude_api.generate_troubleshooting(
    skill_name="discord-bot-diagnostics",
    user_problem="Bot not responding",
    context=recent_logs
)
```

### 2. Web 界面

创建 Web 界面浏览和搜索 Skills：

```
/skills — 所有 skills 列表
/skills/:name — Skill 详情（git 历史、troubleshooting）
/search?q=... — 通过 Letta 搜索
```

### 3. Slack/Discord 通知

```bash
# 在 skill-sync.sh 中添加
curl -X POST $SLACK_WEBHOOK -d '{"text":"Skills synced: 25 indexed"}'
```

### 4. CI/CD 集成

```yaml
# .github/workflows/skill-sync.yml
- name: Sync Skills
  run: bash ~/.claude/skills/skill-sync.sh
  on:
    schedule:
      - cron: '0 3 * * *'
    push:
      paths:
        - '.claude/skills/**'
```

## 常用命令速查

```bash
# 立即运行同步
bash ~/.claude/skills/skill-sync.sh

# 查看最近的 Git 提交
cd ~/.claude/skills && git log --oneline -10

# 查看 Skill 变更
cd ~/.claude/skills && git diff HEAD~1

# 列出所有 skills
ls -d ~/.claude/skills/*/

# 查看 Timer 状态
systemctl --user status skill-sync.timer

# 查看 Timer 日志
journalctl --user -u skill-sync.service -f

# 手动触发 Timer
systemctl --user start skill-sync.service

# 搜索 Letta 中的内容（通过 letta CLI）
letta agent agent-caad9ac5-2a89-4d69-ab74-08379cce48f2 search "discord bot error"
```

---

**版本**：v1.0.0
**创建日期**：2026-04-08
**维护者**：Claude Skills System
