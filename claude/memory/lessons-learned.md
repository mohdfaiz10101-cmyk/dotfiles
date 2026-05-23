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
- [2026-05-21] **Hyprland windowrule 语法大改（0.42→0.54 三代变迁）**：
  - ❌ 旧（已废弃）：`windowrulev2 = float, class:^(name)$`
  - ❌ 旧中间版（也废弃）：`windowrule = float, class:^(name)$`
  - ✅ 新（0.54+ 块语法）：
    ```
    windowrule {
      name = fcitx-rules     # 必须第一行
      match:class = ^(name)$
      float = 1
      no_anim = 1            # 注意：是 no_anim 不是 noanim
    }
    ```
  - 诊断命令：`hyprctl configerrors`（直接返回具体行号和错误原因，优先用这个）
  - 遇到 Hyprland 配置错误红色覆盖层 → 先 `hyprctl configerrors` 再修

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
- [2026-05-22] OnePlus Ace 5 Pro (PKR110) 三卡：联通/移动纯IPv6无CLAT，Nat464Xlat未启动→移动数据仅电信卡有IPv4可用。oplus-netd BPF REJECT规则（/sys/fs/bpf/prog_oplus-netd_skfilter_reject_*）阻止CLAT，fw_INPUT链6条规则。WiFi正常

## Chrome/NVIDIA
- [2026-05-22] Chrome 147 + NVIDIA 595 + Wayland 每个 tab 崩溃 → 加 `--use-angle=gl --ignore-gpu-blocklist --disable-gpu-sandbox` 修复。ANGLE 默认后端在 NVIDIA Wayland 下 GPU 进程崩溃导致所有 tab 显示"喔唷，崩溃啦"。

## 系统稳定性
- [2026-05-03] krdpserver-desktop.service 反复 SIGABRT → disable，远程桌面改用 wayvnc
- [2026-05-07] auto-fix-services 不区分 oneshot timer → SKIP_PATTERNS 加 oneshot 服务名
- [2026-05-21] [OP] 修复: sisyphus 任务穿插 | 原因: 身份与职责里无条件执行op-tasks.md导致接到任意任务都扫描穿插 | 修复: 仅当用户明确说执行op-tasks时才扫描，否则只执行当前分配任务
- [2026-05-22] [OP] 修复: macg MCP -32000 Connection closed | 原因: macg_mcp.py硬编码HTTP transport，OpenCode spawn stdio实例与systemd HTTP实例端口冲突 | 修复: 添加--http参数分离transport mode，无参数默认stdio

- [2026-05-22] [OP] 修复: sisyphus 任务穿插根因 — 不是 agent 配置问题，而是 3 个 systemd timer+脚本在后台独立调用 opencode --agent sisyphus 处理 op-tasks.md。操作: 停用 op-task-runner.timer+删脚本，停用 cc-task-runner.timer+删内联 sisyphus 调用，保留 op-exec.sh 作为唯一入口+check-ttyd.timer不动- [2026-05-22] [OP] 成功记录: FRP 8700端口 | 调用: 新增nixos-openagents-net代理(8700→18700), 更新frps.toml allowPorts, 手动启动FRPS | 结果: 成功 | 场景: OpenAgents Network公网访问
- [2026-05-22] [OP] 修复: macg MCP Not connected — OpenCode config stdio→HTTP | 原因: opencode.json中macg用stdio + /mnt/ai/home-offload路径Python导致D状态挂死 | 修复: 改为streamable-http指向127.0.0.1:18092/mcp，杀掉3个僵尸进程 | 验证: JSON valid + MCP initialize返回200
- [2026-05-22] [Aider] fix: floorp fcitx5 desktop fix + agent sync禁用
  相关文件：claude/memory/agi-audit-log.jsonl, claude/memory/cc-op-dialog.jsonl, claude/memory/changelog.jsonl, claude/memory/lessons-learned.md, claude/memory/letta-memory.json
- [2026-05-22] [OP] 修复: macg MCP SSE 502 | 原因: mihomo代理拦截127.0.0.1:18092请求返回502，no_proxy使用CIDR 127.0.0.0/8但Python urllib/Node.js不认CIDR格式 | 修复: no_proxy显式添加127.0.0.1，更新~/.config/environment.d/20-proxy.conf + systemd set-environment

- [2026-05-23] [OP] DuckDNS:17699缓慢 | 根因: 用户nproc limit 2048被2407线程打满 | 修复: kill Chrome(PID 8015 CDP, PID 353351 opencode), ulimit -u 4096 | 持久化: 需在/etc/security/limits.d/或systemd user.conf设置nproc=8192
- [2026-05-23] [OP] 工具: plocate文件索引 | 路径: plocate -d ~/.local/state/plocate/plocate.db 'pattern' | 覆盖: 全/home/charlie | 规则: 找文件时MUST先plocate再find/glob，毫秒级响应 | 更新: systemd timer每日自动- [2026-05-23] [OP] 修复: overtab tmux serve模式 | 原因: ttyd连接时tmux session才创建，断开即销毁 | 修复: 新增overtab-serve.service(oneshot+RemainAfterExit)维持tmux会话，ttyd-wrapper改为attach已有session | 文件: overtab-serve.service, overtab-serve-start, overtab-serve-stop, overtab-tmux-wrap, ttyd-overtab.service

- [2026-05-23] [OP] 修复: 17699 opentab serve模式 | 原因: opencode-tmux-wrap会话名用sisyphus但实际session叫sisy, opencode TUI退出后会话终止 | 修复: session名改为sisy, opencode命令包裹在while true循环中, tmux remain-on-exit on + destroy-unattached off | 文件: ~/.local/bin/opencode-tmux-wrap, ~/.local/bin/overtab-serve-start- [2026-05-23] [OP] 修复: ttyd beforeunload "留在此页"弹窗 | 原因: ttyd默认beforeunload handler，切换/关闭页面时触发 | 修复: 9个ttyd service全部添加 -t disableLeaveAlert=true 客户端选项，控制台日志 "Leave site alert disabled"

- [2026-05-23] [OP] VNC桌面Tab全链路验证通过: wayvnc:5900→websockify:5998→Caddy:7699→FRP:17699→DuckDNS→外网浏览器 | 本地200 + LAN 200 + DuckDNS 200 | 无需rebuild: /etc/frps.toml已含17698-17699, frp.nix已同步但rebuild受eeb限制 | mihomo代理曾干扰curl测试(HTTP 000), no_proxy绕过即可- [2026-05-23] [OP] 修复: FRPC port not allowed 错误刷屏 | 错误: nixos-tty(17698)和nixos-openagents-net(18700)不在FRPS allowPorts中，每30秒刷屏 | 修复: 禁用frpc.toml中两个无效proxy(17698重复7699端口;18700需等NixOS rebuild添加FRPS allowPorts) | 验证: FRPC重启后所有proxy正常启动无报错

- [2026-05-23] [OP] 8080通过DuckDNS暴露 | 路径: charlie1990.duckdns.org:17699/oc/ → Caddy(7699) → 127.0.0.1:8080 | FRP: nixos-opencode-web(8080→19890)已配置但路由器未转发19890 | 方案: 可复用/oc/路径或等路由器可用后添加19890转发
- [2026-05-23] [OP] 路由器Padavan端口转发: vts_srcip_x*=* → iptables源限制变为0.0.0.0/24致外部不通 | 修复: 清空为"" → 0.0.0.0/0 | 受影响的端口: 7681,2222:22,24801,8080,3456:9800,8283:8284,8888:18789 | 方法: SSH nvram set vts_srcip_xN="" → nvram commit → restart_firewall
- [2026-05-23] [OP] 路由器Web API: 端口转发页面是Advanced_VirtualServer_Content.asp(非DMZ页Advanced_Exposed_Content.asp) | 表单字段名: vts_port_x_0(有额外下划线) | VSList变量格式: [外部端口,内部IP,内部端口,协议,protono,源IP,描述]
- [2026-05-23] [OP] 修复: DuckDNS:17699 浏览器刷新缓存 | 原因: Caddyfile launcher首页和/multi页面设置Cache-Control "no-cache, no-store, must-revalidate"完全禁止浏览器缓存 | 修复: 改为 "no-cache"（仅此词，保留ETag/Last-Modified验证），浏览器发If-None-Match→资源未变返回304用缓存 | 文件: /mnt/ai/apps/launcher/Caddyfile
- [2026-05-23] [OP] 再犯: 问答后自动穿插无关任务 | 场景: 回答ChinaNet问题后无指令执行bun run build | 根因: 回答完成后自动扫描/执行了无关操作 | 强制规则: 对话结束后禁止执行任何命令，除非用户明确指定下一个操作
- [2026-05-23] [OP] GELab-Zero部署: 框架/依赖/ADB就绪，阻塞在模型推理 | 根因: NixOS Ollama 0.20.3是CPU-only构建(无CUDA)，所有模型运行在CPU导致超时 | gelab(Qwen3VL)崩溃因架构不兼容 | StepFun API quota exceeded | 解决方向: 安装CUDA版Ollama binary或nixpkgs-unstable
- [2026-05-23 12:20] [OP] 发现: macg_cc_delegate 永久失效 | 原因: claude CLI 未登录(403 Forbidden)，无API key，Pro/Max OAuth不可用于CLI | 影响: 所有CC委托调用实际返回错误但被静默捕获 | 修复: 改用task subagent(arch+glm-5.1)替代，见sisyphus.md更新
- [2026-05-23] [OP] 再犯: macg MCP SSE 502复发 | 原因: .zshrc未显式设置no_proxy含127.0.0.1，仅靠environment.d文件但shell不读取 | 修复: .zshrc直接export no_proxy='127.0.0.1,...'合并所有值，删除旧的追加行
- [2026-05-23] [Aider] feat: 验证体系 v3 — 前后端全覆盖
  相关文件：git-hooks/pre-commit-verify, systemd/verify-watch.path, systemd/verify-watch.service
- [2026-05-23] [OP] 验证体系v3 | 变更: verify-pipeline.sh(修复白屏检测+路径)+post-edit-verify.sh(--auto+state)+pre-commit-verify(前后端双检)+verify-watch(后端目录监控) | 结果: 提交e2b0a6e已推送 | 关键: 前端build→screenshot→PIL白屏检测→diff, 后端syntax→test→service→HTTP, 统一verify-state.json{frontend,backend}
- [2026-05-23] [OP] 修复: 呼吸灯exit28连续失败 | 根因: opencode:8080进程D状态(393线程/2.6G/3.3Gswap)无HTTP响应 + caddy-launcher死(12:03起) | 修复: restart opencode-web + restart caddy-launcher | 预防: opencode内存上限3G偏低，swap 3.6G峰值需监控
- [2026-05-23] [OP] opencode-config-guard优化: timer轮询→inotify事件驱动 | MCP缺失检查已移除 | 仅监听opencode.json循环链接+JSON无效两项
- [2026-05-23] [OP] 微信Waybar闪烁修复: Hyprland添加 windowrulev2 = nourgency, class:wechat | 原因: 微信UOS发送X11 urgency hint导致Waybar工作区图标变为!并闪烁
- [2026-05-23] [OP] keyring静默: gnome-keyring取消密码提示 | 方法: rm keyring文件 + echo "" | gnome-keyring-daemon --unlock重建空密码keyring | 结果: login.keyring空密码创建成功，不再弹窗
- [2026-05-23] [OP] 修复: GitHub ERR_NO_SUPPORTED_PROXIES | 原因: ~/.config/kioslaverc 中 httpProxy/httpsProxy 端口为17890(应为7890)，socksProxy 格式错误使用了 socks:// 前缀 | 修复: 端口改为7890/7891，去除协议前缀(统一KDE格式)

### 会话摘要 [2026-05-23] [Sonnet/自动]
- 对话轮次: 15 | 被纠正: 1次
  - 用户纠正: 检查下opencode设置和配置哪里不对 要联网
- [2026-05-23] [OP] Moonlight FRP: NixOS Sunshine→FRP隧道→17698配置完成 | 路由器端口转发HTML表单不响应POST，需手动添加 | Moonlight连接: charlie1990.duckdns.org:17698

### 会话摘要 [2026-05-23] [Sonnet/自动]
- 对话轮次: 29 | 被纠正: 1次
  - 用户纠正: 检查下opencode设置和配置哪里不对 要联网
- [2026-05-23] [OP] Padavan DHCP静态绑定: 两步法 | Step1: POST到start_apply.htm action_mode=+Add+ → done_validating | Step2: POST action_mode=+Restart+ → done_committing | MAC格式: 无分隔符大写(8CEA12957E14) | 表单含sid_list=LANHostConfig%3B和所有dhcp字段

### 会话摘要 [2026-05-23] [Sonnet/自动]
- 对话轮次: 47 | 被纠正: 1次
  - 用户纠正: 检查下opencode设置和配置哪里不对 要联网
- [2026-05-23] [OP] 成功: Moonlight FRP 远程串流 | NixOS Sunshine→FRP 17698→DuckDNS→路由器 全链路 | 平板连接: charlie1990.duckdns.org:17698 | 路由器Padavan HTML表单POST/start_apply.htm + fetch API 提交 VSList 成功
