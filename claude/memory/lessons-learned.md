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
- [2026-05-21] [OP] cc-decision-engine.py 每10分钟生成"任务跟进" → memory op-tasks.md 堆积，需定期清理或修复生成逻辑
- [2026-05-21] [OP] Service-Nurse巡检: letta-chromadb 持续 unhealthy，需排查 ChromaDB 容器健康检查配置
- [2026-05-21] [OP] NixOS frp.nix 配置已包含 18092，但需 sudo nixos-rebuild switch 激活防火墙规则
- [2026-05-19] [OP] 成功记录: ibus Hyprland修复 | 调用: windowrule float=yes + Ctrl+Space bind + ibus-daemon --cache=refresh | 结果: config ok, dispatch works | 场景: ibus popup focus stealing + Ctrl+Space not switching
- [2026-05-20] [OP] 成功记录: ibus Ctrl+Space修复 | 调用: NixOS home-manager配置 + windowrule浮动 + hyprland keybind + /home/charlie/.local/bin/ibus-toggle.sh | 结果: config ok, dispatch works, rebuild成功 | 场景: Ctrl+Space不触发ibus切换

## NixOS rebuild 安全规则 (2026-05-21)
- rebuild 前 MUST 执行 `nixos-rebuild-safe`（构建→VM测试→通过才写boot）
- 禁止直接 `sudo nixos-rebuild switch` 后立刻 `sudo reboot`
- 禁止直接 `sudo nixos-rebuild boot && sudo reboot` 跳过 VM 测试
- VM 测试失败 → 不写 boot，先修配置
- AI agent 读到 `last-result.json` 中 overall=FAIL → 自动分析 failed_units 并建议修复
- 结果文件: `~/.cache/nixos-vm-test/last-result.json`
- MCP 查询: `nixos-vm-result --fail` 获取失败服务列表- [2026-05-21] [OP] 成功记录: chromadb健康检查修复 | 根因: chromadb/chroma镜像不含curl,健康检查test用curl导致持续unhealthy(OCI runtime exec failed: curl not found) | 修复: 改用CMD-SHELL + bash /dev/tcp端口检测 | 文件: /mnt/ai/ai-cluster/letta/docker-compose.yml

- [2026-05-21] [OP] 成功记录: Letta Telegram告警彻底修复 | 调用: 移除letta.service + 批量修复agent ID + 修复health-monitor hook检查 | 结果: health-monitor 0问题, Telegram通知正常 | 场景: 遗留systemd服务crash-loop + 硬编码错误agent ID导致API检查失败

- [2026-05-21] [OP] 修复 nixos-sysadmin agent ID 错误 | 错误ID: agent-f7473a7f / agent-8651643c | 正确ID: agent-0040ded4-1831-4b76-a4a4-62519a416a5a | 修复脚本: letta-distill, memory-router, glm-proxy | 根因: agent ID 变更后未同步更新所有引用
- [2026-05-21] [OP] 成功记录: 手机剪贴板同步 | 调用: phone-clip-sync + systemd user service + FRP 15555 | 结果: 服务已启动，等待手机上线 | 场景: NixOS ↔ Android 剪贴板双向同步
- [2026-05-21] [OP] 成功记录: 手机 FRP 隧道 | 调用: frpc 0.66.0 + Magisk service.d + TOML配置修复 | 结果: 15555端口开放，ADB over TCP可用 | 场景: OnePlus Ace 5 Pro 通过FRP隧道实现永远在线调试
- [2026-05-21] [OP] frpc TOML格式坑 | 错误: frpc.toml包含[common]节头导致配置不解析 | 修复: 必须省略[common]节头，直接写proxy/client配置 | 场景: frpc 0.66.0 TOML解析器不支持[common]节，需扁平化配置
- [2026-05-21] [OP] 修复 nixos-sysadmin agent ID 错误 | 错误ID: agent-8651643c-e753-47ed-9759-bd955c6ac240 | 正确ID: agent-0040ded4-1831-4b76-a4a4-62519a416a5a | 修复文件: discord_bot.py, hub-api.py | 根因: agent ID 变更后未同步更新所有引用

- [2026-05-21] [OP] 停用 glm-proxy 及相关服务 | 原因: 使用率极低(2天1次请求), 频繁崩溃, 有更好替代方案 | 停用: glm-proxy.service, agent-orchestrator.service, ai-watchdog.service, glm-monitor.service | 删除: glm-float, glm-task, glm-watch, glm-monitor, glm-health-check.sh, glm, glm-enhanced | 保留: LiteLLM(localhost:4000)作为统一模型路由
- [2026-05-21] [OP] 成功记录: opencode-autoupgrade修复 | 调用: 移除SOCKS5代理+增强重试逻辑 | 结果: GitHub下载正常(47M/32s)，复制重试3次 | 场景: GitHub下载通过SOCKS5代理超时，需直连
- [2026-05-21] [OP] 成功记录: opencode-session-guard验证 | 调用: dry-run检查+SQL查询 | 结果: 0损坏session(总525)，问题已恢复 | 场景: 之前报告3个损坏session，实际已自行清理

- [2026-05-21] [OP] 成功记录: OpenCode上下文优化 | 调用: 停止cc-decision-engine.timer + AGENTS.md添加MCP智能路由 + 创建opencode-smart-mcp启动器 | 结果: 任务跟进死循环已停止, MCP分级策略已定义 | 场景: OpenCode上下文被填满的根因是MCP调用爆炸+任务跟进死循环
- [2026-05-21] [OP] 成功记录: PipeWire Qt 警告修复 | 调用: 设置 LD_LIBRARY_PATH + 创建 playwright-mcp.service | 结果: 服务启动正常，qt.multimedia 警告消失 | 场景: Chrome Qt 组件加载 PipeWire 库失败
- [2026-05-21] [OP] 成功记录: Vector VRL 语法修复 | 调用: 简化 condition 为 .status == "failed" | 结果: 服务启动正常，日志流写入 /var/lib/ai-context/live-errors.json | 场景: VRL 不支持 ?? // unwrap_or coalesce 等操作符，需简化表达式
- [2026-05-21] [OP] 成功记录: FRP phone-adb 代理修复 | 调用: frpc localPort=5555 + remotePort=60004 | 结果: 双代理(phone-adb+phone-ssh)均注册成功, ADB over FRP可用 | 场景: phone-adb localPort必须匹配adbd实际监听端口5555, remotePort选未占用allowPorts(60004)
- [2026-05-21] [OP] 成功记录: OpenCode呼吸灯监控 | 调用: opencode-health-monitor.sh + systemd timer 5min | 结果: 7项检查全通过，呼吸灯green | 场景: OpenCode Web/LiteLLM/Letta/磁盘/内存多探针监控
- [2026-05-21] [OP] 失败学习: Windows USB设备修复 | 错误调用: Disable-PnpDevice + Enable-PnpDevice 循环20+次 | 错误: CM_PROB_PHANTOM 持续Unknown | 正确用法: 需人工检查USB线/驱动/设备本身 | 原因: 软件层面无法修复Phantom设备，可能是硬件接触不良或驱动深度问题
- [2026-05-21] [OP] 成功记录: waybar ck_opencode race condition 修复 | 调用: 移除 ss -tlnp | grep 检查，改用 curl 直接探测 | 结果: 并行执行稳定，不再误报 CRITICAL | 场景: waybar-health.sh 10项并行检查，ss 命令在后台并行时偶发返回空
- [2026-05-21] [OP] 成功记录: claude-knowledge MCP 恢复 | 调用: opencode.json 添加 claude-knowledge 配置 + 验证 mcp list | 结果: 11个MCP全部connected，claude-knowledge提供本地记忆访问 | 场景: 替代context7云端文档库，免费离线访问memory/*.md
- [2026-05-21] [OP] 失败学习: 手机ADB连接 | 错误调用: adb connect 192.168.123.136:5555 | 错误: 连接被拒绝10061 | 正确用法: 需在手机上确认ADB over TCP已启用且防火墙允许5555 | 原因: 手机端网络/防火墙/ADB配置问题，Windows侧已完成(防火墙规则+ADB服务)
