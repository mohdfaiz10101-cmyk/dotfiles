# Obsidian 自动同步指南

> 自动同步 Charlie Hub 文档到 Obsidian Vault
> 创建时间：2026-04-07

---

## 同步内容

### 从 `~/.claude/projects/-home-charlie/memory/` 同步

- `command-reference.md` → `📋 操作命令速查手册.md`
- `nixos-config.md` → `⚙️ NixOS 配置笔记.md`
- `lessons-learned.md` → `💡 经验教训记录.md`
- `troubleshooting.md` → `🔧 问题排查手册.md`
- `MEMORY.md` → `🧠 系统核心档案.md`
- `ai-tools.md` → `🤖 AI 工具对比.md`
- `ideas-roadmap.md` → `💭 方案灵感汇总.md`
- `codebase-map.md` → `🗺️ 代码库探索缓存.md`

### 从 Hub 目录同步

- `/home/charlie/hub/README.md` → `📦 Charlie Hub 部署文档.md`
- `/home/charlie/hub/discord-bot-test-guide.md` → `🤖 Discord Bot 测试指南.md`
- `/home/charlie/.config/api-keys/README.md` → `🔑 API Keys 管理说明.md`

---

## 自动同步机制

### Systemd Timer

**服务文件**: `~/.config/systemd/user/sync-obsidian.service`
**定时器**: `~/.config/systemd/user/sync-obsidian.timer`
**同步间隔**: 5 分钟

### 控制命令

```bash
# 查看 timer 状态
systemctl --user status sync-obsidian.timer

# 手动触发同步
sync-to-obsidian
# 或
systemctl --user start sync-obsidian.service

# 查看同步日志
journalctl --user -u sync-obsidian.service -n 20

# 停止自动同步
systemctl --user stop sync-obsidian.timer

# 重新启用
systemctl --user enable --now sync-obsidian.timer

# 查看下次执行时间
systemctl --user list-timers sync-obsidian.timer
```

---

## 同步特性

### 1. 自动添加元数据

每个同步的文件都会添加 Obsidian frontmatter：

```yaml
---
tags: [charlie-hub, auto-sync]
updated: 2026-04-07 16:42:30
source: /home/charlie/.claude/projects/-home-charlie/memory/command-reference.md
---
```

### 2. Emoji 标识

使用 emoji 前缀便于在 Obsidian 中快速识别：

- 📋 操作手册
- ⚙️ 配置文档
- 💡 经验记录
- 🔧 排查工具
- 🧠 核心档案
- 🤖 AI 工具
- 🔑 安全配置
- 📦 部署文档
- 💭 灵感方案
- 🗺️ 代码地图

### 3. 索引页面

自动生成 `📚 Charlie Hub 文档索引.md`，包含：
- 所有文档的分类链接
- 快速访问链接
- 同步说明

---

## 在 Obsidian 中使用

### 打开文档中心

1. 打开 Obsidian
2. 左侧文件树 → `Charlie-Hub` 文件夹
3. 打开 `📚 Charlie Hub 文档索引.md`

### 快捷搜索

1. `Ctrl+O` 快速打开
2. 输入 emoji 或关键词（如 "📋" 或 "命令"）
3. 选择文档

### 使用标签

所有同步的文档都有 `#charlie-hub` 和 `#auto-sync` 标签：

1. 点击任意标签
2. 查看所有相关文档

### 链接跳转

索引页面使用 Obsidian 内链语法 `[[文件名]]`：
- 可以直接点击跳转
- 支持悬停预览

---

## 目录结构

```
~/Obsidian Vault/
└── Charlie-Hub/
    ├── 📚 Charlie Hub 文档索引.md    # 入口页面
    ├── 📋 操作命令速查手册.md         # 命令速查
    ├── ⚙️ NixOS 配置笔记.md          # NixOS 配置
    ├── 💡 经验教训记录.md            # 踩坑记录
    ├── 🔧 问题排查手册.md            # 故障排查
    ├── 🧠 系统核心档案.md            # 系统信息
    ├── 🤖 AI 工具对比.md             # AI 工具
    ├── 🔑 API Keys 管理说明.md       # 密钥管理
    ├── 📦 Charlie Hub 部署文档.md    # 部署指南
    ├── 🤖 Discord Bot 测试指南.md    # Bot 测试
    ├── 💭 方案灵感汇总.md            # 规划方案
    └── 🗺️ 代码库探索缓存.md          # 代码地图
```

---

## 工作流

### 添加新命令到速查手册

1. 编辑源文件：
   ```bash
   vim ~/.claude/projects/-home-charlie/memory/command-reference.md
   ```

2. 添加命令到对应分类

3. 保存后，等待 5 分钟自动同步
   - 或手动触发：`sync-to-obsidian`

4. 在 Obsidian 中查看更新

### 记录新经验

1. 编辑 lessons-learned.md：
   ```bash
   vim ~/.claude/projects/-home-charlie/memory/lessons-learned.md
   ```

2. 添加新条目：
   ```markdown
   - [2026-04-07] 场景：经验描述
   ```

3. 自动同步到 Obsidian

### 更新部署文档

1. 编辑 Hub README：
   ```bash
   vim /home/charlie/hub/README.md
   ```

2. 更新内容

3. 自动同步到 `📦 Charlie Hub 部署文档.md`

---

## 故障排查

### 同步未执行

```bash
# 查看 timer 状态
systemctl --user status sync-obsidian.timer

# 查看上次执行时间
systemctl --user list-timers sync-obsidian.timer

# 手动触发测试
sync-to-obsidian
```

### 文件内容未更新

```bash
# 查看同步日志
journalctl --user -u sync-obsidian.service -n 50

# 检查源文件修改时间
ls -la ~/.claude/projects/-home-charlie/memory/command-reference.md

# 强制重新同步
sync-to-obsidian
```

### Obsidian 中看不到文件

1. 检查目录：
   ```bash
   ls -la "~/Obsidian Vault/Charlie-Hub/"
   ```

2. 在 Obsidian 中刷新文件树：
   - 右键文件夹 → Refresh

3. 检查文件权限：
   ```bash
   chmod 644 ~/Obsidian\ Vault/Charlie-Hub/*.md
   ```

---

## 定制化

### 修改同步间隔

编辑 timer 配置：
```bash
vim ~/.config/systemd/user/sync-obsidian.timer
```

修改 `OnUnitActiveSec` 值（默认 5min）：
- `OnUnitActiveSec=1min` - 每分钟
- `OnUnitActiveSec=10min` - 每 10 分钟
- `OnUnitActiveSec=1h` - 每小时

重新加载：
```bash
systemctl --user daemon-reload
systemctl --user restart sync-obsidian.timer
```

### 添加新同步文件

编辑同步脚本：
```bash
vim ~/.local/bin/sync-to-obsidian
```

在 `SYNC_FILES` 数组添加：
```bash
["新文件名.md"]="🎯 显示名称.md"
```

### 修改 Emoji 标识

编辑同步脚本，修改对应的 emoji 前缀。

---

## 备份策略

### Obsidian Vault Git 同步

如果 Obsidian Vault 使用 Git 管理：

```bash
cd ~/Obsidian\ Vault
git status
git add Charlie-Hub/
git commit -m "Update Charlie Hub docs"
git push
```

### 自动备份

可以添加到 sync-to-obsidian 脚本末尾：

```bash
cd ~/Obsidian\ Vault
git add -A
git commit -m "Auto-sync $(date +%Y-%m-%d)" || true
```

---

## 相关文件

- 同步脚本：`~/.local/bin/sync-to-obsidian`
- Service 配置：`~/.config/systemd/user/sync-obsidian.service`
- Timer 配置：`~/.config/systemd/user/sync-obsidian.timer`
- 目标目录：`~/Obsidian Vault/Charlie-Hub/`

---

**维护者**: Charlie
**创建日期**: 2026-04-07
**会话 ID**: a8efcb99-6e68-48d3-9318-6f453f05fd3e
