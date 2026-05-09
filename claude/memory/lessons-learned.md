- [2026-05-04] [GLM-5.1] 场景：Caddy v2.11.2 WS反向代理与ttyd(libwebsockets)**不兼容**。Caddy收到101 Switching Protocols后仍尝试解析WS二进制帧为HTTP头（`malformed MIME header: "\x89\x00"`），导致502。**根因**：Caddy HTTP transport未正确切换隧道模式。**最终修复**：CCT iframe绕过Caddy，直连ttyd:7691（`http://location.hostname:7691/cct/`）。Caddy仅用于HTTP页面代理（备用），WS连接走ttyd直连。**Caddy `transport http` 非原因**，移除后问题依旧。**Python websockets库也有兼容问题**（超时），raw nc可完成WS握手。文件：index-v2.html（CCT_URL变量）+ Caddyfile
- [2026-05-04] [GLM-5.1] 场景：OpenCode Web UI在手机7699 launcher中无法选择agent。修复：在launcher的OpenCode tab上方添加agent选择按钮栏，通过`/agent` API获取agent列表，点击按钮创建新session并通过same-origin iframe DOM注入自动选择agent。文件：index-v2.html
- [2026-05-04] [GLM-5.1] 场景：手机Tailscale每5分钟被看门狗force-stop+重启，用户看到频繁切换。根因：看门狗脚本grep模式`ip link show | grep "tun[0-9].*100\.64\."`写反了——`ip link`不显示IP地址，需`ip addr show`，且输出格式是`inet 100.64.x.x/32 scope global tun0`(IP在前tun在后)。修复：grep改为`ip addr show | grep "100\.64\..*tun[0-9]"`。脚本：`/data/adb/service.d/tailscale_keep.sh`
- [2026-05-04] [GLM-5.1] 场景：LiteLLM glm-5-turbo报500 `UnsupportedParamsError: thinking`。根因：`drop_params: false`。修复：改为`drop_params: true`。配置：`/mnt/ai/ai-cluster/litellm/litellm-config.yml`
- [2026-05-03] [GLM-5] 场景：实现记忆遗忘引擎(Memory Decay Engine)。基于人脑遗忘曲线，三层衰减：(1) Letta archival清理空条目 (2) memory/*.md按文件类型差异化衰减(lessons-learned 45天, codebase-map 30天, 一次性报告7天) (3) 知识图谱孤立节点清理。衰减公式: score = importance * e^(-0.02*age) * (1+0.3*recall_count)，阈值0.15。脚本: `~/.local/bin/memory-decay-engine.py`，timer: 每周日10:00。已知问题: Letta DELETE API返回200但实际不删除（可能是版本bug），需后续排查。
- [2026-05-03] [GLM-5] 场景：OPPO PKR110 (ColorOS 16) Tailscale 老是被关闭。根因：**Karing(com.nebula.karing)的VPN隧道抢了Tailscale的VPN slot**。Android一次只能一个VPN，Karing VPN模式(tun0=10.20.0.1)占位后Tailscale无法建立隧道。修复：(1) `pm disable com.nebula.karing --user 0` 禁用Karing开机自启 (2) keepalive脚本中加`am force-stop com.nebula.karing`每5分钟杀一次 (3) Always-on VPN锁定Tailscale (4) 看门狗检测tun接口(100.64.x.x)不在则重启Tailscale。注意：首次修复时误判为ColorOS省电，实际是VPN冲突。手机端脚本：`/data/adb/service.d/tailscale_keep.sh`
- [2026-04-26] [Sonnet] 场景：新建服务手机无法访问。根因：(1) Python http.server 默认可能绑 IPv6，必须加 `--bind 0.0.0.0`；(2) 新端口必须在 networking.nix allowedTCPPorts 或 trustedInterfaces 覆盖接口上验证可达；(3) 必须用非 localhost IP 测试（`curl http://192.168.2.100:PORT/`）才算验证通过，用 localhost 测不代表手机能访问。死规则：创建新网络服务后，MUST 用 LAN IP 测试可达性再标 [OK]。
- [2026-04-26] [Sonnet] 场景：hook 缺陷 — 对话事实未入 Letta。根因：cc-conversation-recorder.sh 的 GLM 异步分类超时 → priority 未赋值 → p>3 门槛拦截 → 消息不写 Letta。修复：移除写入门槛，所有消息直接写 Letta archival，分类结果仅作附加标注。端口映射等事实 CC 需主动写 memory/ai-cluster-architecture.md，hook 只做补充保障。
- [2026-04-26] [Sonnet] 场景：桌面黑屏+任务栏消失。根因：未知操作导致 KDE Plasma 崩溃。**禁止执行任何可能导致 plasmashell 崩溃的操作**（如大量进程并发、内存压力、强制杀进程）。修复：`systemctl --user restart plasma-plasmashell`。预防：操作前确认不会影响 Plasma 稳定性。用户明确要求下次避免。
- [2026-04-25] [GLM] 场景：用户偏好 — 创建agent/工作流前必须先搜索互联网已有开源方案，推荐给用户参考后再讨论决策。用户明确说"不要闭门造车"。触发信号：创建agent、设计工作流、选型技术方案。写入 CLAUDE.md AGENT_RESEARCH_FIRST 死规则。- [2026-04-25] [GLM-Z-Flash] 场景：plasmashell崩溃导致任务栏消失。根因：opencode job(marketing-scan/discord-butler/glm-knowledge-writer)连续失败触发大量进程，内存压力致plasmashell崩溃。修复：`systemctl --user restart plasma-plasmashell`。预防：Plasma 6 已有自动重启机制但不够快，可通过 plasma-panel-restart.timer 定时检查。
- [2026-04-25] [Sonnet] 场景：Ghostty终端整个窗口出现一堆数字乱码（第2次，情况3=全窗口）。症状：整个窗口到处都是数字。根因：**不是GPU渲染问题**，日志明确显示 `Pango: failed to create cairo scaled font, offending font 'Noto Sans 81.75', file not found`。是 Ghostty 1.3.1 + libadwaita 请求了不存在的大小变体字体。**GSK_RENDERER=ngl 无效，renderer=software 无效**。正确修复：升级 Ghostty 到 1.4+（修复了 GTK 字体问题），或降级 noto-fonts。临时方案：先用 Konsole 替代。配置：`~/.config/ghostty/config`，快捷命令：`kill-ghostty`。

### 会话摘要 [2026-04-25] [Sonnet/自动]
- 对话轮次: 128 | 被纠正: 1次
  - 用户纠正: 】我不要换模型。你执行1和三。但是以前约束过 没生效吗。

- 对话轮次: 130 | 被纠正: 1次
  - 用户纠正: 】我不要换模型。你执行1和三。但是以前约束过 没生效吗。

- 对话轮次: 128 | 被纠正: 1次
  - 用户纠正: 】我不要换模型。你执行1和三。但是以前约束过 没生效吗。

- 对话轮次: 117 | 被纠正: 1次
  - 用户纠正: 】我不要换模型。你执行1和三。但是以前约束过 没生效吗。

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

- 对话轮次: 133 | 被纠正: 1次
  - 用户纠正: 你刚才修改的不对啊 7699下面两个标签一个claude实时的输出 一个opencode.你刚才把claude修改了。我需要claude标签同步

- 对话轮次: 131 | 被纠正: 1次
  - 用户纠正: 你刚才修改的不对啊 7699下面两个标签一个claude实时的输出 一个opencode.你刚才把claude修改了。我需要claude标签同步

- 对话轮次: 127 | 被纠正: 2次
  - 用户纠正: 你刚才修改的不对啊 7699下面两个标签一个claude实时的输出 一个opencode.你刚才把claude修改了。我需要claude标签同步
  - 用户纠正: glm弱智没解决下面问题 你帮我看下怎么解决 ：验证错误：
event_webhooks_url: 无法验证指定的活动 webhook 网址。验证错误：
eve

- 对话轮次: 125 | 被纠正: 3次
  - 用户纠正: 你刚才修改的不对啊 7699下面两个标签一个claude实时的输出 一个opencode.你刚才把claude修改了。我需要claude标签同步
  - 用户纠正: glm弱智没解决下面问题 你帮我看下怎么解决 ：验证错误：
event_webhooks_url: 无法验证指定的活动 webhook 网址。验证错误：
eve

- 对话轮次: 118 | 被纠正: 3次
  - 用户纠正: 你刚才修改的不对啊 7699下面两个标签一个claude实时的输出 一个opencode.你刚才把claude修改了。我需要claude标签同步
  - 用户纠正: glm弱智没解决下面问题 你帮我看下怎么解决 ：验证错误：
event_webhooks_url: 无法验证指定的活动 webhook 网址。验证错误：
eve

- 对话轮次: 49 | 被纠正: 1次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务

- 对话轮次: 69 | 被纠正: 1次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务

- 对话轮次: 72 | 被纠正: 1次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务

- 对话轮次: 75 | 被纠正: 1次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务

- 对话轮次: 77 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误

- 对话轮次: 83 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误

- 对话轮次: 87 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误

- 对话轮次: 88 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误

- 对话轮次: 90 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误

- 对话轮次: 98 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误

- 对话轮次: 108 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误

- 对话轮次: 104 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误

- 对话轮次: 104 | 被纠正: 2次
  - 用户纠正: 我现在切换tab他们连接状态不会改变对不对我不想在切换后被打断任务
  - 用户纠正: 不是说op和cc推理能力都依赖云端吗怎么会omm被杀错误

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

- [2026-04-27] [GLM-5] 场景：Hyprland 启动黑屏。根因：(1) 系统从 noGUI specialisation 启动（nomodeset禁用GPU）(2) hyprland.conf 缺少 render.explicit_sync=2（NVIDIA 555+必须显式同步）。修复：charlie.nix 添加 render{explicit_sync=2;} + __GL_GSYNC_ALLOWED/__GL_VRR_ALLOWED 环境变量 + vfr=true。重启选 "NixOS - Default"（非 noGUI）。

- [2026-04-28] [Sonnet] 场景：Hyprland 启动后1秒崩溃，SDDM循环重启导致屏幕闪烁显示乱码文字。根因：**egl-wayland 未安装**。Hyprland NVIDIA wiki明确要求 `egl-wayland` 作为 EGL↔Wayland 桥接，缺少则无法初始化显示→立即crash→SDDM反复重启→黑屏闪烁。修复：`/etc/nixos/modules/hyprland.nix` 添加 `hardware.graphics.extraPackages = [ pkgs.egl-wayland ]` 和 `environment.systemPackages` 中加入 `egl-wayland`。诊断方法：`nix-store -qR <system-derivation> | grep egl` 验证闭包是否包含 egl-wayland。注意：`nixos-rebuild switch` 遇到 dbus 实现变更时需用 `boot` 方式重启。

- [2026-05-03] [GLM-5.1] 场景：Hyprland+KDE双桌面冲突导致卡死
  - 症状：系统随机卡死，journalctl无GPU/OOM错误
  - 根因：panel-nurse-check.timer + plasmashell-crash-guard.timer 检测到 plasmashell 未运行 → 在 Hyprland 下自动启动 plasmashell → Wayland 冲突 → 崩溃风暴
  - 修复：(1) 禁用3个timer (2) mask plasma-plasmashell/kactivitymanagerd service (3) panel-nurse和crash-guard脚本加 Hyprland 检测退出
  - 教训：切换桌面环境后必须检查旧DE的守护进程/autostart/timer
- [2026-05-03] [Sonnet] 场景：系统频繁强制重启（7次/2h）。根因：krdpserver-desktop.service 反复 SIGABRT 崩溃（36次coredump），Restart=on-failure 触发无限重启循环，DrKonqi 级联崩溃(8个处理器)。修复：systemctl --user disable krdpserver-desktop.service。如需远程桌面改用 wayvnc。
- [2026-05-03] [Sonnet] 场景：Docker 16容器同时启动导致资源争抢、letta在litellm就绪前启动报429。修复：创建 /mnt/ai/ai-cluster/start-all.sh 分4层有序启动（Tier1基础设施→Tier2 LiteLLM→Tier3 AI服务→Tier4辅助），systemd user service docker-ordered-start.service 自动在登录后执行，先 docker stop 所有自动拉起的容器再有序启动。

- [2026-05-03] [Sonnet] 场景：Hyprland 屏幕顶部显示配置错误 → 原因：`render:explicit_sync` 在 Hyprland 0.54.x 已废弃（移到内部自动处理）→ 修复：删除 `/etc/nixos/home/charlie.nix` 中 `render = { explicit_sync = 1; }` 段 → `hyprctl reload` 确认无错误

### 会话摘要 [2026-05-03] [Sonnet/自动]
- 对话轮次: 128 | 被纠正: 1次
  - 用户纠正: telegram通知太频繁 取消一些没必要的 如果是成功过的 就减少通知频率 出现错误的通知才给更多的通知

- 对话轮次: 129 | 被纠正: 1次
  - 用户纠正: telegram通知太频繁 取消一些没必要的 如果是成功过的 就减少通知频率 出现错误的通知才给更多的通知

- 对话轮次: 132 | 被纠正: 1次
  - 用户纠正: telegram通知太频繁 取消一些没必要的 如果是成功过的 就减少通知频率 出现错误的通知才给更多的通知
- [2026-05-03 21:37] [GLM-5] 场景：手机无头浏览器部署
  - Termux Chromium在Android 16上EGL链接失败(eglDestroySyncKHR)，无法本地运行
  - Playwright不支持android平台(process.platform=android)
  - puppeteer-core安装成功但chromium无法启动
  - 最终方案：PC端Chrome headless :9222 + puppeteer-core API server :9922
  - 手机通过adb forward tcp:9922或Tailscale访问PC API
  - API: GET /browse?url=xxx | /screenshot?url=xxx | /pdf?url=xxx | /health
  - systemd服务: headless-browser.service
- [2026-05-04] [GLM-5.1] 场景：Claude 403 `Request not allowed` | 根因：mihomo GLOBAL 被设为 DIRECT，国内 IP 直连 anthropic 被封 | 修复：切换 GLOBAL 到 `⚡ 自动选择` | 预防：GLOBAL MUST 保持 URLTest，禁止 DIRECT | 香港 AWS IP 43.199.46.8 被 Anthropic ban，日本/美国节点可用
- [2026-05-04] [GLM-5.1] 场景：mihomo GLOBAL 反复变 DIRECT | 根因：(1)mihomo 配置文件没有 GLOBAL proxy-group，mihomo 自动创建默认 DIRECT (2)proxy-watchdog/proxy-free-fetch 下载免费订阅后 restart mihomo，覆盖了良心云配置 | 修复：在良心云配置 proxy-groups 末尾追加 GLOBAL(type=select, now=⚡自动选择) | 注意：mihomo Meta 用 type=select 不是 Selector | 自动保护：创建了 mihomo-anthemic-check.timer 每10min 检测 GLOBAL+anthropic 可达性

- [2026-05-04] [GLM] 场景：AI 架构全面审计与优化 | CLAUDE.md 从 477行/125条强制规则 精简为 119行/17条 L1核心规则，L2/L3 移入 memory/rules-secondary.md 按需加载 | 创建 cc-session-boot.sh 五合一启动脚本（Letta+OP+ARCH 3秒完成） | 禁用 5 个重叠 systemd 服务（Letta 3合1, 磁盘 3合1, 代理去重, OP去重） | 删除 20 个废弃 auto-* Skills + 10 个废弃脚本 | 重启 opencode-web 释放 508MB 内存泄漏 | Swap 从 5.6G 降至 5.0G

### 会话摘要 [2026-05-05] [Sonnet/自动]
- 对话轮次: 129 | 被纠正: 1次
  - 用户纠正: 那claude额度实在是少 用几下就没了一般人没必要把

### 会话摘要 [2026-05-05] [Sonnet/自动]
- 对话轮次: 128 | 被纠正: 1次
  - 用户纠正: 那claude额度实在是少 用几下就没了一般人没必要把

### 会话摘要 [2026-05-05] [Sonnet/自动]
- 对话轮次: 127 | 被纠正: 1次
  - 用户纠正: 那claude额度实在是少 用几下就没了一般人没必要把

### 会话摘要 [2026-05-05] [Sonnet/自动]
- 对话轮次: 126 | 被纠正: 1次
  - 用户纠正: 那claude额度实在是少 用几下就没了一般人没必要把

### 会话摘要 [2026-05-05] [Sonnet/自动]
- 对话轮次: 125 | 被纠正: 1次
  - 用户纠正: 那claude额度实在是少 用几下就没了一般人没必要把

### 会话摘要 [2026-05-05] [Sonnet/自动]
- 对话轮次: 125 | 被纠正: 1次
  - 用户纠正: 那claude额度实在是少 用几下就没了一般人没必要把

### 会话摘要 [2026-05-05] [Sonnet/自动]
- 对话轮次: 123 | 被纠正: 1次
  - 用户纠正: 那claude额度实在是少 用几下就没了一般人没必要把

- [2026-05-05] [CC] LiteLLM strip proxy: GLM API 不支持 web_search tool type，Claude Code 通过 LiteLLM 转发时报 `tools[0].type:type is illegal`。修复：strip_tools_proxy.py (4000) → LiteLLM (4002)，在 proxy 层剥离非 function 类型的 tools。LiteLLM `drop_params:true` 只丢弃参数不丢弃 tool 定义。
- [2026-05-05] [CC] LiteLLM Docker --port 参数在 v1.77.7 被忽略（监听随机端口），必须用 `PORT` 环境变量才能固定端口。
- [2026-05-05] [CC] mem0-bridge NixOS 依赖链：numpy 需 libstdc++.so.6（设 LD_LIBRARY_PATH），chromadb 需 sentence-transformers 需 torch（530MB），NixOS venv + pip 方式不适合重 ML 依赖，应用 Docker。

### 会话摘要 [2026-05-05] [Sonnet/自动]
- 对话轮次: 124 | 被纠正: 1次
  - 用户纠正: 不对啊 还是有代理问题

### 会话摘要 [2026-05-05] [Sonnet/自动]
- 对话轮次: 127 | 被纠正: 1次
  - 用户纠正: 不对啊 还是有代理问题

## systemd 服务卡住排查
- 症状: opencode web 任务卡住、其他 timer 服务不触发
- 根因: systemd job queue 被卡在 "activating" 的服务阻塞
- 排查: systemctl --user list-jobs 看是否有 pending job; systemctl --user status <service> 看是否卡在启动中
- 常见诱因: 脚本中 curl 连接 SSE/WebSocket 端点不退出（缺 --max-time），且脚本用 set -e 导致永久死锁
- 修复: systemctl --user stop <service>; systemctl --user reset-failed <service>
- 预防: 所有 curl health check 加 --connect-timeout 3 --max-time 5; 避免 curl 访问 SSE 端点（用 /health 代替）- [2026-05-07] [OP] 失败学习: Floorp中文输入 | 错误: MOZ_ENABLE_WAYLAND=1 + Wayland text-input-v3 + KWin relay | 错误: NVIDIA下KWin text-input-v3 relay不可靠，即使fcitx5-gtk的im-fcitx5.so已加载也无法回退 | 正确用法: MOZ_ENABLE_WAYLAND=0 强制XWayland，GTK IM模块直接工作 | 根因: Wayland text-input-v3协议优先级高于GTK IM模块，KWin relay在NVIDIA下不稳定
- [2026-05-07] [OP] 失败学习: auto-fix-services | 错误调用: 每小时重启失败的oneshot timer服务(nixos-full-sync/op-precheck/wechat-backup) | 错误: 造成通知风暴(TG+notify-send重复推送) | 正确用法: SKIP_PATTERNS加oneshot服务名, 不重启timer管理的服务 | 原因: auto-fix-services不区分服务类型, 对所有failed服务执行restart
- [2026-05-07] [OP] 失败学习: nixos-full-sync | 错误调用: nixos-rebuild-safe未加PATH直接调用 | 错误: 命令未找到, rebuild失败, 每小时重新触发 | 正确用法: export PATH="$HOME/.local/bin:$PATH" 在脚本开头 | 原因: systemd user service默认PATH不含~/.local/bin
- [2026-05-07] [OP] 失败学习: sshd-watchdog | 错误: /etc/nixos/sshd-watchdog.nix脚本缺少||导致每2秒无条件重启sshd | 根因: ss -tlnp | grep -q :22  systemctl restart sshd 缺少||运算符,变成每次循环都执行restart | 修复: kill进程+修复nix配置脚本语法
- [2026-05-07] [OP] 成功记录: sshd-watchdog移除 | 根因: pgrep -x sshd在sshd重启间隙匹配失败导致每2秒循环restart | 修复: 移除冗余watchdog, sshd自身Restart=always已覆盖崩溃场景, RestartSec改为10s+限频 | 结果: 稳定
- [2026-05-07] [OP] 成功记录: mihomo代理切换 | 调用: PUT /proxies/付费专线 → US 2 | 结果: claude区域封锁解除 | 场景: claude.com因HK节点被Anthropic封锁时
- [2026-05-07] [OP] 成功记录: systemd drop-in | 调用: caddy-launcher override TimeoutStopSec 10s→3s | 结果: 重启耗时10s→0.008s | 场景: 服务因活跃SSE连接导致停止超时

- [2026-05-07] [CC] Cloudflare全站封禁 → 手机SOCKS5隧道绕过方案
  - 场景: 所有70+代理节点被Cloudflare IP封禁 → claude.com/anthropic.com/discord.com不可达
  - 根因: Cloudflare 大规模封禁代理IP段（非节点/协议/地区问题），所有CF站点TLS握手超时
  - 修复: 
    (1) 利用手机(OnePlus)直连claude.com的能力(手机出口IP 115.223.199.196 未被CF封)
    (2) 创建SSH SOCKS5隧道: `ssh -D 1080 phone` via Tailscale (100.119.174.25)
    (3) mihomo添加socks5代理 + 路由规则 routing claude.com/anthropic.com → 手机隧道
    (4) systemd user service 持久化: phone-socks-tunnel.service (Type=forking + ssh -f)
  - 验证: claude.com 200(2.4s), claude.ai 302, api.anthropic.com 403, Google仍正常
  - 注意: 手机隧道仅在手机在线时可用；手机重启后systemd自动重连(RestartSec=15)
  - 命令: `ssh -NT -D 1080 -f phone` | `systemctl --user start phone-socks-tunnel`
  - 配置: /etc/mihomo/config.yaml proxy添加"📱 手机移动"到🌟付费专线组 + 路由规则

- [2026-05-08] [CC] 记忆系统全链路诊断与修复
  - 场景: 当前 Claude Code 窗口中记忆注入完全失效，lessons-learned/让塔/KG 有大量数据但不被使用
  - 根因1: cc-letta-check.sh 中 Letta REST API 返回含控制字符的 JSON，python3 json.load 报错 → 每次静默退出，零注入
  - 根因2: 意图路由硬编码为 code-assistant（9条记忆），运维问题应路由到 nixos-sysadmin（140条记忆）
  - 根因3: memory-bootstrap.sh 高频主题正则 `(?<=场景[：:] ).*` 与实际格式不匹配
  - 根因4: memory-bootstrap.sh Letta 状态检测用的 systemctl --user letta-mcp（不存在），应用 curl 检测 Docker
  - 根因5: AGENTS.md 被注入了10个重复的「记忆系统状态」块，浪费上下文窗口
  - 修复1: cc-letta-check.sh 添加 `raw.replace(控制字符)` 清理 + 意图关键词路由(ops_kw→nixos-sysadmin)
  - 修复2: memory-bootstrap.sh 正则改为 `场景[:\s]` + Letta 用 curl HTTP status 检测 + 清理逻辑改为替换而非追加
  - 修复3: AGENTS.md 运行 bootstrap 清理重复块
  - 验证: echo '{"message":"mihomo proxy"}' | cc-letta-check.sh → 命中5条nixos-sysadmin记忆
  - 子agent超时: 当前 spawn 6 个子agent全部 60-120s 超时，但最终都返回了结果

- [2026-05-08] [CC] mihomo 代理规则修复
  - 场景: Chrome/终端大量网站无法访问（cloudflare/npm/pypi/zerotier/twitter/discord全挂）
  - 根因1: 「🐟 漏网之鱼」默认 DIRECT，被墙域名没命中规则就直连
  - 根因2: 代理节点（SG/HK）IP 被 Cloudflare 封禁，TLS握手超时
  - 根因3: fake-ip DNS 缓存过期导致 Chrome 转圈（central.zerotier.com）
  - 修复1: mihomo config 添加 cloudflare/npm/pypi/zerotier/workers.dev/pages.dev → DIRECT
  - 修复2: 手动切换代理到 US_5 节点（能通所有站）
  - 修复3: curl -X POST flush fake-ip + DNS 缓存
  - 注意: mihomo 自动选择的健康检查 URL 是 google.com，选出的节点可能不通 cloudflare

- [2026-05-08] [CC] 手机 OnePlus 代理诊断
  - 场景: Google Play 无法访问，手机完全没走代理
  - 根因: Clash Meta App 没在运行，无 VPN 接口，系统代理为空
  - 手机配置: Clash Meta v0.x，config 在 /storage/emulated/0/ClashMeta/config.yaml
  - 已有: Magisk service.d/99-clash-meta.sh 开机自启脚本（但 intent 无法激活 VPN）
  - 限制: 该版本 Clash Meta 不支持 ADB intent 激活 VPN，必须通过 UI 手动点击
  - ADB 设备变化: USB(ff3ef385) + WiFi(192.168.2.37) → 5G(192.168.2.33)
- [2026-05-08] [GLM自动] 观察: 4个user服务持续failed(agl-discord-bot/discord-intelligent-bot/docker-ordered-start/letta-health-guard)，OP连接守护日志停更4天(最后5/4)，service-nurse日志停更至4/22
- [2026-05-08] [GLM自动] 观察: 4个用户服务持续failed状态: agi-discord-bot/discord-intelligent-bot/docker-ordered-start/mihomo-guardian，需排查是否已弃用可清理
- [2026-05-08] [GLM自动] 观察: LiteLLM /health返回401 auth_error但无api key参数，说明网关存活但健康检查端点需认证，非故障
- [2026-05-09] [GLM-5-turbo] 场景：overcode-loop-watch 反复误杀。根因：kill 后无冷却期，overcode 被 tmux-wrap 自动重启后再次循环。修复：添加冷却机制(5min×N次, 5次后30min停检) + 进程存活检测。文件：~/.local/bin/overcode-loop-watch.sh
- [2026-05-09] [GLM-5-turbo] 场景：memory-bootstrap.sh 高频主题全返回空值。根因：`[^|]+` 正则在多行条目匹配空串。修复：改为 `grep -oP '场景[：:]\s*\K\S+'`。文件：~/.local/bin/memory-bootstrap.sh
- [2026-05-09] [GLM-5-turbo] 场景：Letta Docker 完全消失(容器/镜像/compose目录全无)，8283不可达。重建：docker-compose.yml(letta+pgvector)，Docker Hub 拉取失败(mirror EOF)，改 pip install。加速器 docker.1ms.run 部分 blob 损坏，xuanyuan.me 不可达。
- [2026-05-09] [GLM-5-turbo] 场景：snip 偶发 SQLITE_BUSY。tracking.db 1.6MB，多进程并发写入锁竞争。非持续性bug，不影响功能。

### 会话摘要 [2026-05-09] [Sonnet/自动]
- 对话轮次: 138 | 被纠正: 2次
  - 用户纠正: 我github上没有吗 但是不要覆盖我的配置
  - 用户纠正: 但是overcode这个配置不对啊 跟关机前不一样

### 会话摘要 [2026-05-09] [Sonnet/自动]
- 对话轮次: 136 | 被纠正: 2次
  - 用户纠正: 我github上没有吗 但是不要覆盖我的配置
  - 用户纠正: 但是overcode这个配置不对啊 跟关机前不一样

### 会话摘要 [2026-05-09] [Sonnet/自动]
- 对话轮次: 135 | 被纠正: 3次
  - 用户纠正: 我github上没有吗 但是不要覆盖我的配置
  - 用户纠正: 但是overcode这个配置不对啊 跟关机前不一样

### 会话摘要 [2026-05-09] [Sonnet/自动]
- 对话轮次: 134 | 被纠正: 4次
  - 用户纠正: 我github上没有吗 但是不要覆盖我的配置
  - 用户纠正: 但是overcode这个配置不对啊 跟关机前不一样

- [2026-05-09] [GLM-5-turbo] 场景：Letta 完全消失的根因追溯
  - 症状：curl localhost:8283 返回 000，Docker 无容器/镜像，compose 目录内容丢失
  - 根因：5月8日 23:29 系统重启，docker-ordered-start 反复失败，Letta compose 未重新拉起
  - 时间线：22:42 Letta 正常 → 23:18 Docker daemon 停 → 23:29 系统重启 → Letta 再未启动
  - 重建：pip install letta==0.16.7 成功（/mnt/ai/apps/letta-venv），但需 PostgreSQL 5432
  - 阻塞：Docker 镜像拉取失败（mirror EOF），本地无 PostgreSQL，Letta 暂无法启动

- [2026-05-09] [GLM-5-turbo] 场景：mihomo 全部节点失效
  - 症状：所有境外站点 Google/GitHub/claude.ai 全 000（TLS EOF），HTTP 502
  - 根因：nodpai 订阅 155 个节点全被 GFW 封锁（TCP 通但 TLS 握手 EOF）
  - 修复：需更新订阅或切换到良心云等其他订阅
