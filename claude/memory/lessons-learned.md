# 核心经验（≤50行，2026-05-18 精简）

## 代理/网络
- [2026-05-04] mihomo GLOBAL 必须保持 `⚡ 自动选择`，禁止 DIRECT。Cloudflare 全站封禁时用手机 SOCKS5 隧道 `ssh -D 1080 phone` 绕过
- [2026-05-04] Claude 403 `Request not allowed` = GLOBAL 被设 DIRECT，国内 IP 直连 anthropic 被封
- [2026-05-09] mihomo 全部节点失效 → 更新订阅或切良心云

## NixOS/Python
- [2026-05-18] `.zshrc` 的 Nix Python3.13 PYTHONPATH for 循环必须排除含 C 扩展的包（numpy/scipy/chromadb/pydantic-core/pydantic），否则 uv/pip 的 Python3.11 沙箱会加载不兼容的 3.13 C 扩展崩溃
- [2026-05-05] mem0-bridge 重 ML 依赖（torch 530MB）不适合 NixOS venv+pip，用 Docker
- [2026-05-03] NTFS 上禁止 Python venv install（不仅限 npm/bun），迁移到 /mnt/ai/apps/

## Hyprland/NVIDIA
- [2026-04-28] Hyprland 启动崩溃 → 检查 egl-wayland 是否安装（NVIDIA 必需）
- [2026-04-27] Hyprland 黑屏 → render.explicit_sync 在 0.54+ 已废弃，删除该配置
- [2026-05-03] Hyprland+KDE 双桌面冲突 → 避免同时启用
- [2026-05-10] Hyprland Super+D 全屏冲突 → 只保留 `fullscreen,1`，删除 `fullscreen`

## Docker/服务
- [2026-05-03] Docker 16 容器同时启动 → 用 docker-ordered-start.sh 分层启动（Tier1→Tier4）
- [2026-05-18] NVIDIA GPU 崩溃后 Docker containerd 损坏 → 全量清理 `containers/network/rootfs` 重建，禁用宿主同名服务让 Docker 接管
- [2026-05-17] opencode-worktree 插件无 main 字段 → 从 plugin 数组移除，否则 sisyphus tmux 循环崩溃

## 记忆系统
- [2026-05-10] Letta MCP 307 重定向 → macg_mcp.py 中 `/v1/agents` 改为 `/v1/agents/`
- [2026-05-03] 记忆遗忘引擎：lessons-learned 45天衰减，codebase-map 30天，一次性报告 7天
- [2026-05-09] memory-bootstrap.sh 正则 `场景[:\s]` 匹配高频主题，Letta 用 curl HTTP status 检测

## 手机/ADB
- [2026-05-03] OPPO PKR110 Tailscale 被 Karing VPN 抢占 → `pm disable com.nebula.karing` + 看门狗每5分钟 force-stop
- [2026-05-04] 截图 watcher 必须 `adb shell ls` 确认最新文件再 pull，不依赖 intent 缓存
- [2026-05-04] Tailscale 看门狗 grep 用 `ip addr show | grep "100\.64\..*tun"` 而非 `ip link show`

## 系统稳定性
- [2026-05-03] krdpserver-desktop.service 反复 SIGABRT → disable，远程桌面改用 wayvnc
- [2026-05-07] auto-fix-services 不区分 oneshot timer → SKIP_PATTERNS 加 oneshot 服务名
- [2026-05-07] nixos-full-sync 需 export PATH="$HOME/.local/bin:$PATH"
- [2026-05-17] 根分区 >85% → nix-collect-garbage，禁止装新系统包

## 关键路径
- [2026-05-18] 新建服务手机访问 → MUST 用 LAN IP 测试（非 localhost），端口须在 allowedTCPPorts
- [2026-05-04] Playwright headless 对百度 OAuth 无效（反自动化），需用户手动登录
- [2026-05-27] GLM-4.6V-Flash 连续调用 >3 次触发 429 → 加 sleep 10-15s
- [2026-05-18] [OP] 根因修复: frpc systemd 服务 | 错误: frpc 连 frps timeout | 原因: http_proxy=http://127.0.0.1:7890 被 systemd 继承,FRP 协议被 mihomo 代理拦截 | 修复: frpc.service 添加 Environment="http_proxy=" 清除代理 | 场景: 任何走 systemd 的网络服务如果本机有代理,必须显式清除代理变量
- [2026-05-18] [OP] 成功记录: FRP 连接修复 | 调用: frpc 0.68.1→0.66.0 匹配 frps | 结果: 10 proxy 全部 success | 场景: NixOS frps 0.66.0，手动安装 frpc 0.68.1 导致握手超时
- [2026-05-18] [OP] 成功记录: CrewAI+LangGraph Gateway v2.0 | 调用: POST /agent/chat + /crew/kickoff + /workflow/run + /health(upstream) | 结果: 全部正常 | 场景: 六层架构 L1 入口层
- [2026-05-18] [OP] 成功记录: OpenCode CLI 桥接 | 调用: opencode run -m openai-compatible/deepseek-v4-flash | 结果: 成功读取文件 | 场景: OpenClaw→OpenCode 编码桥接
- [2026-05-18] [OP] 待办: FRP 端口 18091 需添加到 NixOS frps allowPorts（受保护配置，需 CC 或 nixos-rebuild）
- [2026-05-18] [OP] 成功记录: Windows frpc | 调用: scp+ssh G@192.168.123.136 | 结果: 成功 | 场景: Win frpc 部署到 C:\Toolsrpc\, 版本 0.66.0, 开机自启 schtasks FRPClient, 隧道 win-ssh:2222 win-rdp:3389 | 注意: Win IP 是 DHCP(192.168.123.x), NixOS frpc 连 frps 用 192.168.123.209:7000
- [2026-05-18] [OP] 用户偏好: Charlie要求不再委派CC(macg_cc_delegate)，OP自行完成所有任务，CC委托路由永久禁用
- [2026-05-18] [OP] Windows↔NixOS连接稳定性诊断 | 根因: 无网线+3条路径全走WiFi+WiFi波动大(22-300ms抖动)+Windows无有线网卡IP | 修复: (1)SSH config多路径回退winpc(frp)/winpc-ts(Tailscale)/winpc-wifi (2)Windows frpc心跳10s/超时30s/连接池2 (3)WiFi BSSID锁定FC:FC:43:26:60:B8+功率管理关闭 (4)frp-watchdog v3自动通过Tailscale触发Windows frpc重启 (5)ssh-win脚本自动回退3路径 (6)Windows侧win-frpc-watchdog.ps1待推送 | 注意: 192.168.2.36已失效, Windows当前IP是192.168.123.136(WiFi), Tailscale 100.91.93.99
- [2026-05-18] [OP] 成功记录: Letta API | 调用: archival-memory/search改GET+query参数 | 结果: 成功 | 场景: Letta v0.x API, POST→GET, 返回{results:[...]}非数组
- [2026-05-18] [OP] 成功记录: embedding-server.service | 调用: systemd user service运行ONNX MiniLM-L6-v2 | 结果: 端口8286稳定运行 | 场景: Letta Docker需要宿主机embedding API, venv路径/home/charlie/agi/.venv
- [2026-05-18] [OP] 成功记录: Letta Docker no_proxy | 调用: docker-compose.yml添加小写no_proxy | 结果: Letta容器可访问宿主机8286 | 场景: Docker内大小写proxy env不一致导致连接拒绝
- [2026-05-19] [OP] 失败学习: systemd服务重启风暴 | 错误: letta.service/obsidian.service ExecStart路径不存在导致10秒重启循环 | 正确: disable无效服务 + 安装systemd-orphan-guard.timer每小时自动清理 | 原因: venv清理/路径迁移后服务文件未同步

- [2026-05-19] [OP] 用户偏好: Charlie的USB线常插Windows不在NixOS | 场景: ADB连接手机时 | 正确做法: SSH到Windows(G@100.91.93.99)执行adb tcpip 5555激活无线调试，然后NixOS直连 | 根因: NixOS USB口不够用，Charlie习惯USB线插Windows
- [2026-05-19] [OP] 成功记录: otp-sync多元连接方案 | 场景: 手机ADB连接失败时 | 调用: 4层连接优先级 WiFi直连→USB→Windows SSH中转→局域网扫描 | 注意: 手机当前WiFi IP 192.168.123.22，子网192.168.123.0/24
- [2026-05-19] [OP] 成功记录: waybar自定义模块添加 | 场景: waybar由home-manager管理时 | 调用: 生成config.override覆盖符号链接+kill -SIGUSR2重载 | 注意: /etc/nixos/home/charlie.nix已同步更新OTP模块，下次nixos-rebuild后无需override
- [2026-05-19] [OP] 记忆修正: StepClaw 已从架构移除但记忆未更新 | 错误: session-notes.md 仍引用 StepClaw 4-agent/待办/文档 | 修正: 清除 StepClaw 引用，标注为 3-agent，写入 Letta 归档 | 原因: 组件移除时未同步清理记忆文件
- [2026-05-19] [OP] 成功记录: NixOS systemd python3 | 调用: ExecStart=/run/current-system/sw/bin/python3 (不用.venv) | 结果: 成功 | 场景: NixOS systemd服务需导入nix store中的Python包(fastapi等)时，必须用系统python而非.venv wrapper
- [2026-05-19] [OP] 空壳防护: smoke-test.sh + dead-component-detect.sh | 修复: CrewAI 8701 挂死(旧进程未释放端口) | CLAUDE.md 新增 SHELL_GUARD 死规则 | 根因: AI 搭建完不验证链路，建成≠完成
- [2026-05-19] [OP] 调度打通: telegram_bot._handle_ask → macg.py -p supervisor → GLM/Claude/CrewAI | 修复: make_models全部走LiteLLM(ChatOpenAI替代ChatAnthropic) | 模型名: claude-opus-4-6-20250514, claude-sonnet-4-5-20250514 | waybar调度呼吸灯: dispatch-green/yellow/red | agi.venv需pip install langchain-core/openai/anthropic/langgraph
- [2026-05-19] [OP] 记忆一致性教训 | 问题: MEMORY.md/command-reference.md等5个文件残留旧IP 192.168.2.36, 新会话读到旧信息直接执行导致连接失败 | 根因: lessons-learned记录了变更但未自动回刷到其他文件, 模型默认先读MEMORY.md | 修复: (1)全局替换17处旧IP为ssh winpc (2)以后关键基础设施变更(IP/端口/路径)写入lessons-learned时MUST同步grep全目录替换 | 场景: 任何跨文件一致性问题
- [2026-05-19] [OP] 工具: Playwright MCP | 调用: navigate platform.stepfun.com | 结果: 失败(ERR_EMPTY_RESPONSE) | 场景: Playwright MCP不走系统代理，被墙站点无法访问
- [2026-05-19] [OP] 成功记录: opencode闪退恢复 | 调用: SIGILL崩溃后自动重启 | 结果: opencode --continue + web服务正常运行 | 场景: Node.js v24.14.0 + opencode 1.15.3 偶发SIGILL

- [2026-05-19] [OP] 永久禁用配置回滚 | 根因: 3个定时器脚本 (ai-config-sync-pull/12min, ai-config-guard/10min, opencode-config-guard/11min) 自动检测"异常"并用 git restore/checkout --theirs/json.dump 覆盖用户手动修改 | 修复: 全部改为仅检测+通知, 永不自动覆盖 | 文件: ~/bin/ai-config-sync-pull.sh, ~/.local/bin/ai-config-guard.sh, ~/.local/bin/opencode-config-guard.sh | 新增: config-lock.sh 手动锁定工具
- [2026-05-19] [OP] 失败学习: 记忆调用纪律 | 错误: 执行手机ADB任务时跳过了记忆检索步骤,直接尝试本地ADB,忽略了已知的"USB线插在Windows上"和"手机已Root"信息 | 正确: 执行前MUST调用macg_context_probe + 读取lessons-learned.md | 触发条件: 涉及手机/外部设备/Windows等跨系统操作时
- [2026-05-19] [OP] Tailwind v4修复: @tailwindcss/oxide Scanner的`**/*` glob在NixOS/ext4项目路径下不递归子目录。根因: native Rust walker bug。解决: 在globals.css中用brace expansion显式列举每个组件子目录 `@source "../app/components/{dir1,dir2,...}/*.{ts,tsx}"`。深度嵌套目录(如dashboard/charts)需单独`@source`。`@source "../app"`(Auto模式)不工作，必须用Pattern+单层`*`。修复后CSS从7.6KB→42KB，200+工具类生成。- [2026-05-19] [Aider] fix: 全系统git备份覆盖所有仓库+修复路径
  相关文件：bin/git-backup.sh, systemd/git-backup.service
