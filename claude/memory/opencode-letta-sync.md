# OpenCode-Letta 同步服务（方案 B：定时单向同步）

## 功能
- **实时监控**：监控 `memory/` 目录变化，自动同步到 Letta
- **容错机制**：Letta 不可用时静默失败，后台重试
- **状态追踪**：文件 hash 去重，避免重复上传
- **安全上传**：每块 2000 字符，分块上传，避免超限

## 配置
```bash
# 启动服务
systemctl --user enable --now opencode-letta-sync.service

# 查看状态
systemctl --user status opencode-letta-sync.service

# 查看日志
journalctl --user -u opencode-letta-sync.service -f

# 停止服务
systemctl --user stop opencode-letta-sync.service
```

## 文件映射
| OpenCode Memory | Letta Agent |
|----------------|-------------|
| MEMORY.md | code-assistant |
| lessons-learned.md | nixos-sysadmin |
| op-tasks.md | nixos-sysadmin |

## 容错策略
- **Letta 不可用**：服务继续运行，显示警告，后台重试
- **网络超时**：5 秒超时，失败后继续监控
- **上传失败**：跳过当前文件，不影响其他文件同步

## 状态文件
`~/.local/state/opencode-letta-sync-state.json` - 记录文件 hash 和同步时间戳

## 方案 B 特点
- **单向同步**：memory → Letta，简化复杂度
- **定时拉取**：每小时尝试拉取 Letta 更新（可选功能）
- **容错优先**：Letta 不可用时不会崩溃
- **资源友好**：内存占用 ~17M，CPU 占用极低
