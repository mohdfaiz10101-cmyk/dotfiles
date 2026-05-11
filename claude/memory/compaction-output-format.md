---
name: OpenCode 压缩输出格式规范
description: 统一 opencode 和诊断脚本的输出风格，遵循 CLAUDE.md R1-R8 规则
type: feedback
---

## 为什么

OpenCode 压缩和系统诊断的输出频繁违反 CLAUDE.md R1-R8 规则，包含大量过渡句、冗余状态标记、空洞的解释。导致日志混乱。

## 规则

**遵循 CLAUDE.md R1-R8**：

| 规则 | 要求 | 违规例 | 正确例 |
|------|------|--------|--------|
| R1 零废话 | 禁止寒暄、过渡句 | "符合 R1-R8 的替代方案：" | `[SKIP]` |
| R3 状态标记 | 仅用 `[OK]` `[FAIL]` `[SKIP]` `[INFO]` | `FAIL WAL 文件锁定 → 需停止...` | `[FAIL] WAL 文件锁定` |
| R4 紧凑布局 | 段落≤3行 | 多行解释 | 一行状态 + 列表数据 |

## 实施

### 方案 A：脚本格式化（推荐）

```bash
# 使用格式化器
echo "诊断输出..." | opencode-format-compaction
```

位置：`~/.local/bin/opencode-format-compaction`

### 方案 B：GLM Prompt 规范

在 GLM 系统 prompt 中加入：

```
【压缩输出格式（opencode/诊断）】
- 禁止：寒暄、"符合 R1-R8"、"继续"、重复状态
- 只用：[OK] [FAIL] [SKIP] [INFO] 状态标记
- 格式：[STATUS] 结果概述 | 关键数据列表
- 例子：[OK] 数据库健康 | 282MB 34454条消息 | 所有消息60天内
```

位置：`launcher-server.py:_GLM_SYSTEM_BASE`

## 标准输出示例

### 前（违规）

```
FAIL WAL 文件锁定 → 需停止 opencode 进程
根本原因：opencode 以只读模式打开数据库...
符合 R1-R8 的替代方案：
SKIP 压缩失败 → 诊断报告
当前状态：
- 数据库：282MB，34454 条消息
```

### 后（规范）

```
[FAIL] WAL 文件锁定 | opencode 以只读模式
[SKIP] 压缩失败
- 数据库：282MB，34454 条消息
[OK] 诊断完成
```

## 如何应用

1. ✅ 所有 opencode 压缩诊断输出经过 `opencode-format-compaction`
2. ✅ GLM 压缩相关任务遵循新 prompt 规范
3. ✅ op-tasks.md SELF-IMPROVE 输出改用新格式

## 何时审查

- opencode 新版本发布后验证格式化规则是否需要更新
- GLM prompt 改动时检查是否兼容本规范

---

**why:** 日志一致性和可读性
**how to apply:** 所有系统诊断和压缩相关输出都经过格式化或遵循 GLM prompt
