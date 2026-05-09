---
name: skill-create
description: 从已完成的工作中自动提取操作模式，封装为可复用的 Claude Code skill
user-invocable: true
version: "1.0.0"
category: meta
tags: [meta, skill, automation, reuse]
effort: medium
---

# /skill-create

从当前会话已完成的工作中提取操作模式，自动生成可复用的 Claude Code skill。

## 用法

```
/skill-create [name] [--from session] [--from memory]
```

**参数**:
- `name` (可选) — skill 名称。不提供时自动从任务内容推断
- `--from session` (默认) — 从当前会话的工作中提取
- `--from memory` — 从 memory/lessons-learned.md 的最近条目中提取

## 提取流程

当用户触发 `/skill-create` 时，执行以下步骤：

### Step 1: 识别操作模式

回顾当前会话（或 memory），识别以下特征：

- **是否解决了特定类型的问题？** （如：配置某服务、部署某架构、诊断某故障）
- **是否有重复出现的命令序列？** （如：总是先检查 X 再执行 Y）
- **是否积累了领域知识？** （如：某工具的配置要点、某框架的最佳实践）
- **是否创建了工具/脚本？** （如：诊断脚本、自动化工具）

### Step 2: 判断是否值得封装

以下情况**值得封装**为 skill：
- 操作步骤 ≥ 3 步
- 包含特定于用户环境的命令/路径
- 涉及用户常遇到的问题
- 包含踩坑经验和注意事项

以下情况**不值得封装**：
- 一次性操作（如：安装某个特定软件）
- 简单的 1-2 步操作
- 纯对话/问答，无实际操作

### Step 3: 生成 SKILL.md

根据识别到的模式，生成 skill 文件。文件结构：

```
---
name: <skill-name>
description: <一句话描述功能>
user-invocable: true
version: "1.0.0"
category: <system|development|diagnostics|meta>
tags: [<tag1>, <tag2>, ...]
effort: <low|medium|high>
---

# /<skill-name>

<详细描述>

## 用法
<子命令和参数说明>

## 操作步骤
<具体的命令和代码>

## 注意事项
<环境特定的坑和解决方案>
```

### Step 4: 写入文件

```bash
mkdir -p ~/.claude/skills/<skill-name>/
```

将生成的 SKILL.md 写入 `~/.claude/skills/<skill-name>/SKILL.md`。

### Step 5: 验证

- 检查文件语法正确（有 frontmatter + 正文）
- 检查文件出现在 skill 列表中
- 输出总结：skill 名称、文件路径、包含的子命令数量

## Skill 模板类型

根据提取到的模式类型，选择合适的模板：

### 诊断类 (diagnostics)

适用于：排查问题、健康检查、状态诊断

```
# /<name>
<问题描述>

## 用法
/<name> [--full] [--fix]

## 检查项
1. <检查 1>: <命令>
2. <检查 2>: <命令>
...

## 修复方案
<常见问题和修复命令>
```

### 操作类 (system)

适用于：执行特定操作、管理服务、部署配置

```
# /<name>
<功能描述>

## 用法
/<name> [start|stop|status|<其他子命令>]

## 操作步骤
### <子命令 1>
<命令序列>

## 注意事项
<环境特定注意点>
```

### 知识类 (knowledge)

适用于：最佳实践、配置参考、设计模式

```
# /<name>
<知识领域描述>

## 原则
1. <原则 1>
2. <原则 2>
...

## 参考配置
<代码示例>

## 常见错误
<错误 → 修复>
```

## 输出格式

生成完成后，输出结构化总结：

```
╔════════════════════════════════════════════════════╗
║  Skill 自动封装完成                                  ║
║────────────────────────────────────────────────────║
║  名称: <name>                                      ║
║  路径: ~/.claude/skills/<name>/SKILL.md            ║
║  类型: <diagnostics|system|knowledge>              ║
║  子命令: <N> 个                                     ║
║  来源: 当前会话 / memory                            ║
╚════════════════════════════════════════════════════╝
```

## 注意事项

- **不要覆盖已有 skill** — 如果同名 skill 已存在，在文件名后加 `-v2` 或询问用户
- **保持简洁** — skill 文件控制在 200 行以内，只保留核心操作
- **包含环境特定信息** — 如 NixOS 的 LD_LIBRARY_PATH、端口号码、文件路径等
- **验证命令有效** — 生成的 bash 命令必须经过验证（至少 `bash -n` 检查）
- **中文描述** — description 和正文使用中文，命令和代码保持英文
