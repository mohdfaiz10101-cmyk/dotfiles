---
name: tool-calling-patterns
description: AI 工具调用最佳实践 — 并行策略、错误处理、上下文管理、验证闭环
user-invocable: false
version: "1.0.0"
category: ai-orchestration
tags: [tool-calling, patterns, optimization, multi-model]
effort: low
---

# 工具调用模式库（Tool-Calling Playbook）

从 Opus 级模型的工具调用策略中提炼的可共享知识。所有 AI 工具均可参考。

## 1. 并行调用策略

### 何时并行
- 多个独立的文件读取（无依赖关系）
- 多个独立的 Web 搜索
- 多个独立的服务状态检查
- 多个独立的 Grep/Glob 搜索

### 何时串行
- 读取文件 → 编辑文件（依赖前一步内容）
- 创建目录 → 写入文件（依赖目录存在）
- Git add → Git commit → Git push（严格顺序）
- 修改配置 → 重启服务 → 验证（依赖链）

### 反模式
- 猜测文件内容直接编辑（必须先 Read）
- 一个接一个执行可并行的搜索
- 不验证就报告完成

## 2. 错误处理模式

### 重试策略
- 第 1 次失败 → 检查参数/路径是否正确，修正后重试
- 第 2 次失败 → 换思路（不同的工具/方法）
- 第 3 次失败 → 升级到更高能力模型或报告用户

### 降级策略
- Letta MCP 不可用 → 降级到 grep memory/ 文件
- Docker 不可用 → 降级到本地命令
- 网络不可用 → 降级到本地缓存

### 升级链
- Haiku 失败 → Sonnet → Opus → 报告用户
- 传递上下文：原始任务 + 已尝试方法 + 失败原因

## 3. 上下文管理

### 何时 Compact
- 上下文超过 50% 时主动 /compact
- 任务切换时清理无关上下文
- 长会话中完成阶段性任务后

### 传递上下文
- 分发子任务时 MUST 包含：原始 prompt、相关文件路径、约束条件、验证要求
- 不要假设子 agent 有任何先验知识

### Token 节省
- 搜索前先检查 memory/ 缓存（PRE_GATE）
- 使用 Skill 替代重复探索
- 大文件只读关键部分（offset + limit）

## 4. 验证闭环（强化版）

### 标准验证流程
1. **修改文件** → 验证语法（bash -n / nix flake check / jq . / python3 -m py_compile）
2. **修改服务** → 重启 → curl 测试 → 检查日志 → 验证前端加载
3. **修改配置** → 读回确认写入成功（kreadconfig6 / cat）
4. **创建脚本** → 运行一次确认可执行 + 检查权限

### 原子编辑模式（关键配置）
```bash
# 1. 备份
cp config.conf config.conf.bak

# 2. 编辑
Edit(file_path="config.conf", ...)

# 3. 验证
验证命令 || {
    # 失败回滚
    mv config.conf.bak config.conf
    报告错误
}

# 4. 成功清理
rm config.conf.bak
```

### 禁止
- 修改后不验证就报告完成
- 假设操作成功而不检查
- 跳过服务重启直接测试
- 关键配置修改不备份

## 5. MCP 工具选择决策树

```
需要读取文件？ → Read 工具（不是 cat）
需要搜索文件名？ → Glob 工具（不是 find）
需要搜索内容？ → Grep 工具（不是 grep 命令）
需要编辑文件？ → Edit 工具（不是 sed）
需要记忆检索？ → letta_search（Letta 在线时）→ grep memory/（降级）
需要记忆存储？ → letta_store + guard_record（双写）
需要网页信息？ → WebSearch → WebFetch
需要运行命令？ → Bash 工具
需要复杂任务？ → Task 工具（委派子 agent）
```

## 6. 跨工具协作模式

### Claude → Roo Code
- 通过 .roo/rules/ 传递知识
- 通过 shared-rules.yaml → compiler.py 传递规则

### Roo Code → Claude
- 通过 guard_record MCP 回写 memory/
- 通过 roo-digest 定期提取对话摘要
- **新增**：工具调用模式回写到此 Skill

### Claude → GLM/DeepSeek
- 通过 compiler.py 编译 shared-prompt-*.md
- 通过 LiteLLM 统一调用接口

### Aider → Claude
- Git post-commit hook 自动提取变更摘要
- 写入 memory/codebase-map.md

### 所有工具 → 共享索引
- ~/.local/share/ai-learning/shared-knowledge-index.json
- 知识事件总线自动分发

## 7. 性能优化技巧（新增）

### Token 节省
- 用 `Grep` 代替盲目 `Read`（节省 70% token）
- 用 `Glob` 代替 `ls` 和 `find`（更快更准）
- 并行调用工具（减少往返次数）
- 长文件使用 `offset` + `limit` 窗口读取

### 速度提升
- 独立操作一次性发起（3-5 倍加速）
- 使用 `head_limit` 限制输出长度
- PRE_GATE 检索避免重复探索
- Skill 缓存避免重复规划

### 可靠性提升
- 所有 Edit 后必须 Verify
- 关键操作使用 Atomic Edit
- 记录失败经验到 memory
- 破坏性操作前先 SAFETY RETRIEVAL
