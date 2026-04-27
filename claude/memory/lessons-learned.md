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

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 133 | 被纠正: 1次
  - 用户纠正: 你刚才修改的不对啊 7699下面两个标签一个claude实时的输出 一个opencode.你刚才把claude修改了。我需要claude标签同步

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 133 | 被纠正: 1次
  - 用户纠正: 你刚才修改的不对啊 7699下面两个标签一个claude实时的输出 一个opencode.你刚才把claude修改了。我需要claude标签同步

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 131 | 被纠正: 1次
  - 用户纠正: 你刚才修改的不对啊 7699下面两个标签一个claude实时的输出 一个opencode.你刚才把claude修改了。我需要claude标签同步

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 127 | 被纠正: 2次
  - 用户纠正: 你刚才修改的不对啊 7699下面两个标签一个claude实时的输出 一个opencode.你刚才把claude修改了。我需要claude标签同步
  - 用户纠正: glm弱智没解决下面问题 你帮我看下怎么解决 ：验证错误：
event_webhooks_url: 无法验证指定的活动 webhook 网址。验证错误：
eve

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 125 | 被纠正: 3次
  - 用户纠正: 你刚才修改的不对啊 7699下面两个标签一个claude实时的输出 一个opencode.你刚才把claude修改了。我需要claude标签同步
  - 用户纠正: glm弱智没解决下面问题 你帮我看下怎么解决 ：验证错误：
event_webhooks_url: 无法验证指定的活动 webhook 网址。验证错误：
eve

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 118 | 被纠正: 3次
  - 用户纠正: 你刚才修改的不对啊 7699下面两个标签一个claude实时的输出 一个opencode.你刚才把claude修改了。我需要claude标签同步
  - 用户纠正: glm弱智没解决下面问题 你帮我看下怎么解决 ：验证错误：
event_webhooks_url: 无法验证指定的活动 webhook 网址。验证错误：
eve

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 49 | 被纠正: 1次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 69 | 被纠正: 1次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 72 | 被纠正: 1次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 75 | 被纠正: 1次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 77 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 83 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 87 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 88 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 90 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 98 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 108 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 104 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 104 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误

### 会话摘要 [2026-04-26] [Sonnet/自动]
- 对话轮次: 107 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误
- [2026-04-27] [GLM-5-turbo] 场景：百度网盘OAuth授权无法纯API绕过。百度强制要求用户交互登录（滑块/短信验证），即使Playwright无头模式也会被拦截。唯一方案：用户在手机/平板浏览器打开OAuth授权链接，手动登录后获取refresh_token。Alist BaiduNetdisk驱动只需要refresh_token即可挂载。
- [2026-04-27] [GLM-5-turbo] 场景：screenshot-watcher只监控手机(192.168.2.33)，未覆盖平板(100.104.211.70)。已修复：加入平板ADB轮询，截图保存到~/Pictures/TabletScreenshots/，共享GLM-4.6V意图识别流程。
- [2026-04-27] [GLM-5-turbo] 场景：GLM-4.6V-Flash频繁429限流。LiteLLM单模型无fallback，连续调用>3次即触发限流。需在连续调用间加sleep 10-15秒间隔。
- [2026-04-27] [GLM-5-turbo] 场景：Playwright在NixOS上必须用executablePath指定系统Chrome，且headless:true模式对百度OAuth无效（被反自动化检测）。Charlie要求：所有AI操作必须无头(headless)，不允许弹出浏览器窗口。

### 会话摘要 [2026-04-27] [Sonnet/自动]
- 对话轮次: 119 | 被纠正: 1次
  - 用户纠正: 不是以前无线连接过吗？你怎么都没有记忆？把这些都边做边记以后。然后然后边做边记的这个东西以后都要强制你怎么强制
- [2026-04-27] [GLM-5] 场景：CCT终端黑屏修复
  - 根因：ttyd 1.7.7 -I 参数完全替换页面，custom index.html 有 #terminal-container div 但缺少 xterm.js + WebSocket 连接代码（ttyd 嵌入二进制的默认 HTML 才有）
  - 修复：ttyd-cct.service 去掉 -I 参数，用 ttyd 默认 index.html 渲染终端
  - 影响：语音/复制浮动面板丢失，但 launcher index.html 已有对应浮动工具栏覆盖
  - 验证：curl 127.0.0.1:7691 确认包含 token/WebSocket/xterm/terminal-container

- [2026-04-27] [GLM-5-Turbo] 场景：读平板截图时用了 intent 缓存的旧图片而非最新截图
  症状：latest-intent.json 指向 01:15 的旧截图（tablet-screenshot.png），但平板上实际最新截图是 03:26 的
  根因：(1) ADB screencap 生成的是当前屏幕实时抓拍，不是用户保存的截图文件 (2) 未先 adb shell ls 确认平板上最新的截图文件再拉取 (3) 截图 watcher 的 intent 缓存可能过期
  修复：(1) 必须先 `adb shell ls /sdcard/DCIM/Screenshots/` 确认最新文件名和时间戳 (2) 拉取最新时间戳的截图文件，不依赖 intent 缓存 (3) ADB pull 失败时用 `adb shell cat > local` 兜底
  经验：intent 缓存只是预分析提示，绝对不能替代读取最新截图文件。平板截图路径是 /sdcard/DCIM/Screenshots/（非 /sdcard/Pictures/Screenshots/）

- [2026-04-27] [GLM-5-Turbo] 场景：Claude Code 2.1.92 通过 LiteLLM 调用 GLM-5.1 报 500 UnsupportedParamsError: openai does not support parameters: ['thinking']
  症状：CCT 终端（GLM 路由）反复重试，显示 "Retrying in 3 seconds... (attempt 5/10)"
  根因：Claude Code 2.1.92 默认发送 thinking 参数，LiteLLM glm-5.1 配置 drop_params: false 直接透传给 Z.AI OpenAI 兼容 API，Z.AI 不支持该参数
  修复：LiteLLM config.yml glm-5.1 条目 drop_params: false → true（静默丢弃不支持的参数）
  配置文件：/mnt/ai/ai-cluster/litellm/litellm-config.yml
  验证：发送带 thinking 参数的请求 → 正常返回（reasoning_content 有内容）
