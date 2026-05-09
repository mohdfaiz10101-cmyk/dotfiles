---
name: system-audit-fix
description: "全系统审计→诊断→修复执行闭环：资源巡检(CPU/内存/磁盘/Docker/systemd)、代码质量扫描(连接池/硬编码/无界队列)、配置优化(LiteLLM/agent分层/定时器重叠)、自动生成优先级排序和修复建议，支持--audit-only和--auto-fix模式"
user-invocable: true
version: "1.0.0"
category: system
tags: [audit, optimization, docker, systemd, systemd-timers, sqlite, litellm, resource-management]
effort: medium
auto-generated: true
created: 2026-04-23
---

# System Audit→Fix 全系统审计修复闭环

## 场景
- 定期/按需全系统健康审计
- 发现问题后自动按优先级执行修复
- 系统变更前后对比验证

## Phase 1: 资源巡检（并行采集）

```bash
docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.Status}}' > /tmp/audit-docker.txt &
systemctl --user list-units --state=failed --no-pager > /tmp/audit-failed-services.txt &
systemctl --user list-timers --all --no-pager > /tmp/audit-timers.txt &
df -h / /mnt/ai /mnt/ai-cluster 2>/dev/null > /tmp/audit-disk.txt &
free -h > /tmp/audit-mem.txt &
wait
```

**判断阈值**：根分区>85% → P0 | 内存>90%+swap>80% → P0 | 单容器>1G且unhealthy → P0

## Phase 2: 优先级分类（P0-P3）

| 级别 | 条件 | 示例 |
|------|------|------|
| P0 紧急 | 分区>85% / 内存>90%+swap满 / 服务failed / 明文凭证 | gpt-sovits(2G unhealthy)、Discord token明文 |
| P1 高优 | 无连接池>10处 / 新建连接>5处 / 模型路由浪费 / 定时器重叠>3 | hub-api 21处sqlite3.connect、wechat 8处httpx |
| P2 深层 | Context Rot / 无界队列 / 缓存未启用 / 异步可优化 | CRM upsert schema不匹配、reply_queue无界 |
| P3 配置 | 硬编码路径 / 缺少超时 / 无重试策略 | 4处LITELLM_API_KEY硬编码 |

## Phase 3: 代码质量扫描（grep模式）

```bash
# 连接泄漏
grep -rn 'sqlite3.connect' --include='*.py' ~/hub/ ~/agi/ | grep -v 'contextmanager\|with '
# 硬编码凭证
grep -rn 'API_KEY\s*=\s*["\x27][^"\x27]' --include='*.py' ~/hub/ ~/agi/
# 无界队列
grep -rn 'queue\|Queue(' --include='*.py' ~/hub/ ~/agi/ | grep -v 'maxsize'
# 每次新建连接
grep -rn 'httpx.AsyncClient(' --include='*.py' ~/hub/ ~/agi/
# 定时器重叠
awk '/OnCalendar/{print FILENAME, $0}' ~/.config/systemd/user/*.timer /etc/nixos/modules/timers*.nix 2>/dev/null | sort -k3
```

## Phase 4: 自动修复（--auto-fix 模式）

### P0（立即执行）
1. 根分区>85% → `nix store gc` + `docker system prune -f`
2. unhealthy容器 → `docker stop <name>` + 记录
3. 明文凭证 → 移至 `.env` + systemd `EnvironmentFile=` 引用

### P1（逐项确认）
1. SQLite → `aiosqlite` 连接池或 `@contextmanager`
2. httpx → 全局 `_http_client` 单例 + `lifespan` 管理
3. 定时器重叠 → 合并为单一timer（保留最高频率）
4. 模型分层 → explore→flash, plan→turbo, build→coding

### P2（批量执行）
1. 无界队列 → `maxsize=1000`
2. 硬编码路径 → 配置文件或环境变量
3. 缺少超时 → 默认 `timeout=30`

## Phase 5: 验证+报告

```bash
docker stats --no-stream --format '{{.Name}}: {{.MemUsage}}'
systemctl --user show <svc> --property=Result,ActiveState
curl -s http://localhost:<port>/health | python3 -m json.tool
```

**输出**：`[OK/FAIL/SKIP] 操作 → 结果` | 相同×N合并 | 报告存 `~/Desktop/audit/`
**记忆**：`memory/lessons-learned.md` + `letta_store()`

## 安全约束（死规则）
- 涉及分区操作前 MUST：`df -T <path>` 验证文件系统
- 修改任何文件前 MUST：先 read 完整内容
- `nixos-rebuild` 前 MUST：`nix flake check` + `memory/` 检索历史风险
- 禁止在 NTFS 上执行 Docker/npm/cargo 操作
- `systemctl --user is-active` 返回 `inactive` ≠ 失败，MUST 用 `show --property=Result` 确认

## 关联 Skill
- `system-health-check` — 健康巡检（轻量版）
- `docker-cleanup` — Docker 清理
- `proxy-diagnose` — 代理系统诊断
- `nixos-safety-check` — NixOS 安全预检
- `security-audit` — 安全审计
