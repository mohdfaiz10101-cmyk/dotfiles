---
name: opencode-ansi-strip
description: "修复 opencode --format json 输出混入 TUI ANSI 转义码导致乱码的问题"
user-invocable: false
version: "1.0.0"
category: opencode
tags: [opencode, ansi, 乱码, formatter, op-exec]
effort: medium
auto-generated: true
created: 2026-04-20
---

# Opencode Ansi Strip

## 场景
## 场景
opencode run --format json 仍会向 stdout 输出 TUI 鼠标/光标 ANSI 控制序列（如 5;36;21M...），导致下游 formatter/grep 看到乱码。

## 修复方法
在 opencode 调用前设置 NO_COLOR=1 TERM=dumb，并在管道中加 sed ANSI 过滤：

```bash
NO_COLOR=1 TERM=dumb opencode run --model xxx --format json "$PROMPT" 2>/dev/null   | sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g; s/\x1b[()]//g; s/\r//g'   | python3 -u /tmp/formatter.py
```

## 注意事项
- NO_COLOR=1 禁止颜色，TERM=dumb 禁止光标/鼠标序列
- sed 模式覆盖：CSI 序列(\x1b[...)、字符集切换(\x1b()、Windows 回车(\r)
- 两者都要加，单独用其中一个不够
- 在 bash -c 包裹时：bash -c "NO_COLOR=1 TERM=dumb opencode run ..."

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
