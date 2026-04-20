# 踩坑日志

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
