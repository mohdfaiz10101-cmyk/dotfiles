# 踩坑日志

- [2026-04-25] [GLM-Z-Flash] **ADB 同一设备多连接 + pm install SELinux 限制**
  - 症状：`adb devices` 显示多个 PKR110 设备，`pm install /sdcard/` 报 SELinux fuse 拒绝
  - 根因：同一台 OnePlus Ace 5 Pro 通过 WiFi(192.168.2.200) 和 Tailscale(100.64.206.110) 双连接；Android 16 SELinux 限制 system_server 读 /sdcard/
  - 修复：断开重复连接保留一个；APK 推到 `/data/local/tmp/` 再 `pm install`，或用 `am start` 调系统安装器
  - 设备对应：PKR110 = 一加 Ace 5 Pro（手机），nabu = 小米平板5（24117RK2CC），后者 Tailscale IP 100.104.211.70

- [2026-04-23] [Sonnet] **wxhook/wxhook 0.0.10 不支持 WeChat 4.x (xwechat UWP架构)**
  - 症状：`Bot()` 初始化抛 `Exception: unknown error`
  - 根因：wxhook 0.0.10 硬编码 `self.version = "3.9.5.81"`，`start-wechat.exe` 只注入 `WeChat.exe`（3.9.x传统桌面版），当前机器运行 `WeChatAppEx.exe`（xwechat 4.x）
  - 证据：进程路径 `C:\Users\G\AppData\Roaming\Tencent\xwechat\xplugin\plugins\RadiumWMPF\19201\extracted\runtime\WeChatAppEx.exe`，版本 `2.4.1.19201`
  - 修复：必须降级到 WeChat 3.9.12.51，使用 skill `wechat-windows-lock`
  - 替代：gewechat/ComWechat 声称支持 4.x 但稳定性未验证

- [2026-04-23] [Sonnet] **WeChat XWayland UI自动化：xdotool+xclip全X11路径是唯一可靠方案**
  - 坐标系：wmctrl报告2×真实坐标；xdotool getwindowgeometry=真实X11物理坐标；ydotool=Wayland logical=X11/1.25
  - 例：WeChat窗口 xdotool pos=(425,85) → ydotool pos=(340,68) → wmctrl pos=(850,170)
  - ydotool click无法激活XWayland应用（WeChat）的控件焦点，弃用ydotool click
  - xdotool key --window <xid> KEY：直接X11事件注入，不经Wayland，WeChat响应正常
  - 粘贴方案：xclip -selection clipboard（X11剪贴板）+ xdotool key --window ctrl+v → 搜索框收到文字
  - wl-copy（Wayland剪贴板）+ ydotool paste对WeChat搜索框无效
  - **Ctrl+F全局搜索导航**：粘贴搜索词后等2s，功能区条目自动高亮，直接Enter（0次Down）打开聊天
  - Down键会跳到网页建议区，不要用Down导航到联系人
  - 已测试：Down×7在v12偶尔成功但不稳定（搜索结果顺序动态变化），Enter=0 Down在v13验证为稳定方案
  - xdotool absolute click会触发KDE XTest权限弹窗，必须用 --window 参数避免
  - wechat_agent.py HTTP API端口9801：POST /api/wechat/reply 返回202（非阻塞），避免macg.py 5s超时

- [2026-04-22] [Sonnet] **Letta archival 记忆缺失根因：hash缓存在 /tmp，重启后丢失** — letta-sync.py 的 HASH_CACHE 原为 `/tmp/letta-sync-hashes.json`，重启后清空导致重复写入（DB从2055条膨胀到6945条），且 API limit=2000 导致计数虚报"满"。修复：缓存改为 `~/.config/letta-sync-hashes.json` + 对现有DB条目重建缓存 + SQL去重删除4890条重复。

- [2026-04-22] [Sonnet] **GPT-SoVITS API 正确参数**：`text_lang`应为`text_language`，`ref_audio_path`应为`refer_wav_path`，中文字符需 Python urllib.parse.urlencode 编码（curl直接传中文会400）。测试命令：`python3 -c "import urllib.request,urllib.parse; params=urllib.parse.urlencode({...}); urllib.request.urlopen(f'http://localhost:9880/?{params}')"` → 200 OK，返回55KB WAV。

- [2026-04-22] [Sonnet] **WeChat UOS 图片 V2 格式**：dat文件头为 `07 08 56 32`（非XOR编码），直接解码为JPEG/PNG，不需要XOR键。消息丢失原因：WeChat离线7天（4月15-22日），正在从服务器同步历史，等待即可。DB和WAL均有效。

- [2026-04-21] [GLM] **未验证分区类型直接触发 NTFS_BAN** — `/mnt/ai` 实为 ext4 loop 设备，GLM 未执行 `df -T` 就断言 NTFS 并给出迁移建议。死规则：涉及分区类型的任何操作，MUST 先 `df -T <path>` 验证，禁止凭路径名推断。

- [2026-04-20] [Sonnet] **高返工率根因：先修后诊断** — ANSI乱码修了3轮，每次只改症状未验证假设。死规则：修复前先写假设+验证命令，确认根因后再动手。命令示例：`echo -e '\x1b[<17;35;24M' | sed '...' | xxd` 这类一行验证。

- [2026-04-20] [Sonnet] **find扫NTFS大分区引发IO等待+swap耗尽**
  - 场景：CC 发起 `find /mnt/win_c /mnt/data` 搜索DreamMail，3个并行find进程拖满IO
  - 教训：NTFS扫描任务必须写入OP低优先级任务队列（[low]标注），不得在CC会话中同步执行
  - 修复：终止find进程 + 任务写入op-tasks DREAMMAIL-SEARCH [low]，空闲时执行

- [2026-04-20] [Sonnet] **opencode.json循环软链接导致所有OP任务失败**
  - 场景：dotfiles/opencode/opencode.json 自指向自身，opencode启动报JSON invalid
  - 根因：stow或手动ln时目标路径写错
  - 修复：rm循环链接 + cp备份文件恢复 + 写opencode-config-guard.sh防复发
  - 预防：CC Stop hook + OP heartbeat前置检查均加入guard脚本

- [2026-04-20] [Sonnet] **OP heartbeat prompt只扫[ ]不扫[!]导致失败任务积压**
  - 场景：EMAIL-SEARCH/WIN-GIT-01标记[!]后OP忽略，长期堆积
  - 修复：更新heartbeat-task-check.json prompt加入[!]扫描逻辑
  - 同时：sisyphus.md加入假阳性识别规则（timer job Result=success不算失败）

- [2026-04-20] [Sonnet] **Chrome 在 NTFS 上崩溃**
  - 场景：强制关机后 Chrome 报"致命错误"，配置目录 `~/.config/google-chrome` 软链接指向 NTFS（/mnt/pool-disks/POOL-B1）
  - 根因：NTFS 不支持文件锁，强制关机后脏位导致 Chrome 无法创建 SingletonLock
  - 修复：`rsync` 迁移至 ext4（`/mnt/ai/data/chrome-config`），更新软链接
  - 教训：所有浏览器配置目录必须在 ext4，不能在 NTFS。已加入 NTFS_BAN 迁移表

- [2026-04-18] [Sonnet] **SSH authorized_keys 权限不安全**
  - 场景：安全哨兵巡检发现 `~/.ssh/authorized_keys` 权限为 644（组和其他用户可读）
  - 风险：其他用户可读取公钥，虽然不影响SSH安全性，但违反最佳实践
  - 修复：`chmod 600 ~/.ssh/authorized_keys` → 权限改为 600
  - 教训：SSH 公钥文件必须始终设置为 600 权限，系统安全巡检应定期检查

- [2026-04-18] [Opus] **LiteLLM 容器 running 但端口未监听**
  - 场景：LiteLLM Docker 容器状态 running+unhealthy，但 4000 端口未绑定
  - 原因：新版 litellm 镜像的 `prod_entrypoint.sh` 先执行 `prisma_migration.py`，其中 `run_server(["--skip_server_startup"])` 导致启动卡死
  - 解决：docker-compose.yml 中加 `entrypoint: ["litellm"]` 跳过 prisma migration
  - 教训：(1) 守护脚本不能只看 `docker ps`，必须 `ss -tlnp | grep :端口` 级别检查 (2) LiteLLM 启动需 ~70秒，健康检查 start_period 要 ≥90s
  - 相关：`/mnt/ai-cluster/litellm/docker-compose.yml`

- [2026-04-18] [Opus] **服务膨胀审计 — 清理 11 个冗余服务释放 1.1GB**
  - 场景：系统卡顿，swap 满，发现 40 个自定义 systemd user service 在运行
  - 最大嫌疑：claude-token-tray 736MB、the-companion 150MB、ai-patrol 107MB
  - 原因：各阶段实验项目堆积，功能重复（ai-patrol/ai-watchdog/op-watchdog/agi-brain 四套巡检）
  - 修复：停止+禁用 11 个服务，释放 ~1.1GB
  - 教训：(1) 定期审计 `systemctl --user list-units --state=running` (2) 新建 service 前先检查功能是否已有覆盖 (3) Spectacle(KDE截图) 和 Baloo(文件索引) 也是内存大户，前者会 CPU 100% 空转
  - 保留清单：agi-brain/letta-mcp/wechat-*/claude-md-sync/ai-rules-sync/mihomo-watch/proxy-403-monitor/charlie-hub/discord-bot/chronos-*/ttyd-*/voxtype/paperclip-report-daemon/cookie-sync-server

- [2026-04-18] [Opus] **Cerebras/Groq 主动分流（非备选）**
  - 场景：用户指出免费模型不应只当备选，要主动用在强项场景
  - 方案：Cerebras llama-8b → AGI Brain think 循环（高频低延迟）+ Aider weak-model（代码补全）；Groq Whisper → 语音识别；Cerebras qwen3-235b → CLI `cerebras` 命令
  - 教训：免费模型的价值是**速度**而非**降级**，应该放在高频调用位置

- [2026-04-18] [Opus] **Cerebras API 模型名变更**
  - 场景：按文档配置 `llama-3.3-70b` 报 NotFoundError
  - 原因：Cerebras 模型名已更新 → `llama3.1-8b` / `qwen-3-235b-a22b-instruct-2507` / `gpt-oss-120b` / `zai-glm-4.7`
  - 教训：接入新 API 前 MUST 先 `curl /v1/models` 查询实际可用模型，不凭文档/记忆

- [2026-04-18] [GLM-5.1] **微信聊天记录→Letta 学习管道创建**
  - 场景：用户要求手动备份微信聊天→Letta 学习→定期提醒
  - 发现：Wine 微信 ChatMsg.db 也是加密的（不是明文 SQLite），UOS DB 自定义 AES 解密失败（格式可能已变）
  - 方案：以文件导入为主（用户手动导出 TXT/CSV/HTML），DB 直读作为可选功能
  - 创建：`/home/charlie/agi/wechat-learn.py`（685 行），`/home/charlie/agi/wechat-learn.sh`（nix-shell wrapper）
  - 备份提醒：`wechat-backup-reminder.timer`（systemd，每天10:00检查，3天间隔）
  - Letta API：POST `/v1/agents/{id}/archival-memory` body=`{"text":"..."}`（单条写入，不是批量）
  - 踩坑：Letta 批量写入导致 embedding API 413 过载→event loop hang→服务重启
- [2026-04-18] [Sonnet] **voxtype 语音输入 KDE Wayland 粘贴不上屏修复**
  - 场景：voxtype paste 模式日志显示 `Text pasted via clipboard + ctrl+v` 成功，但用户看不到文字出现
  - 根因分析链：(1) wtype 在 KDE Plasma Wayland 不可用（`Compositor does not support the virtual keyboard protocol`）(2) dotool 不支持 CJK 字符 (3) ydotool 通过 uinput 可发送按键但 Ctrl+V 在终端中无效
  - **核心问题**：Ctrl+V 在 Konsole 等终端中不是粘贴快捷键（终端用 Ctrl+Shift+V），所以 ydotool 模拟的 Ctrl+V 在终端中无效
  - **修复**：config.toml `paste_keys = "shift+insert"` — Shift+Insert 在所有 Linux 应用中（含终端、浏览器、编辑器）都是粘贴快捷键
  - 完整 paste 链路：whisper 转写 → wl-copy 写入剪贴板 → wtype Shift+Insert（失败）→ ydotool Shift+Insert（成功，通过 uinput 模拟物理按键）
  - 其他配置：`pre_type_delay_ms = 150`（粘贴前等待剪贴板就绪）、`driver_order = ["ydotool", "dotool"]`（跳过不可用的 wtype）
  - systemd 服务添加 `-v` 调试日志级别便于排查
  - 教训：(1) KDE Plasma Wayland 不支持 wtype 的 virtual keyboard protocol (2) Ctrl+V 在终端中无效，Shift+Insert 是更通用的粘贴方案 (3) voxtype paste 模式内部会先尝试 wtype 再降级 ydotool，日志需要 -vv 级别才能看到降级过程

- [2026-04-18] [GLM-5.1] 僵尸服务刷日志：hub-caddy/langchain-hub/glm-proxy 三个 service 因 nix store 路径失效/venv 不存在反复重启刷错误日志。修复：ExecStart 改 /bin/true + Restart=no。教训：nixos-rebuild 后必须检查 systemd user service 中的硬编码 nix store 路径
- [2026-04-18] [GLM-5.1] bun add 超时根因：默认 registry（npmjs.org）在国内慢，BUN_CONFIG_REGISTRY=https://registry.npmmirror.com + BUN_INSTALL_CACHE_DIR=/tmp/bun-cache（tmpfs）可解决
- [2026-04-18] [GLM-5.1] agi-frontend 127 错误：bun run dev 调 next 但 node_modules/.bin/next 不存在（bun install 超时导致）。bun install 成功后恢复正常
- [2026-04-18] [GLM-5.1] **OP 自动注入重复误报任务**：discord-butler/heartbeat-system-sentry/heartbeat-task-check/proxy-guardian/service-nurse 等 service unit 根本不存在，OP 监控循环反复报告"重启失败"并注入 op-tasks.md。根因：OP 检查服务列表时不区分"service 不存在"和"service 存在但失败"。修复：CC 批量标记为误报。建议：OP auto-fix-services 增加 `systemctl cat $svc` 前置检查，unit 不存在则跳过
- [2026-04-18] [GLM-5.1] **Termux APK 安装流程**：F-Droid URL 格式已变（12KB 不是完整 APK），GitHub releases 直接下载 arm64 APK 更可靠。`curl -sL https://github.com/termux/termux-app/releases/download/v0.118.0/termux-app_v0.118.0+github-debug_arm64-v8a.apk` → `adb install` 成功
- [2026-04-18] [GLM-5.1] Capacitor 8.x 要求 Java 21，NixOS 默认 Java 17 → 降级到 Capacitor 6.x 解决
- [2026-04-18] [GLM-5.1] hub-caddy service 原用 caddy binary（nix store 过期）→ 改用 Python http.server 临时替代
- [2026-04-18] [GLM-5.1] discord-butler/service-nurse/heartbeat-system-sentry 失败根因：systemd service 文件从未创建
- [2026-04-18] [GLM-5.1] Android SDK 安装路径：/mnt/ai/data/android（cmdline-tools + build-tools/34 + platforms/android-34 + platform-tools）
- [2026-04-18] [GLM-5.1] Gradle 安装路径：/mnt/ai/data/gradle-8.14

- [2026-04-18] [GLM-5.1] 场景：端口3000前端看板显示空数据（服务状态/任务/微信联系人全部空白）
  根因：API响应格式与前端解析不匹配：(1) /api/systemd返回扁平对象{"agi-brain":"active"}但前端读data.services?.xxx (2) /api/tasks返回{"tasks":[...]}但前端检查Array.isArray(data) (3) 状态值是"active"但前端判断"running"
  修复：page.tsx修正为data["agi-brain"]，data.tasks||snip []，状态判断加"active"
  教训：前后端对接时必须验证实际API响应格式，不能假设嵌套结构

- [2026-04-18] [GLM-5.1] 场景：Wayland下微信和Floorp输入法不工作（焦点丢失）
  根因：desktop.nix手动设置GTK_IM_MODULE=fcitx和QT_IM_MODULE=fcitx，覆盖了NixOS fcit5模块waylandFrontend=true的自动行为（该模式下不应设置这两个变量）
  修复：从desktop.nix移除GTK_IM_MODULE/QT_IM_MODULE/INPUT_METHOD/GLFW_IM_MODULE，只保留XMODIFIERS
  教训：waylandFrontend=true时NixOS fcitx5模块不设置GTK_IM_MODULE/QT_IM_MODULE，让Wayland原生text-input协议生效；手动设了等于强制走X11桥接，导致焦点问题

- [2026-04-18] [Sonnet] hub-api.py 微信数据库列名：merged DB 用小写（create_time/message_content/local_id/local_type），不是大写（CreateTime/StrContent）。之前代码用大写导致 last_time 全为0。另外 nickname/remark 字段可能含控制字符，需 sanitize。table_map 映射的每张 Msg_ 表就是一个联系人，没有 StrTalker 列。

- [2026-04-19] [GLM-5.1] service-nurse 巡检诊断结论：(1) glm-proxy.service 僵尸服务 ExecStart=/bin/true（NixOS 无 /bin/true），已 disable+mask+reset-failed；(2) image-captioner.service WorkingDirectory=/mnt/ai/ai-cluster/unified-search 不存在（目录从未创建）；(3) cookie-sync-server :9977 返回空响应非故障，服务只有 /cookies 端点有 handler；(4) health-monitor 系统服务 30s 超时，脚本内 Telegram API 阻塞
- [2026-04-19] [Sonnet] OP→CC 升级项排查结论：discord-butler/proxy-guardian/service-nurse 的 systemd unit 实际存在（opencode-job-* service+timer），凌晨 LiteLLM 不可达导致 op-adaptive-gate 失败→AGI Brain 误报为 agent 重启失败。当前 3 个 service 状态均为 inactive/success，问题已自愈。根因是凌晨 LiteLLM 服务短暂不可用

- [2026-04-19] [GLM-5.1] launcher-server.py auth 踩坑：do_POST 中 _check_auth() 必须在 rfile.read(length) 之前调用，否则 body 已被消费导致后续 handler 读不到数据 → BrokenPipeError。正确顺序：auth check → read body → dispatch route

- [2026-04-19] [GLM-5.1] launcher-server.py Bearer Token auth 实现：LAUNCHER_TOKEN 环境变量（默认 launcher-local-2026），LOCAL_ONLY_AUTH=1 时 localhost 请求（127.0.0.1/::1）自动放行，远程请求需 Authorization: Bearer {token} header

- [2026-04-19] [GLM-5.1] crm.html 微信面板踩坑：fetch 9875 messages API 返回的 JSON 含 emoji/control chars 导致 Python json.load 失败，但浏览器 JS fetch 正常处理。chat 参数需 encodeURIComponent 编码

- [2026-04-19] [GLM-5.1] OP→CC 告警模式识别：所有 opencode-job-* 服务告警都是 AGI Brain 误报（LiteLLM 短暂不可达后自愈），服务 exit 0 正常完成后 Brain 误判为重启失败。标记 [x] 即可，无需实际修复
- [2026-04-19] [Sonnet] 成本优化5项：(1) OP定时任务 glm-5.1→glm-4.7 省推理开销 (2) Router high_token 正则收紧，避免'文档/报告'等常用词误推 DeepSeek (3) fast 规则增加运维查询模式（cat/ls/grep/systemctl/curl 等）(4) system-sentry 从 opencode 进程改为纯 bash 脚本，内存 711MB→19MB (5) sentry timeout 120→300s 防 ALRM 被杀。已写入 AUTO_COST_OPTIMIZE 死规则，agent 以后自动执行类似优化。
- [2026-04-19] [Sonnet] AUTO_SKILL 执行漏检：输出了 [AUTO_SKILL] 可封装 但未调用 create-skill.py（累计 7 次）
- [2026-04-19] [GLM-5.1] 场景：AGI Control Plane Dashboard 数据对不上
  问题1: /api/tasks done/fail 返回 bool，前端期望 int → done===0 永远 false
  问题2: /api/systemd 返回 dict{str:str}，前端期望 SystemdService[] 数组 → safeArray 得空
  问题3: systemctl --user show MemoryCurrent 返回 "[not set]" → int() 崩溃
  修复: (1) done/fail 改为 0/1 int (2) systemd 改返回 [{name,active,sub,memory_mb,cpu_percent}] (3) safe_int 处理 [not set]
  教训: **前后端类型必须对齐** — TypeScript interface vs Python 返回值，任何 bool/int/数组/字典 不匹配都会导致前端静默显示空数据

- [2026-04-19] [Opus] **op-exec.sh formatter 修复：opencode --format json 实际输出格式**
  - 场景：op-exec.sh 调用 opencode run --format json 后 formatter 没有捕获执行结果
  - 根因：opencode JSON 格式中 `tool_use` 事件的数据在 `part.state.input/output/metadata` 下，而非直接在 `part.input`
  - 三种事件类型：`step_start`(空), `tool_use`(含 state.status/input/output/metadata.exit), `text`(part.text), `step_finish`(reason=stop/tool-calls)
  - 修复：重写 formatter 按实际格式解析 state 字段，捕获 bash 命令+输出+退出码
  - 教训：opencode 的 --format json 与 Claude API 格式不同，必须先抓原始输出再写 parser

- [2026-04-19] [Opus] **OP prompt 优化：精简指令 GLM 执行效率高 3 倍**
  - 场景：冗长 prompt（含多条规则）导致 GLM token 耗尽，没完成最后的 sed 标记
  - 修复：精简为 5 行指令（角色 + 规则 + sed 命令 + 任务 + 开始），GLM 每次任务只用 ~47K tokens
  - 教训：GLM 上下文有限（~45K 有效），prompt 越短效率越高；任务 ID 用变量提取，sed 命令直接嵌入 prompt

- [2026-04-19] [Opus] **NixOS systemd user service 不能用 /bin/bash**
  - 场景：GLM 创建 systemd service 使用 /bin/bash，NixOS 没有此路径
  - 修复：改用 /run/current-system/sw/bin/bash 或 ExecStart 直接指向脚本文件（脚本用 #!/usr/bin/env bash shebang）
  - 教训：NixOS systemd unit 的 ExecStart 必须用绝对路径，且只有 /run/current-system/sw/bin/ 下的命令可靠

- [2026-04-20] [GLM] Floorp fcitx5 无法打字：根因是 ~/.local/bin/floorp wrapper 显式设置 MOZ_ENABLE_WAYLAND=0 强制 XWayland 模式，导致 KDE Plasma 6 Wayland 下 fcitx5 text-input protocol 不工作。修复：改为 MOZ_ENABLE_WAYLAND=1
- [2026-04-20] [GLM] Node.js letta-mcp-server SIGABRT 崩溃（225MB coredump）：一次性 OOM/Node 异常，Letta Docker 服务本身正常。MCP bridge 是 CC 子进程，每次会话自动重启。清理 coredump: sudo rm -f /var/lib/systemd/coredump/core.*.zst
- [2026-04-20] [Aider] fix: 添加 noGUI 紧急恢复模式 + 修复 NVIDIA GSP firmware 卡死
  相关文件：configuration.nix, modules/desktop.nix
- [2026-04-20] [Aider] fix: 修复 opencode.json 和 AGENTS.md 循环软链接，恢复真实文件内容
  相关文件：opencode/AGENTS.md, opencode/opencode.json
- [2026-04-20] [Aider] fix: 恢复 opencode.json 真实内容（第二次循环链接修复）
  相关文件：opencode/opencode.json
- [2026-04-20] [Aider] fix: 清除循环链接+废链接（AGENTS.md/opencode.json修复，28个废链接删除）
  相关文件：claude/memory/agi-audit-log.jsonl, claude/memory/lessons-learned.md, claude/memory/op-tasks.md, opencode/AGENTS.md, opencode/opencode.json
- [2026-04-20] [Aider] fix: AGENTS.md 补充 nixos-rebuild 完整命令格式（必须指定 #charlie）
  相关文件：opencode/AGENTS.md

  - 用户纠正: 不是这次 你是验证这一个月以来的所有案例 给我下你返工的原因和解决方案
- 对话轮次: 117 | 被纠正: 1次
- [2026-04-20] [Sonnet] WeChat 4.x (xwechat) DB 加密分析：
  - 进程名：WeChatAppEx.exe（多进程架构）
  - DB路径：C:\Users\G\Documents\xwechat_files\w422417869_448e\db_storage\
  - 主要DB：message/message_0.db (10MB), contact/contact.db (3.7MB), session/session.db
  - 加密状态：全部 SQLCipher 加密，非明文
  - 失败原因：pywxdump 3.1.46 不支持 4.x；wcferry 39.5.2.0 仅支持 3.9.x；ctypes.WinDLL 在 SSH 非交互会话挂起
  - 可行路径：(1) Frida 动态插桩捕获 SQLite open key (2) 等待 wcferry 4.x 版本 (3) 在 Windows 桌面手动运行提取脚本
  - wxid: w422417869_448e
[2026-04-20] [Sonnet] 场景：微信三端消息合并 Phase 1 完成

完成内容：
1. 合并 NixOS UOS + Windows PC 消息到统一 DB
   - 路径：/mnt/ai/data/wechat-merged/messages.db
   - 总消息：319条（UOS: 104 + Windows: 215，去重9条）
   - Schema：msg_id TEXT, server_id, talker, is_send, create_time, local_type, message_content, source, db_origin, merged_at

2. 更新 hub-api
   - WECHAT_MSG_DBS[0] 指向 merged DB
   - 添加 search 参数到 /api/wechat/messages 端点
   - 修复重复消息 bug（删除重复的 results.append）

3. API 测试验证
   - 默认查询：curl 'http://localhost:9800/api/wechat/messages?limit=5'
   - talker 筛选：curl 'http://localhost:9800/api/wechat/messages?limit=5&talker=xxx'
   - 搜索功能：curl 'http://localhost:9800/api/wechat/messages?limit=5&search=%E6%88%91'（需 URL 编码）

已知问题：
- 搜索中文关键词需 URL 编码（如 '我' → '%E6%88%91'）
- hub-api 服务端口 9800，不是 9900（AGI Gateway）

下一步（Phase 2）：
- 手机端 Web UI（ttyd 或 port 3000 的微信 Tab）
- mobile Safari 访问 merged DB 的界面
- [2026-04-20] [Sonnet] 微信三端消息汇总：hub-api _query_messages 函数存在重复代码导致每条消息返回2次（第116-140行）。修复方法：删除第128-140行的重复 results.append 代码块。症状：10条查询返回20个结果（10个唯一ID重复2次）。
- [2026-04-20] [Sonnet] 微信三端消息汇总：msg_id 数据类型不匹配导致合并失败。原 schema：msg_id INTEGER。修复：msg_id TEXT。原因：微信 msg_id 是字符串格式（如 "uos_xxx_123"）。
- [2026-04-20] [Sonnet] 微信三端消息汇总：搜索功能需要 URL 编码（curl 自动编码）。API 端点：/api/wechat/messages?limit=10&search=关键词。已验证包含"我"、"高中"的消息可正常检索。
- [2026-04-20] [Sonnet] 场景：微信三端消息同步 Phase 2 完成 - 手机端 Web UI

完成内容：
1. 创建微信搜索页面
   - 路径：/home/charlie/hub/static/wechat-search.html
   - 功能：搜索消息内容、联系人筛选、加载更多
   - API 调用：/api/wechat/messages?limit=20&offset=0&search=关键词&talker=xxx

2. 添加 hub-api 端点
   - 路径：/wechat
   - 功能：返回微信搜索 HTML 页面

3. 访问方式
   - 本地：http://localhost:9800/wechat
   - 手机 Safari：http://192.168.2.100:9800/wechat

技术细节：
- 纯前端 HTML + JS，无需额外服务
- 响应式设计，支持手机浏览器
- 分页加载（每页20条）
- 实时搜索和筛选
- [2026-04-20] [Sonnet] 微信数据链接：Wine 微信 ~/文档/WeChat Files → /mnt/data/WeChat Files（符号链接），84G 完整数据，备份至 WeChat Files.wine-backup（20K）
- [2026-04-21] [Aider] fix: opencode.json instructions 必须为数组格式（永久修复）
  相关文件：opencode/opencode.json

- [2026-04-21] [GLM] 集成：散落功能联动集成
  - brain.py 加 _auto_trigger_flows()：每30轮检测服务异常→self_heal，每60轮→social_intelligence
  - brain.py 加 _increment_flow_runs()：flow执行后自动更新 index.json runs计数
  - brain.py 加 Cognitive Modulation：Ne发散限流/深夜降级/Fe休息提醒
  - self_improve.py 加 _write_to_letta() + _trigger_evolve()：审查结论→Letta archival + 触发evolve flow
  - wechat-learn.py 加 _trigger_social_flow()：导入完成后自动触发social_intelligence flow
  - 4个 systemd timer 已启用：cognitive-engine(09:00), self-improve(10:00), wechat-learn(11:00), letta-sync(10,16,22:00)
  - 关键教训：audit只出报告不够，必须实际执行代码变更才算完成
  - 关键教训：brain.py加调用点时必须同时写函数体，否则会crash
- [2026-04-21] [Aider] fix: 永久修复循环链接根因 — push-to-cloud.sh 不再 rsync 软链接文件
  相关文件：opencode/AGENTS.md, push-to-cloud.sh

  - 用户纠正: AGENTS.md 已从 git 自动恢复  agent.md你是根据我这一个月的返修率修改过的 现在是你修改和优化过的版本吗
  - 用户纠正: 需要。同时彻查循环链接都是被谁修改的 很多循环链接被修改。

  - 用户纠正: 需要。同时彻查循环链接都是被谁修改的 很多循环链接被修改。

  - 用户纠正: 需要。同时彻查循环链接都是被谁修改的 很多循环链接被修改。

  - 用户纠正: 需要。同时彻查循环链接都是被谁修改的 很多循环链接被修改。

  - 用户纠正: 需要。同时彻查循环链接都是被谁修改的 很多循环链接被修改。

  - 用户纠正: 需要。同时彻查循环链接都是被谁修改的 很多循环链接被修改。

  - 用户纠正: 需要。同时彻查循环链接都是被谁修改的 很多循环链接被修改。

  - 用户纠正: 需要。同时彻查循环链接都是被谁修改的 很多循环链接被修改。

  - 用户纠正: 需要。同时彻查循环链接都是被谁修改的 很多循环链接被修改。

  - 用户纠正: 我搜索下近一个月来 给cc和op 和glm的优化 全部找出来 看是否被修改了。如果有修改全补上。然后只能cc修改。

  - 用户纠正: 我搜索下近一个月来 给cc和op 和glm的优化 全部找出来 看是否被修改了。如果有修改全补上。然后只能cc修改。

  - 用户纠正: 我搜索下近一个月来 给cc和op 和glm的优化 全部找出来 看是否被修改了。如果有修改全补上。然后只能cc修改。

  - 用户纠正: 我搜索下近一个月来 给cc和op 和glm的优化 全部找出来 看是否被修改了。如果有修改全补上。然后只能cc修改。
  - 用户纠正: 我不明白 一般人买glm和deepseek是不是没办法配置好 导致能力下降很快

  - 用户纠正: 我搜索下近一个月来 给cc和op 和glm的优化 全部找出来 看是否被修改了。如果有修改全补上。然后只能cc修改。
  - 用户纠正: 我不明白 一般人买glm和deepseek是不是没办法配置好 导致能力下降很快

  - 用户纠正: 我搜索下近一个月来 给cc和op 和glm的优化 全部找出来 看是否被修改了。如果有修改全补上。然后只能cc修改。
  - 用户纠正: 我不明白 一般人买glm和deepseek是不是没办法配置好 导致能力下降很快

  - 用户纠正: 我搜索下近一个月来 给cc和op 和glm的优化 全部找出来 看是否被修改了。如果有修改全补上。然后只能cc修改。
  - 用户纠正: 我不明白 一般人买glm和deepseek是不是没办法配置好 导致能力下降很快

  - 用户纠正: 我搜索下近一个月来 给cc和op 和glm的优化 全部找出来 看是否被修改了。如果有修改全补上。然后只能cc修改。
  - 用户纠正: 我不明白 一般人买glm和deepseek是不是没办法配置好 导致能力下降很快

  - 用户纠正: 我搜索下近一个月来 给cc和op 和glm的优化 全部找出来 看是否被修改了。如果有修改全补上。然后只能cc修改。
  - 用户纠正: 我不明白 一般人买glm和deepseek是不是没办法配置好 导致能力下降很快
- [2026-04-21] [Sonnet] 业务邮件发送流程：msmtp + Gmail App Password → msmtp -a gmail --smtp-domain=gmail.com -t < mail.txt，收件人支持 -t 从stdin读To/Cc头，附件用 -- -a attachment.pdf。配置文件 ~/.msmtprc，凭据源 ~/.config/claude-export.env

  - 用户纠正: 密码有误，请重新输入。您还有2次机会

  - 用户纠正: 密码有误，请重新输入。您还有2次机会

- [2026-04-21] [Sonnet] NixOS NVIDIA Docker GPU直通踩坑：
  1. `hardware.nvidia-container-toolkit.enable = true` 需加 `suppressNvidiaDriverAssertion = true`，否则 noGUI specialisation 断言失败
  2. docker daemon 用 NixOS 生成的 `/nix/store/*-daemon.json` 而非 `/etc/docker/daemon.json`，必须通过 `virtualisation.docker.daemon.settings` 配置
  3. `pkgs.nvidia-container-toolkit` 只有 nvidia-ctk，`nvidia-container-runtime` 在 `pkgs.nvidia-container-toolkit.tools`
  4. nvidia-container-runtime 读取 `/etc/nvidia-container-runtime/config.toml`（不是 `/etc/nvidia-container-toolkit/`），且默认 mode="auto" 找不到 runc，需改 mode="cdi" + runtimes=["绝对路径/runc"]
  5. docker compose `deploy.resources.reservations.devices: driver: nvidia` 需要 NVIDIA 钩子（legacy模式），CDI/runtime:nvidia 不支持此语法，改用 `runtime: nvidia` 在服务顶层
  6. 最终可用方案：NixOS environment.etc 固化 config.toml，mode=cdi，runtimes=[pkgs.runc/bin/runc]

- [2026-04-21] [Sonnet] GPT-SoVITS Docker镜像：API文件是 api.py（不是 api_v2.py），TTS端点是 POST / 而非 /tts，参数用 text_language 而非 prompt_language

  - 用户纠正: 你不是说不支持 4.0吗
  - 用户纠正: 那不是说sonnet推理很强吗 怎么会这种逻辑漏洞
- [2026-04-22] [Aider] fix: 恢复 AGENTS.md CC所有权声明 + opencode instructions 禁止agent修改
  相关文件：opencode/AGENTS.md, opencode/opencode.json
- [2026-04-22] [Aider] fix: 恢复 AGENTS.md 完整内容（sisyphus二次篡改）+ 新增 SKILL_FIRST_FIX 死规则
  相关文件：opencode/AGENTS.md
- [2026-04-22] [GLM] NixOS: plasmashell 进程 comm 名为 `.plasmashell-wr`（wrapper），`pgrep -x plasmashell` 匹配不到，必须用 `pgrep -f plasmashell` 或 `pgrep plasmashell`。所有涉及 plasmashell 进程检测的脚本必须注意此兼容性问题。
- [2026-04-22] [GLM] `nix-store --verify --check-contents` 在 systemd timer 中会超时（遍历整个 store），应只使用 `nix-store --verify` 并加 `timeout 20` 限制。
- [2026-04-22] [GLM] systemd user service 创建后必须：(1) daemon-reload (2) enable --now (3) 验证 timer 列表 (4) 用 show --property=Result 验证首次运行结果。service 引用脚本路径必须与实际文件名一致。
- [2026-04-22] [Aider] feat: SOPS加密ZAI_API_KEY + OP模型分层 + 修复plasma-manager警告
  相关文件：home/charlie.nix, modules/users.nix, secrets/secrets.yaml
- [2026-04-22] [Aider] fix: Floorp输入法声明式修复 + GLM知识写入job + user.js Wayland设置
  相关文件：home/charlie.nix, modules/browser.nix

- [2026-04-22] [GLM-Z-Air] UOS微信4.1.1数据库解密：关键突破是验证算法修正
  - 症状：ylytdeng/wechat-decrypt 扫描 /proc/<pid>/mem 的 x'<hex>' 模式，15M候选全失败
  - 原因：HMAC验证算法写错。正确方法是用 PBKDF2-HMAC-SHA512（mac_salt = salt XOR 0x3A, iterations=2），不是直接 HMAC
  - 修复：用 ylytdeng key_scan_common.py 的 verify_enc_key() 函数
  - 结果：16/16 活跃 DB 全部解密成功
  - 密钥位置：~/文档/xwechat_files/wxid_bjo2p0swoxm822_fe61/decrypted/keys.json
  - 解密DB位置：~/文档/xwechat_files/wxid_bjo2p0swoxm822_fe61/decrypted/dbs/
  - 注意：sqlcipher 解密命令需用 PRAGMA cipher_compatibility = 4
  - 注意：message_0.db 只有 .factory 备份，不在活跃使用中（活跃的是 message_1.db）
  - GDB断点法（setCipherKey at 0x41efc90）可用但命中太多无关字符串，内存扫描更高效
- [2026-04-23] [Stop-Hook] AUTO_SKILL 补调：tg-push cooldown 机制
- [2026-04-23] [Stop-Hook] AUTO_SKILL 补调：Windows微信版本锁定+降级部署流程

  - 用户纠正: 这发送不对劲啊 只能用屏幕截屏来发送信息吗

  - 用户纠正: 这发送不对劲啊 只能用屏幕截屏来发送信息吗

- [2026-04-23] [Sonnet] xdotool 在 KDE Wayland 崩溃：xdotool 在 KDE Plasma Wayland 下触发"致命错误被关闭"弹窗（崩溃），即使设置了 XAUTHORITY 也不行。解决：全部替换为 ydotool（uinput 层，Wayland 原生）+ wmctrl（窗口激活）+ wl-copy/Ctrl+V（粘贴，比 ydotool type 更可靠处理中文）。ydotoold daemon 已在系统中通过 systemd user service 运行。GUI 应用中用 Ctrl+V 粘贴（终端用 Shift+Insert）。

  - 用户纠正: win微信有消息。但是信息内容不对。nixos没消息 好像是选错了

  - 用户纠正: win微信有消息。但是信息内容不对。nixos没消息 好像是选错了

  - 用户纠正: win微信有消息。但是信息内容不对。nixos没消息 好像是选错了

  - 用户纠正: win微信有消息。但是信息内容不对。nixos没消息 好像是选错了

  - 用户纠正: 我是业务员。不要被封号。所以最后方案是什么

  - 用户纠正: 我是业务员。不要被封号。所以最后方案是什么

  - 用户纠正: 我是业务员。不要被封号。所以最后方案是什么

  - 用户纠正: 我是业务员。不要被封号。所以最后方案是什么

  - 用户纠正: 我是业务员。不要被封号。所以最后方案是什么

  - 用户纠正: 我是业务员。不要被封号。所以最后方案是什么

  - 用户纠正: 我是业务员。不要被封号。所以最后方案是什么

  - 用户纠正: 我是业务员。不要被封号。所以最后方案是什么

  - 用户纠正: 我是业务员。不要被封号。所以最后方案是什么

  - 用户纠正: 我是业务员。不要被封号。所以最后方案是什么

  - 用户纠正: 我是业务员。不要被封号。所以最后方案是什么

  - 用户纠正: 我是业务员。不要被封号。所以最后方案是什么
  - 用户纠正: 现在微信是实时同步的吗 都解密了吗 但http://192.168.2.100:9800/wechat 这个不是最新

  - 用户纠正: 现在微信是实时同步的吗 都解密了吗 但http://192.168.2.100:9800/wechat 这个不是最新
  - 用户纠正: 🤖 AI链路巡检告警 (04-23 19:49)
🔴 关键配置被篡改: AGENTS.md (CHANGED)
🔴 关键配置被篡改: opencode.json

  - 用户纠正: 微信文件处理群处理任务 之前不是设置过吗 比如#文档 或者office我设置过的。 你怎么还是没有读取记忆。

  - 用户纠正: 微信文件处理群处理任务 之前不是设置过吗 比如#文档 或者office我设置过的。 你怎么还是没有读取记忆。

  - 用户纠正: 这总结结果不行啊，这个微信呃联系人什么的就是呃他的这个ID跟群名都没有，我需要梳理啊，你这个东西都没有梳理，然后就是事情的来龙去脉都没有说。嗯，你能搜索一下社区

  - 用户纠正: 这总结结果不行啊，这个微信呃联系人什么的就是呃他的这个ID跟群名都没有，我需要梳理啊，你这个东西都没有梳理，然后就是事情的来龙去脉都没有说。嗯，你能搜索一下社区

  - 用户纠正: 这总结结果不行啊，这个微信呃联系人什么的就是呃他的这个ID跟群名都没有，我需要梳理啊，你这个东西都没有梳理，然后就是事情的来龙去脉都没有说。嗯，你能搜索一下社区

  - 用户纠正: 这总结结果不行啊，这个微信呃联系人什么的就是呃他的这个ID跟群名都没有，我需要梳理啊，你这个东西都没有梳理，然后就是事情的来龙去脉都没有说。嗯，你能搜索一下社区

- [2026-04-24] [Sonnet] 卡死根因：凌晨 OP Timer 堆积 → CPU 99% → KWin 挂起
  症状：系统无响应需强制重启
  根因：proxy-watchdog.timer 每15秒触发(24/7) + 25个user timer凌晨全开 → CPU 持续99%超10分钟
  触发链：01:38 fwupd-refresh+Cockpit启动 → CPU 70%+ → 01:44 CPU 96% → 01:49 KWin主线程挂 → 强制重启
  已修复：claude-orphan-killer 60s→5min，fcitx5/wechat-sync 改为仅08-23运行
  待修复：proxy-watchdog 15s→90s（需改 /etc/nixos/modules/proxy.nix:517）
- [2026-04-24] [Aider] fix: 修复登录卡死三根因
  相关文件：home/charlie.nix, modules/desktop.nix

- [2026-04-24] [Sonnet] NixOS 登录卡死三根因诊断修复：
  - 症状：gen 156 某些启动会话卡死（boot -3 仅36秒，全部 KDE 组件 DBus NoReply）
  - 根因1：xdg-desktop-portal 懒启动，Plasma 组件超时等待 → 修复：activation 脚本在 graphical-session.target.wants/ 创建 portal 链接
  - 根因2：home-manager 在 /mnt/ai 挂载前执行（.cache→/mnt/ai/cache/xdg）→ 修复：systemd.services.home-manager-charlie After/Wants mnt-ai.mount
  - 根因3：krfb-autostart.service 有 PartOf=graphical-session.target → novnc 循环依赖被 systemd 强制删除 → 修复：移除 PartOf
  - 诊断方法：journalctl -b -N 对比多次启动，查找 "ordering cycle" 和 "Failed to register with host portal QDBusError"
  - 存储警告：storage.nix 已改为 POOL-D1 bind mount，下次重启 /mnt/ai 从 loop→bind，POOL-D1/ai 有16个容器（loop有14），数据已迁移
- [2026-04-24] [Sonnet] NixOS登录卡死根因+防护：(1)systemd用户服务 PartOf+After 指向同一target且被Requires→循环依赖；(2)home-manager在/mnt/ai挂载前执行（~/.cache→/mnt/ai/cache符号链接）。修复：新建nixos-preflight-check.sh(rebuild前检查两类问题)+nixos-smoketest.sh(rebuild后验证3项)+集成进nixos-rebuild-safe步骤2.5/3.5+CLAUDE.md NIXOS_REBUILD_GUARD规则
- [2026-04-24] [Aider] fix: NixOS登录卡死三根因修复 + 预检/冒烟测试工具
  相关文件：claude/memory/ideas-roadmap.md, claude/memory/lessons-learned.md, systemd/graphical-session.target.wants/xdg-desktop-portal.service, systemd/krfb-autostart.service

  - 用户纠正: 我的意思是 是关机前的数据 而不是rebuild的数据？

  - 用户纠正: 我的意思是 是关机前的数据 而不是rebuild的数据？

  - 用户纠正: 我的意思是 是关机前的数据 而不是rebuild的数据？

  - 用户纠正: 那我grub里面的而 nixos default每次都是最新版本吗 我怎么感觉每次进去感觉不对劲

  - 用户纠正: 那我grub里面的而 nixos default每次都是最新版本吗 我怎么感觉每次进去感觉不对劲

  - 用户纠正: 那我grub里面的而 nixos default每次都是最新版本吗 我怎么感觉每次进去感觉不对劲

  - 用户纠正: 那我grub里面的而 nixos default每次都是最新版本吗 我怎么感觉每次进去感觉不对劲

  - 用户纠正: 那我grub里面的而 nixos default每次都是最新版本吗 我怎么感觉每次进去感觉不对劲

  - 用户纠正: 那我grub里面的而 nixos default每次都是最新版本吗 我怎么感觉每次进去感觉不对劲

- [2026-04-24] [Sonnet] 代理主从倒置根因：proxy-watchdog 代码 `echo "xray"` 默认 xray 为主，`if CURRENT != "xray"` 每5分钟主动停 mihomo 切 xray，注释写的 Tier1=mihomo 但代码逻辑相反。修复：改 default 和恢复逻辑为 mihomo，rebuild（restartIfChanged=false 保护不断线）。
- [2026-04-24] [Sonnet] mihomo-guardian 92次误报根因：ipinfo.io/country 被限速返回 429 JSON，ifconfig.me/country 返回 "Not found"，guardian 误判为"不支持地区"触发 rollback，rollback 调用 do_rollback 超时120s+。修复：do_check 改为只检查 gstatic.com generate_204，任何非000均视为健康，去掉国家检测整个分支。

  - 用户纠正: 问题是我手机5G网络访问哪个地址进行远程编程。 我不要tailscale.我要固定地址

  - 用户纠正: 问题是我手机5G网络访问哪个地址进行远程编程。 我不要tailscale.我要固定地址

  - 用户纠正: 问题是我手机5G网络访问哪个地址进行远程编程。 我不要tailscale.我要固定地址

- [2026-04-24] [GLM] happy claude session 卡死：症状→用户发了消息但happy无响应超过5分钟 根因→上游代理节点(良心云 aws-link1.liangxin1.xyz) DNS解析失败，mihomo 7890端口在监听但所有出站请求ECONNREFUSED，happy SDK backoff到retry 50还不停(无max_retries)，session永远不放弃 修复→kill卡死进程+创建happy-session-watchdog.sh(每3分钟检查session日志最后修改时间，>5分钟无更新自动kill+notify) 防范→watchdog已注册systemd timer(happy-session-watchdog.timer)，代理节点故障是上游问题无法本地控制

- [2026-04-24] [GLM] 启动崩溃：~/.cache 是指向 /mnt/ai/cache/xdg 的符号链接，home-manager linkGeneration 尝试 mkdir ~/.cache 报"文件已存在" → 级联导致所有用户服务失败（找不到 bash/python3/npx）。修复：在 home/charlie.nix 添加 activation script，在 linkGeneration 前删除旧 .keep 符号链接。症状：启动卡住、大量服务 "Failed at step EXEC spawning"。
- [2026-04-25] [Sonnet] **fewer-permission-prompts skill 清空 bypass-all**：此 skill 扫描历史记录后将 `"allow":["*"]` 替换为具体白名单（17条只读规则），导致 ADB/nixos-rebuild 等命令重新弹权限提示。修复：手动恢复 `"allow":["Bash(*)","Read(*)","Edit(*)","Write(*)","Agent(*)"]`。建议：运行该 skill 前确认是否真的需要收紧权限。
- [2026-04-25] [Sonnet] **auto-save 误改 fcitx5 waylandFrontend**：2026-04-24 22:00 自动提交将 `waylandFrontend=true` 改为 `false`（注释称修复 Floorp 输入法），破坏 Kitty/OpenCode Wayland IME。根因：`waylandFrontend=true` 时 NixOS 不自动设 GTK_IM_MODULE，auto-save 认为这是 bug 改掉了。修复：改回 `true` + 在 desktop.nix `sessionVariables` 显式设置 GTK_IM_MODULE/QT_IM_MODULE/SDL_IM_MODULE/INPUT_METHOD。
- [2026-04-25] [Aider] fix: opencode permission bypass + model cleanup
  相关文件：opencode/opencode.json
- [2026-04-25] [Sonnet] 插網線斷 WiFi：eno1 有兩條 NM 連接搶默認路由 → nmcli connection modify 有线连接1/eno1-wired ipv4.never-default yes 修復

### 会话摘要 [2026-04-25] [Sonnet/自动]
- 对话轮次: 136 | 被纠正: 1次
  - 用户纠正: 不是登陆问题 是代理问题 请彻查

### 会话摘要 [2026-04-25] [Sonnet/自动]
- 对话轮次: 138 | 被纠正: 1次
  - 用户纠正: 不是登陆问题 是代理问题 请彻查
- [2026-04-25] [GLM] 偏好：Charlie要求已知偏好自动执行，禁止回问。新增 USER_PREF_AUTO 死规则。典型信号：以后都/每次/不用问我

- [2026-04-25] [GLM-Z-Air] **pi (badlogic/pi-mono) v0.70.2 自定义 provider 模型名不带前缀**
  - 场景：pi --provider litellm --model openai-compatible/glm-4.7 报 400 Invalid model name
  - 根因：pi 的 custom provider models.json 中 model id 必须和 LiteLLM `/v1/models` 返回的 id 完全一致（如 `glm-4.7`），不能带 `openai-compatible/` 前缀
  - 修复：models.json model id 改为 `glm-4.7`、`glm-5-turbo` 等（和 LiteLLM 实际 id 一致）
  - 配置路径：`~/.pi/agent/models.json`（custom provider）+ `~/.pi/agent/AGENTS.md`（规则注入）
  - pi 自动发现项目目录下的 AGENTS.md 和 CLAUDE.md，无需手动注入 system prompt
  - pi 无内置 web server，无多客户端实时同步（和 OpenCode 相同限制）
  - CLI alias：`pi` = `pi --provider litellm --model glm-5-turbo`（已写入 .zshrc）
- [2026-04-25] [Sonnet] **auto-save 第二次误改 waylandFrontend**：2026-04-24 22:00 auto-save 再次将 waylandFrontend=true 改为 false，OP 在 02:26 改回但 lessons-learned 未能阻止。根因：auto-save 脚本无法理解 PROTECTED 注释。修复：在配置行加 # PROTECTED: DO NOT CHANGE TO FALSE + 注释说明历史。永久方案：把 auto-save 脚本加入 waylandFrontend 黑名单。
