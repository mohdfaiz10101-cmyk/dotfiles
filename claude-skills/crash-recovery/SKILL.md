---
name: crash-recovery
description: 强制关机后快速恢复上下文、诊断卡死原因、继续未完成任务
user-invocable: true
version: "1.0.0"
category: system
tags: [recovery, crash, gpu, context, resume]
effort: low
---
# Crash Recovery — 强制关机后快速恢复

## 使用方式
用户说「卡死了」「强制关机了」「恢复任务」→ 立即执行本 skill

## 步骤 1：诊断卡死原因

```bash
# GPU 相关（最常见根因）
journalctl -k --since "6 hours ago" | grep -E "nvidia.*ERROR|0x0000c67d|GPU.*hang|NVRM.*Xid" | tail -20

# 系统崩溃/OOM
journalctl --since "6 hours ago" | grep -E "Out of memory|oom-kill|kernel panic|BUG:|Oops:" | tail -10

# 内核错误摘要
journalctl -k --since "6 hours ago" --priority=0..3 | tail -30

# IO 问题（NTFS/磁盘挂起）
journalctl -k --since "6 hours ago" | grep -E "EXT4-fs error|NTFS.*error|I/O error|hung_task" | tail -10
```

## 步骤 2：恢复上下文

```bash
# 找最近6小时内的会话
ls -lt ~/.claude/projects/-home-charlie/*.jsonl | head -5

# 读最近会话的用户消息
python3 -c "
import json, sys
f = sys.argv[1]
with open(f) as fp:
    lines = fp.readlines()
for line in lines[-50:]:
    line = line.strip()
    if not line: continue
    try:
        d = json.loads(line)
        t = d.get('type','')
        if t in ('user','assistant'):
            msg = d.get('message',{})
            role = msg.get('role',t)
            content = msg.get('content','')
            if isinstance(content,list):
                for c in content:
                    if isinstance(c,dict) and c.get('type')=='text':
                        print(f'[{role}] {c["text"][:300]}')
                        break
            elif isinstance(content,str):
                print(f'[{role}] {content[:300]}')
    except: pass
" $(ls -t ~/.claude/projects/-home-charlie/*.jsonl | head -1)
```

## 步骤 3：查未完成任务

```bash
# pending-tasks.md 中的待办
grep "^- \[ \]" ~/.claude/projects/-home-charlie/memory/pending-tasks.md | head -10

# op-tasks.md 中未完成
grep "^- \[ \]" ~/.claude/projects/-home-charlie/memory/op-tasks.md | tail -20
```

## 步骤 4：系统健康快检

```bash
# 关键服务状态
systemctl is-active docker litellm 2>/dev/null
docker ps --format "{{.Names}}: {{.Status}}" 2>/dev/null | head -10

# GPU 当前状态（确认无卡死）
cat /proc/driver/nvidia/gpus/*/information 2>/dev/null | grep "Model\|Firmware"
journalctl -k --since "30 min ago" | grep -c "0x0000c67d" || echo "GPU: 正常"
```

## 常见卡死根因速查

| 错误关键词 | 根因 | 修复 |
|-----------|------|------|
| `0x0000c67d` / `nvidia-modeset ERROR` | GSP firmware 超时 (RTX 3060 Ti, 595.x, Wayland) | `NVreg_EnableGpuFirmware=0` 写入 desktop.nix |
| `Xid 79` / `NVRM: Xid` | GPU 硬件错误/驱动崩溃 | 重启 + 检查温度 |
| `oom-kill` / `Out of memory` | 内存耗尽 | `systemctl status` 查哪个进程吃内存 |
| `hung_task` | IO 阻塞（NTFS/NFS） | 检查 NTFS 挂载，迁移缓存到 ext4 |
| `EXT4-fs error` | 磁盘文件系统错误 | `fsck` 修复 |

## 已知常驻问题（跳过）
- `OP agent xxx 连续3次重启失败` — 假阳性，timer job 非持续服务，exit=142 SIGALRM 正常
- `opencode` 不响应 → 检查 `~/.opencode/opencode.json` 是否为循环软链接
