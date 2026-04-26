- [2026-04-26] [Sonnet] 场景：新建服务手机无法访问。根因：(1) Python http.server 默认可能绑 IPv6，必须加 `--bind 0.0.0.0`；(2) 新端口必须在 networking.nix allowedTCPPorts 或 trustedInterfaces 覆盖接口上验证可达；(3) 必须用非 localhost IP 测试（`curl http://192.168.2.100:PORT/`）才算验证通过，用 localhost 测不代表手机能访问。死规则：创建新网络服务后，MUST 用 LAN IP 测试可达性再标 [OK]。
- [2026-04-26] [Sonnet] 场景：hook 缺陷 — 对话事实未入 Letta。根因：cc-conversation-recorder.sh 的 GLM 异步分类超时 → priority 未赋值 → p>3 门槛拦截 → 消息不写 Letta。修复：移除写入门槛，所有消息直接写 Letta archival，分类结果仅作附加标注。端口映射等事实 CC 需主动写 memory/ai-cluster-architecture.md，hook 只做补充保障。
- [2026-04-26] [Sonnet] 场景：桌面黑屏+任务栏消失。根因：未知操作导致 KDE Plasma 崩溃。**禁止执行任何可能导致 plasmashell 崩溃的操作**（如大量进程并发、内存压力、强制杀进程）。修复：`systemctl --user restart plasma-plasmashell`。预防：操作前确认不会影响 Plasma 稳定性。用户明确要求下次避免。
- [2026-04-25] [GLM] 场景：用户偏好 — 创建agent/工作流前必须先搜索互联网已有开源方案，推荐给用户参考后再讨论决策。用户明确说"不要闭门造车"。触发信号：创建agent、设计工作流、选型技术方案。写入 CLAUDE.md AGENT_RESEARCH_FIRST 死规则。- [2026-04-25] [GLM-Z-Flash] 场景：plasmashell崩溃导致任务栏消失。根因：opencode job(marketing-scan/discord-butler/glm-knowledge-writer)连续失败触发大量进程，内存压力致plasmashell崩溃。修复：`systemctl --user restart plasma-plasmashell`。预防：Plasma 6 已有自动重启机制但不够快，可通过 plasma-panel-restart.timer 定时检查。
- [2026-04-25] [Sonnet] 场景：Ghostty终端整个窗口出现一堆数字乱码（第2次，情况3=全窗口）。症状：整个窗口到处都是数字。根因：**不是GPU渲染问题**，日志明确显示 `Pango: failed to create cairo scaled font, offending font 'Noto Sans 81.75', file not found`。是 Ghostty 1.3.1 + libadwaita 请求了不存在的大小变体字体。**GSK_RENDERER=ngl 无效，renderer=software 无效**。正确修复：升级 Ghostty 到 1.4+（修复了 GTK 字体问题），或降级 noto-fonts。临时方案：先用 Konsole 替代。配置：`~/.config/ghostty/config`，快捷命令：`kill-ghostty`。

### 会话摘要 [2026-04-25] [Sonnet/自动]
- 对话轮次: 128 | 被纠正: 1次
  - 用户纠正: 】我不要换模型。你执行1和三。但是以前约束过 没生效吗。

### 会话摘要 [2026-04-25] [Sonnet/自动]
- 对话轮次: 130 | 被纠正: 1次
  - 用户纠正: 】我不要换模型。你执行1和三。但是以前约束过 没生效吗。

### 会话摘要 [2026-04-25] [Sonnet/自动]
- 对话轮次: 128 | 被纠正: 1次
  - 用户纠正: 】我不要换模型。你执行1和三。但是以前约束过 没生效吗。

### 会话摘要 [2026-04-25] [Sonnet/自动]
- 对话轮次: 117 | 被纠正: 1次
  - 用户纠正: 】我不要换模型。你执行1和三。但是以前约束过 没生效吗。

### 会话摘要 [2026-04-25] [Sonnet/自动]
- 对话轮次: 110 | 被纠正: 1次
  - 用户纠正: 】我不要换模型。你执行1和三。但是以前约束过 没生效吗。
- [2026-04-26] [GLM-Z-Flash] 场景：content-creator依赖安装。根因：sourcing-site在NTFS（~/projects/实际是/mnt/pool-disks/），nix-shell依赖冲突（sphinx-9.1.0不支持python3.11）。修复：迁移到/mnt/ai/apps/content-creator/（ext4），用venv+清华镜像pip安装。教训：NTFS_BAN不仅限npm/bun，python venv也受影响。
- [2026-04-26] [GLM-Z-Flash] 场景：LiteLLM模型名错误。根因：copy_generator.py用openai-compatible/glm-4.7但LiteLLM实际注册名为glm-4.7。修复：去掉openai-compatible/前缀。教训：用curl测试/v1/models确认真实模型名。
- [2026-04-26] [GLM-Z-Flash] 场景：Hub API端口混淆。根因：workflow.py默认hub_api_url=9801但实际Hub API在9800。修复：改为9800。教训：确认前先curl两个端口。
- [2026-04-26] [GLM-Z-Flash] 场景：Mem0 Docker镜像不支持amd64。根因：mem0/mem0-api-server:latest无linux/amd64 manifest。修复：待CC用pip+venv方案替代Docker。
- [2026-04-26] [GLM-Z-Flash] 场景：AGI Telegram Bot不支持群组@提及。根因：_check_auth()只允许私聊，未检测群组entities.mention。修复：(1)添加context参数获取bot.username (2)检测update.message.entities中mention类型 (3)匹配@{bot_username}返回True (4)更新所有调用点。教训：python-telegram-bot群组@通过entities.type=="mention"检测，需offset+length提取。
