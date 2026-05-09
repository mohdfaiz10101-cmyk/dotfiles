# Charlie Hub 操作命令速查手册

> 最后更新：2026-04-07
> 会话 ID：a8efcb99-6e68-48d3-9318-6f453f05fd3e

---

## 目录

- [Discord Bot 管理](#discord-bot-管理)
- [API Keys 配置](#api-keys-配置)
- [Systemd 服务管理](#systemd-服务管理)
- [测试和调试](#测试和调试)
- [Agent Console](#agent-console)
- [Hub API](#hub-api)
- [数据库操作](#数据库操作)
- [Git 操作](#git-操作)
- [常见问题排查](#常见问题排查)

---

## Discord Bot 管理

### 基本操作

```bash
# 启动 Discord Bot
systemctl --user start discord-bot.service

# 停止 Discord Bot
systemctl --user stop discord-bot.service

# 重启 Discord Bot
systemctl --user restart discord-bot.service

# 查看状态
systemctl --user status discord-bot.service

# 开机自启
systemctl --user enable discord-bot.service

# 取消自启
systemctl --user disable discord-bot.service
```

### 日志查看

```bash
# 实时日志
journalctl --user -u discord-bot.service -f

# 最近 50 行
journalctl --user -u discord-bot.service -n 50

# 最近 5 分钟
journalctl --user -u discord-bot.service --since "5 minutes ago"

# 过滤关键词
journalctl --user -u discord-bot.service | grep -E "ERROR|DEBUG|Received"

# 只看错误
journalctl --user -u discord-bot.service -p err
```

### Discord Bot 开发

```bash
# 编辑 Bot 代码
vim /home/charlie/hub/discord-bot.py

# 测试运行（前台）
cd /home/charlie/hub
source ~/.config/api-keys/env
./venv/bin/python3 discord-bot.py

# 检查虚拟环境依赖
./venv/bin/pip list | grep discord

# 安装新依赖
./venv/bin/pip install <package-name>
```

### Discord Developer Portal

```bash
# 获取 Bot 邀请链接（替换 CLIENT_ID）
echo "https://discord.com/oauth2/authorize?client_id=CLIENT_ID&permissions=274877922320&scope=bot"

# 从 token 提取 Bot ID（Base64 解码）
echo "MTQ5MDY0MTY3ODEzNzAzMjg0NA" | base64 -d
```

---

## API Keys 配置

### 查看配置

```bash
# 查看所有配置文件
ls -la ~/.config/api-keys/

# 查看 Shell 版本（带 export）
cat ~/.config/api-keys/env

# 查看 Systemd 版本（无 export）
cat ~/.config/api-keys/systemd.env

# 检查权限
ls -l ~/.config/api-keys/env ~/.config/api-keys/systemd.env
# 应显示：-rw------- (600)

# 验证当前环境变量
env | grep -E "API_KEY|TOKEN|PROXY"
```

### 编辑配置

```bash
# 编辑 Shell 版本
vim ~/.config/api-keys/env

# 编辑 Systemd 版本
vim ~/.config/api-keys/systemd.env

# 重新加载 Shell 环境
source ~/.config/api-keys/env

# 重启使用 API Keys 的服务
systemctl --user restart discord-bot.service
```

### 添加新 API Key

```bash
# 方法 1：手动编辑
vim ~/.config/api-keys/env
# 添加：export NEW_KEY="value"

vim ~/.config/api-keys/systemd.env
# 添加：NEW_KEY=value

# 方法 2：命令行追加
echo 'export NEW_KEY="value"' >> ~/.config/api-keys/env
echo 'NEW_KEY=value' >> ~/.config/api-keys/systemd.env

# 生效
source ~/.config/api-keys/env
systemctl --user restart discord-bot.service
```

### 安全检查

```bash
# 验证文件权限
ls -la ~/.config/api-keys/

# 检查 Git 忽略
cd ~ && git check-ignore -v .config/api-keys/env

# 查看全局 .gitignore
cat ~/.gitignore_global

# 搜索可能泄露的 Keys
grep -r "sk-\|AIza" ~/.bashrc ~/.zshrc 2>/dev/null
```

---

## Systemd 服务管理

### Charlie Hub 服务

```bash
# 重启所有 Hub 服务
systemctl --user restart charlie-hub.service hub-caddy.service discord-bot.service

# 查看所有 ttyd 服务
systemctl --user list-units "ttyd-*"

# 重启单个 ttyd
systemctl --user restart ttyd-claude.service

# 查看服务依赖关系
systemctl --user list-dependencies discord-bot.service
```

### 服务配置文件

```bash
# 查看配置文件位置
systemctl --user cat discord-bot.service

# 编辑配置
vim ~/.config/systemd/user/discord-bot.service

# 重新加载配置（修改后必须执行）
systemctl --user daemon-reload

# 验证配置语法
systemd-analyze verify ~/.config/systemd/user/discord-bot.service
```

### 批量操作

```bash
# 重启所有 Hub 相关服务
for svc in charlie-hub hub-caddy discord-bot ttyd-{claude,gemini,opencode,aider}; do
  systemctl --user restart $svc.service
done

# 查看所有服务状态
systemctl --user status charlie-hub hub-caddy discord-bot ttyd-*

# 检查失败的服务
systemctl --user --failed
```

---

## 测试和调试

### Discord Bot 测试

```bash
# 监听实时消息
journalctl --user -u discord-bot.service -f | grep -E "DEBUG|Received"

# 测试 Gemini API
source ~/.config/api-keys/env
echo "test" | gemini

# 测试 OpenCode
opencode providers list

# 查看 Bot Python 进程
ps aux | grep discord-bot.py

# 检查网络连接
curl -I https://discord.com/api/v10
```

### 服务健康检查

```bash
# Hub API 健康检查
curl http://localhost:9801/api/status | jq

# 检查端口占用
ss -tlnp | grep -E "9800|9801|7690|7691|7692|7693"

# Caddy 状态
curl http://localhost:9800/

# Letta MCP 检查
curl http://localhost:8788/sse
```

### 调试工具

```bash
# 查看 Python 虚拟环境
which python3
./venv/bin/python3 --version

# 查看已安装的包
./venv/bin/pip list

# 测试 Discord 库导入
./venv/bin/python3 -c "import discord; print(discord.__version__)"

# 检查环境变量加载
env | grep DISCORD_BOT_TOKEN | wc -c
# 应显示 token 长度
```

---

## Agent Console

### 访问终端

```bash
# 通过浏览器访问
# Claude:   http://localhost:7690
# Gemini:   http://localhost:7691
# OpenCode: http://localhost:7692
# Aider:    http://localhost:7693

# 查看 ttyd 进程
ps aux | grep ttyd

# 重启单个 Agent 终端
systemctl --user restart ttyd-claude.service
```

### 命令行直接调用

```bash
# Claude Code
claude

# Gemini CLI
gemini

# OpenCode
opencode

# Aider
aider
```

---

## Hub API

### 启动和管理

```bash
# 启动 Hub API
systemctl --user start charlie-hub.service

# 查看日志
journalctl --user -u charlie-hub.service -f

# 测试 API 端点
curl http://localhost:9801/api/status
curl http://localhost:9801/api/nav
```

### Caddy 反向代理

```bash
# 重启 Caddy
systemctl --user restart hub-caddy.service

# 查看 Caddy 配置
cat /home/charlie/hub/Caddyfile

# 测试配置
caddy validate --config /home/charlie/hub/Caddyfile

# 查看 Caddy 日志
journalctl --user -u hub-caddy.service -f
```

---

## 数据库操作

### AGI Brain 数据库

```bash
# 数据库位置
/home/charlie/agi/agi.db

# 查看表结构（需要 sqlite3）
# sqlite3 /home/charlie/agi/agi.db ".schema"

# 备份数据库
cp /home/charlie/agi/agi.db /home/charlie/agi/agi.db.backup-$(date +%Y%m%d)

# 查看数据库大小
du -sh /home/charlie/agi/agi.db
```

### Letta 记忆查询

```bash
# 通过 API 查询
curl -H "Authorization: Bearer letta" \
  "http://localhost:8283/v1/agents/<agent-id>/archival-memory?limit=10"

# 通过 Discord Bot
# 在 Discord 中：/search <keyword>
```

---

## Git 操作

### Discord Bot 提交

```bash
cd /home/charlie/hub

# 查看状态
git status

# 提交前检查敏感信息
grep -r "sk-\|AIza\|MTQ5" .

# 添加文件
git add discord-bot.py

# 提交（带 Co-Authored）
git commit -m "$(cat <<'EOF'
feat: add Discord Bot with smart routing

- Intelligent agent routing based on message content
- Support for Claude/Gemini/OpenCode
- AGI Brain alerts integration
- Auto-channel creation

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

### 配置保护

```bash
# 查看全局 .gitignore
cat ~/.gitignore_global

# 添加新规则
echo "new-pattern" >> ~/.gitignore_global

# 验证文件是否被忽略
git check-ignore -v ~/.config/api-keys/env
```

---

## 常见问题排查

### Discord Bot 无响应

```bash
# 1. 检查服务状态
systemctl --user status discord-bot.service

# 2. 查看最近日志
journalctl --user -u discord-bot.service -n 50

# 3. 检查 Token 是否加载
journalctl --user -u discord-bot.service | grep "DISCORD_BOT_TOKEN"

# 4. 验证网络连接
curl -I https://discord.com/api/v10

# 5. 检查代理设置
env | grep -i proxy
```

### Gemini API 配额耗尽

```bash
# 查看错误信息
journalctl --user -u discord-bot.service | grep "429"

# 检查 API Key
echo $GEMINI_API_KEY

# 监控使用量（浏览器）
# https://ai.dev/rate-limit

# 临时方案：使用其他 Agent
# 在 Discord #cc 频道：@claude <你的问题>
```

### OpenCode 无法启动

```bash
# 检查 GLM API Key
opencode providers list

# 重新登录
opencode providers login

# 查看可用模型
opencode models

# 清理缓存
rm -rf ~/.local/share/opencode/cache
```

### npm symlink 错误

```bash
# 查看 npm cache 位置
npm config get cache

# 全局安装包
npm install -g @google/gemini-cli

# 验证安装
which gemini
ls -la ~/.npm-global/bin/gemini
```

### 服务启动失败

```bash
# 查看详细错误
systemctl --user status discord-bot.service

# 查看完整日志
journalctl --user -xe -u discord-bot.service

# 检查配置语法
cat ~/.config/systemd/user/discord-bot.service

# 重新加载 daemon
systemctl --user daemon-reload

# 前台运行调试
cd /home/charlie/hub
source ~/.config/api-keys/env
./venv/bin/python3 discord-bot.py
```

---

## 快速参考

### 一键重启所有服务

```bash
systemctl --user restart charlie-hub hub-caddy discord-bot ttyd-{claude,gemini,opencode,aider}
```

### 一键查看所有状态

```bash
systemctl --user status charlie-hub hub-caddy discord-bot ttyd-* --no-pager
```

### 一键查看所有日志

```bash
journalctl --user -u charlie-hub -u hub-caddy -u discord-bot -n 100
```

### 紧急停止

```bash
# 停止所有 Hub 服务
systemctl --user stop charlie-hub hub-caddy discord-bot ttyd-*

# 杀死所有相关进程
pkill -f "discord-bot.py"
pkill -f "hub-api.py"
pkill -f "ttyd"
```

---

## 相关文档

- 完整部署文档：`/home/charlie/hub/README.md`
- API Keys 说明：`~/.config/api-keys/README.md`
- Discord Bot 测试：`/home/charlie/hub/discord-bot-test-guide.md`
- 行为规则：`~/CLAUDE.md`
- 经验记录：`~/.claude/projects/-home-charlie/memory/lessons-learned.md`

---

**维护者**: Charlie
**创建日期**: 2026-04-07
**自动同步**: Obsidian Vault

---

## 浏览器管理

### Floorp 配置

```bash
# 修复后台弹窗问题
floorp-popup-fix

# 查看配置文件位置
ls -la ~/.floorp/*/prefs.js

# 备份配置
cp ~/.floorp/rw7f0w9p.default/prefs.js ~/.floorp/prefs.js.backup

# 清除浏览数据（需在 Floorp 内执行）
# 设置 → 隐私与安全 → 清除数据

# 重置 Floorp（需在 Floorp 内执行）
# 帮助 → 更多故障排除信息 → 重置 Floorp
```

### 弹窗控制（about:config）

```bash
# 关键配置项
dom.disable_open_during_load = false      # 允许页面加载时弹窗
dom.popup_maximum = 50                     # 最大弹窗数
privacy.popups.showBrowserMessage = false  # 不显示拦截提示
dom.allow_scripts_to_close_windows = true # 允许脚本关闭窗口
```

---

---

## Windows 主机（192.168.2.36）最效率操作速查

> 更新：2026-04-22 [Sonnet]
> **SSH最快路径**：`ssh G@192.168.2.36`（密码 `1`）

### 命令执行模板
```bash
# 单条命令（无交互）
ssh G@192.168.2.36 "cmd /c \"你的命令\""

# PowerShell（推荐用于文件/注册表）
ssh G@192.168.2.36 "powershell -NoProfile -Command \"你的PS命令\""

# 读文件（跨行内容）
ssh G@192.168.2.36 "type C:\\path\\to\\file" 2>/dev/null

# 上传文件到Windows
scp /本地路径 G@192.168.2.36:C:/Users/G/Desktop/

# 下载文件到本地
scp G@192.168.2.36:"C:/Users/G/Desktop/文件" /tmp/
```

### 常用场景
| 场景 | 命令 |
|------|------|
| 检查微信进程 | `ssh G@192.168.2.36 "tasklist | findstr WeChat"` |
| 启动微信 | `ssh G@192.168.2.36 "start /b C:\\Program Files\\Tencent\\Weixin\\Weixin.exe"` |
| 读注册表 | `ssh G@192.168.2.36 "reg query HKCU\\Software\\Tencent\\WeChat"` |
| 定时任务 | `ssh G@192.168.2.36 "schtasks /query /tn 任务名"` |
| 设置环境变量 | `ssh G@192.168.2.36 "setx VAR_NAME value"` |
| 代理配置 | 用 mihomo `192.168.2.100:7890` |

### 反复踩坑（NEVER做）
- ❌ 不要用 `&` 后台，SSH会话断开进程也死（用 `start /b`）
- ❌ 路径用正斜杠 `/` 在PowerShell可以，`cmd /c` 下必须用 `\\`
- ❌ 中文乱码：ssh前加 `LANG=zh_CN.UTF-8` 或PowerShell用 `-OutputEncoding UTF8`
