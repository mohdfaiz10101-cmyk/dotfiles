---
name: auto-skill
description: 检测当前会话已完成的工作并立即执行封装，不询问确认，直接生成 SKILL.md
user-invocable: true
version: "1.0.0"
category: meta
tags: [meta, automation, skill-creation, auto]
effort: low
---

# /auto-skill

检测本次会话中值得封装的工作模式，**立即调用 create-skill.py 生成 SKILL.md**，不输出标签、不询问确认。

## 触发方式

用户说 `/auto-skill` 或 `封装这个` 或 `把这个做成skill`

## 执行流程（死规则 — 必须真正运行命令，不仅输出文字）

### Step 1: 识别本次会话的核心工作
从以下维度提取：
- 新增了什么功能/脚本/配置？
- 解决了什么具体问题？
- 有哪些步骤/命令序列可复用？
- 踩了什么坑？

### Step 2: 确定 skill 名称和分类
- 名称：kebab-case，描述功能而非场景（如 `kanban-agent-hub` 而非 `今天做的kanban`）
- 分类：system | code | devops | meta | ai | frontend | backend

### Step 3: 立即执行封装（MUST — 死规则）
```bash
python3 ~/.claude/skills/create-skill.py \
  --name "{skill-name}" \
  --content "{功能摘要+步骤+踩坑}" \
  --category "{分类}" \
  --tags "{tag1},{tag2},{tag3}"
```

**禁止**：
- ❌ 只输出 `[AUTO_SKILL] 可封装: xxx` 标签然后停下
- ❌ 问用户"要不要封装？(y/n)"
- ❌ 说"建议创建 skill"但不执行命令
- ✅ 直接运行 `python3 create-skill.py`，输出创建结果

### Step 4: 验证并汇报
```bash
ls ~/.claude/skills/{skill-name}/SKILL.md
```
输出：`[AUTO_SKILL] 已创建 → ~/.claude/skills/{name}/SKILL.md`

## 判断标准（满足 ≥2 条即立即封装，无需确认）
1. **可复用**：未来可能再遇同类场景
2. **多步骤**：≥3 步操作或有排查过程
3. **知识密度**：包含非显而易见的信息
4. **缺失**：`ls ~/.claude/skills/` 中无对应 skill

## 与 CLAUDE.md 的关系
CLAUDE.md 中 AUTO_SKILL 协议的"封装流程"第2步 MUST 直接执行本 skill 逻辑，
不等用户确认，不输出建议标签后停下。
