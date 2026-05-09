---
name: quickstart-guide
description: Claude Skills 管理系统快速参考文档
---

# Claude Skills 管理系统 — 快速参考

## 一句话总结

**Git 版本控制** + **Letta 语义检索** + **自动更新** = 全局共享的 Skill 知识库

---

## 快速开始（5 分钟）

### 1. 检查系统状态
```bash
bash ~/.claude/skills/test-skills.sh    # 或
systemctl --user status skill-sync.timer
```

### 2. 立即同步
```bash
bash ~/.claude/skills/skill-sync.sh
```

### 3. 触发自动更新（示例）
```bash
python3 ~/.claude/skills/skill-update-hook.py "Discord bot 429 error"
```

---

## 文件位置速查

| 文件 | 位置 | 说明 |
|------|------|------|
| **skill-sync.sh** | `~/.claude/skills/` | 主同步脚本（Git + Letta） |
| **skill-to-letta.py** | `~/.claude/skills/` | Letta 索引脚本 |
| **skill-update-hook.py** | `~/.claude/skills/` | 自动更新 Hook |
| **test-skills.sh** | `~/.claude/skills/` | 测试套件 |
| **README.md** | `~/.claude/skills/` | 完整文档 |
| **Timer 配置** | `~/.config/systemd/user/skill-sync.timer` | 定时器 |
| **Service 配置** | `~/.config/systemd/user/skill-sync.service` | 服务定义 |

---

## 常用命令（复制粘贴）

### Git 操作
```bash
# 查看最近提交
cd ~/.claude/skills && git log --oneline -10

# 查看某 Skill 的变更历史
cd ~/.claude/skills && git log --oneline -- discord-bot-diagnostics/

# 查看最近一次提交的 diff
cd ~/.claude/skills && git diff HEAD~1 HEAD

# 恢复某文件到上一次提交
cd ~/.claude/skills && git checkout HEAD~1 -- discord-bot-diagnostics/SKILL.md
```

### Systemd Timer
```bash
# 查看 Timer 状态
systemctl --user status skill-sync.timer

# 查看 Timer 执行日志（实时）
journalctl --user -u skill-sync.service -f

# 查看最近的 Timer 日志
journalctl --user -u skill-sync.service -n 50

# 手动触发一次 Timer
systemctl --user start skill-sync.service

# 禁用 Timer
systemctl --user disable skill-sync.timer

# 启用 Timer
systemctl --user enable skill-sync.timer
```

### 脚本执行
```bash
# 立即执行同步（Git + Letta）
bash ~/.claude/skills/skill-sync.sh

# 只执行 Letta 索引
python3 ~/.claude/skills/skill-to-letta.py

# 测试自动更新 Hook
python3 ~/.claude/skills/skill-update-hook.py "问题描述"

# 运行完整测试套件
bash ~/.claude/skills/test-skills.sh
```

---

## 常见场景

### 场景 1：遇到问题，想让系统自动学习

```bash
# 当发生错误时，调用 hook 让系统自动更新 Skill
python3 ~/.claude/skills/skill-update-hook.py "Discord bot returned 429 RESOURCE_EXHAUSTED"

# 查看自动添加的 troubleshooting 条目
cat ~/.claude/skills/discord-bot-diagnostics/SKILL.md | tail -30
```

### 场景 2：想要看最近发生了什么

```bash
# 查看 Git 日志
cd ~/.claude/skills && git log --oneline -20

# 查看同步日志
cat ~/.claude/skills/.sync.log | tail -50

# 查看 Systemd 运行日志
journalctl --user -u skill-sync.service -n 100
```

### 场景 3：想要检索相关的 Skill

```bash
# 所有 Skills 已索引到 Letta，其他 AI 可以：
letta agent <agent-id> search "discord bot error"

# 或者查看本地 Skill 列表
ls -d ~/.claude/skills/*/

# 或者看某个 Skill 的详情
cat ~/.claude/skills/discord-bot-diagnostics/SKILL.md
```

### 场景 4：想要手动编辑某个 Skill

```bash
# 编辑文件
vim ~/.claude/skills/discord-bot-diagnostics/SKILL.md

# 手动提交到 Git
cd ~/.claude/skills
git add discord-bot-diagnostics/
git commit -m "docs(discord-bot-diagnostics): update troubleshooting section"

# 立即同步（可选，Timer 也会每天同步）
bash ~/.claude/skills/skill-sync.sh
```

---

## 核心工作流程

```
用户遇到问题
    ↓
skill-update-hook.py 检测 trigger patterns
    ↓
匹配相应 Skill，自动添加 troubleshooting
    ↓
Git 提交变更
    ↓
[每天 3:00 AM]
skill-sync.sh 运行：
  - 提交未提交的变更到 Git
  - 索引所有 Skill 到 Letta
    ↓
其他 AI 通过 Letta 搜索 Skill 获取最新知识
```

---

## 环境变量（可选）

```bash
# 如果 Letta 不在默认位置，设置
export LETTA_API_URL="http://your-letta-server:8283"
export LETTA_API_KEY="your-api-key"

# 然后运行
python3 ~/.claude/skills/skill-to-letta.py
```

---

## 故障排除（常见问题）

### Q1: Timer 没有执行？

**A:** 检查是否启用了：
```bash
systemctl --user is-enabled skill-sync.timer
# 若输出 "disabled"，运行：
systemctl --user enable skill-sync.timer
```

### Q2: Letta 索引失败？

**A:** 检查 Letta 连接：
```bash
curl -s http://localhost:8283/v1/agents | jq .

# 若连接不上，脚本会自动跳过 Letta 部分
# 可在生产环境配置正确的 LETTA_API_URL
```

### Q3: skill-update-hook 没有匹配？

**A:** 检查 trigger patterns：
```bash
cat ~/.claude/skills/discord-bot-diagnostics/skill.json | jq '.auto_update.trigger_patterns'

# 确保用户的消息包含 trigger 关键词
# trigger 支持正则表达式
```

### Q4: Git 提交失败？

**A:** 检查 Git 配置：
```bash
cd ~/.claude/skills && git config --list | grep user

# 若缺失，配置：
git config user.name "Claude Skills System"
git config user.email "skills@claude-mpm.local"
```

---

## Timer 执行计划

| 字段 | 值 | 含义 |
|------|-----|------|
| OnCalendar | daily | 每天执行 |
| 执行时间 | 03:00:00 | 凌晨 3 点（可编辑） |
| Persistent | true | 若错过执行时间，启动后补偿执行 |

**编辑执行时间**：
```bash
# 编辑 timer
systemctl --user edit --full skill-sync.timer

# 找到 OnCalendar 行，修改为：
OnCalendar=*-*-* 02:00:00   # 改为 2 点

# 重新加载并重启 timer
systemctl --user daemon-reload
systemctl --user restart skill-sync.timer
```

---

## 系统架构图

```
                    ┌─────────────────────┐
                    │  User Problem       │
                    │  (Discord bot 429)  │
                    └──────────┬──────────┘
                               │
                               ↓
                    ┌──────────────────────────┐
                    │ skill-update-hook.py     │
                    │ (Pattern Matching)       │
                    └──────────┬───────────────┘
                               │
                               ↓
                    ┌────────────────────────────┐
                    │ discord-bot-diagnostics    │
                    │ (Skill auto-update)        │
                    │ + troubleshooting entry    │
                    └──────────┬─────────────────┘
                               │
                               ↓
                    ┌─────────────────────┐
                    │ Git Commit          │
                    │ (Version Control)   │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ↓                                     ↓
    ┌──────────────────┐          ┌──────────────────────┐
    │ Systemd Timer    │          │  (每日 3:00 AM)      │
    │ (Daily)          │          │                      │
    └──────────────────┘          └─────────┬────────────┘
                                            │
                                ┌───────────┴────────────┐
                                ↓                        ↓
                    ┌──────────────────┐     ┌──────────────────┐
                    │ skill-sync.sh    │     │skill-to-letta.py │
                    │ (Git Commit)     │     │ (Letta Index)    │
                    └──────────────────┘     └──────────────────┘
                                ↓                        ↓
                        ┌───────────────────────────────┘
                        ↓
                    ┌────────────────────────┐
                    │ Letta Archival Memory  │
                    │ (Global Knowledge)     │
                    │ (Other AI can search)  │
                    └────────────────────────┘
```

---

## 下一步

1. **启用 Timer**（如果还没启用）：
   ```bash
   systemctl --user enable skill-sync.timer
   ```

2. **阅读完整文档**：
   ```bash
   cat ~/.claude/skills/README.md
   ```

3. **浏览现有 Skills**：
   ```bash
   ls -d ~/.claude/skills/*/
   ```

4. **创建新 Skill**（参考 discord-bot-diagnostics 结构）

---

**版本**：v1.0.0
**最后更新**：2026-04-08
**快速参考卡片**
