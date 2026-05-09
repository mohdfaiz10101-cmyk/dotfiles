---
name: cc-op-bash-precheck
description: "CC/OP 自主引擎空跑防护：bash 前置检查替代 OpenCode scheduler，有异常才启动 LLM"
user-invocable: false
version: "1.0.0"
category: 系统运维
tags: [cc-op, opencode, scheduler, bash, empty-run, systemd]
effort: medium
auto-generated: true
created: 2026-04-17
---

# Cc Op Bash Precheck

## 场景
场景：OpenCode scheduler JSON 会被进程覆盖，改 invocation 无效。解决方案：(1) 禁用 OpenCode job JSON（.disabled 后缀）(2) stop+disable OpenCode 生成的 systemd timer (3) 创建 bash 包装脚本做前置检查：grep -c '^- \[ \]' op-tasks.md → 0 则 exit 0 静默退出，>0 才 exec opencode run。(4) 创建 systemd user timer 调用脚本。踩坑：grep -c 无匹配返回 exit code 1，不能用 set -e；需用 PENDING=$(grep ...) || PENDING=0 模式。cc-autonomous 同样需要检查 fixes_failed/disk_warn/backlog>5 再运行。OpenCode scheduler 生成两套触发机制：内部 supervisor.pl + 独立 systemd timer，两个都要禁用。

## 步骤
See content summary for details.

## 注意事项
Manually created — review and expand as needed.
