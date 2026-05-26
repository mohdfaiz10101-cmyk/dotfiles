# 核心经验（≤50行，2026-05-18 精简）

<!-- DEAD_RULE: search命中backup/恢复/灾难/永久化类文件名时，MUST先read该文件全文再执行任何操作 -->

## 行为规则
- [2026-05-26] [OP] 用户有 coding plan 时，MUST 先等 plan 再执行，禁止自行设计架构和实现。即使用户未主动提供 plan，也应先确认是否存在 plan。
- [2026-05-24] [OP] THINKING_CLEANUP: 任务完成后MUST回溯思考过程中遇到的工具调用失败/配置缺失/权限不足/依赖缺失等所有阻碍，强制解决并记录。禁止以"任务已完成"为由遗留未解决的问题。

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

- [auto] 发现: router.port_forward.18300 = TCP 18300→192.168.123.209:18300 (Sisy-18300)

- [auto] 发现: router.port_forward.12399 = UDP 12399→192.168.123.209:1235 (DF-Remote)

- [auto] 发现: router.port_forward.8888 = TCP 8888→192.168.123.209:18789 (OpenClaw-GW)

- [auto] 发现: router.port_forward.19892 = TCP 19892→192.168.123.209:19892 (Sisy-19892)

- [auto] 发现: router.port_forward.2222 = TCP 2222→192.168.123.209:22 (NixOS-SSH)

- [auto] 发现: router.port_forward.17698 = TCP 17698→192.168.123.209:17698 (win-ai)

- [auto] 发现: router.port_forward.2223 = TCP 2223→192.168.123.209:2223 (nixos-ssh)

- [auto] 发现: router.port_forward.17699 = TCP 17699→192.168.123.209:17699 (nixos-ai)

- [auto] 发现: router.port_forward.19890 = TCP 19890→192.168.123.209:19890 (Sisy-19890)

- [auto] 发现: router.port_forward.19891 = TCP 19891→192.168.123.209:19891 (Sisy-19891)

- [auto] 发现: router.port_forward.19893 = TCP 19893→192.168.123.209:19893 (Sisy-19893)

- [auto] 发现: router.port_forward.18090 = TCP 18090→192.168.123.209:18090 (Sisy-18090)

- [auto] 发现: router.port_forward.24801 = TCP 24801→192.168.123.209:24801 (ydotool)

- [auto] 发现: router.port_forward.42111 = TCP 42111→192.168.123.209:42111 (Sisy-42111)

- [auto] 发现: router.port_forward.3456 = TCP 3456→192.168.123.209:9800 (Hub-API)

- [auto] 发现: router.port_forward.7681 = TCP 7681→192.168.123.209:7681 (ttyd)

- [auto] 发现: router.port_forward.8283 = TCP 8283→192.168.123.209:8284 (Letta-MCP)

- [auto] 发现: router.port_forward.18700 = TCP 18700→192.168.123.209:18700 (openagents-net)

- [auto] 发现: router.port_forward.18091 = TCP 18091→192.168.123.209:18091 (Sisy-18091)

- [auto] 发现: router.port_forward.8080 = TCP 8080→192.168.123.209:8080 (OpenCode-Sisy)

- [auto] 发现: router.port_forward.7000 = TCP 7000→192.168.123.209:7000 (frps)

- [auto] 发现: docker.container.dfremote = 0.0.0.0:1235->1235/udp, [::]:1235->1235/udp | 状态: Up 52 minutes

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 2 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 2 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 2 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.rss-freshrss-1 = 127.0.0.1:8420->80/tcp | 状态: Up 36 minutes (unhealthy)

- [auto] 发现: docker.container.dfremote = 0.0.0.0:1235->1235/udp, [::]:1235->1235/udp | 状态: Up 3 hours

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 3 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 3 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 3 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.rss-freshrss-1 = 127.0.0.1:8420->80/tcp | 状态: Up About a minute (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 4 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 4 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 4 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 4 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 4 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 4 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 4 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 4 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 4 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 4 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 4 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 4 hours (healthy)

- [auto] 发现: docker.container.rss-freshrss-1 = 127.0.0.1:8420->80/tcp | 状态: Up About an hour (healthy)

- [auto] 发现: docker.container.dfremote = 0.0.0.0:1235->1235/udp, [::]:1235->1235/udp | 状态: Up 4 hours

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 5 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 5 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 5 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 5 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 5 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 5 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 5 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 5 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 5 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 5 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 5 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 5 hours (healthy)

- [auto] 发现: docker.container.rss-freshrss-1 = 127.0.0.1:8420->80/tcp | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.dfremote = 0.0.0.0:1235->1235/udp, [::]:1235->1235/udp | 状态: Up 5 hours

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 6 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 6 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 6 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 6 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 6 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 6 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 6 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 6 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 6 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 6 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 6 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 6 hours (healthy)

- [auto] 发现: docker.container.rss-freshrss-1 = 127.0.0.1:8420->80/tcp | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.dfremote = 0.0.0.0:1235->1235/udp, [::]:1235->1235/udp | 状态: Up 6 hours

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 7 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 7 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 7 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 7 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 7 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 7 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 7 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 7 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 7 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 7 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 7 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 7 hours (healthy)

- [auto] 发现: docker.container.rss-freshrss-1 = 127.0.0.1:8420->80/tcp | 状态: Up 4 hours (healthy)

- [auto] 发现: docker.container.dfremote = 0.0.0.0:1235->1235/udp, [::]:1235->1235/udp | 状态: Up 7 hours

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 8 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 8 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 8 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 8 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 8 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 8 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 8 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 8 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 8 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 8 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 8 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 8 hours (healthy)

- [auto] 发现: docker.container.rss-freshrss-1 = 127.0.0.1:8420->80/tcp | 状态: Up 5 hours (healthy)

- [auto] 发现: docker.container.dfremote = 0.0.0.0:1235->1235/udp, [::]:1235->1235/udp | 状态: Up 8 hours

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 9 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 9 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 9 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 9 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 9 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 9 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 9 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 9 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 9 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 9 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 9 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 9 hours (healthy)

- [auto] 发现: docker.container.rss-freshrss-1 = 127.0.0.1:8420->80/tcp | 状态: Up 6 hours (healthy)

- [auto] 发现: docker.container.dfremote = 0.0.0.0:1235->1235/udp, [::]:1235->1235/udp | 状态: Up 9 hours

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 10 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 10 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 10 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.rss-freshrss-1 = 127.0.0.1:8420->80/tcp | 状态: Up 7 hours (healthy)

- [auto] 发现: docker.container.dfremote = 0.0.0.0:1235->1235/udp, [::]:1235->1235/udp | 状态: Up 10 hours

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 11 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 11 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 11 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.rss-freshrss-1 = 127.0.0.1:8420->80/tcp | 状态: Up 8 hours (healthy)

- [auto] 发现: docker.container.dfremote = 0.0.0.0:1235->1235/udp, [::]:1235->1235/udp | 状态: Up 11 hours

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 12 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 12 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 12 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.rss-freshrss-1 = 127.0.0.1:8420->80/tcp | 状态: Up 9 hours (healthy)

- [auto] 发现: docker.container.dfremote = 0.0.0.0:1235->1235/udp, [::]:1235->1235/udp | 状态: Up 12 hours

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 13 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 13 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 13 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 13 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 13 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 13 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 13 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 13 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 13 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 13 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 13 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 13 hours (healthy)

- [auto] 发现: docker.container.rss-freshrss-1 = 127.0.0.1:8420->80/tcp | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.dfremote = 0.0.0.0:1235->1235/udp, [::]:1235->1235/udp | 状态: Up 13 hours

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 14 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 14 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 14 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.rss-freshrss-1 = 127.0.0.1:8420->80/tcp | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.dfremote = 0.0.0.0:1235->1235/udp, [::]:1235->1235/udp | 状态: Up 14 hours

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 15 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 15 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 15 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 15 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 15 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 15 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 15 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 15 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 15 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 15 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 15 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 15 hours (healthy)

- [auto] 发现: docker.container.rss-freshrss-1 = 127.0.0.1:8420->80/tcp | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.dfremote = 0.0.0.0:1235->1235/udp, [::]:1235->1235/udp | 状态: Up 15 hours

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 16 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 16 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 16 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 16 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 16 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 16 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 16 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 16 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 16 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 16 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 16 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 16 hours (healthy)
- [2026-05-26] [OP] 失败学习: mem0_watchdog.py | 错误: UnboundLocalError "failed" used before definition (line 235 before line 244) | 修复: 将 failed = [...] 移到 Telegram通知块之前 | 原因: 变量定义在使用之后

- [auto] 发现: docker.container.rss-freshrss-1 = 127.0.0.1:8420->80/tcp | 状态: Up 13 hours (healthy)

- [auto] 发现: docker.container.dfremote = 0.0.0.0:1235->1235/udp, [::]:1235->1235/udp | 状态: Up 16 hours

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 17 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 17 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 17 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 17 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 17 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 17 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 17 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 17 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 17 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 17 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 17 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 17 hours (healthy)

- [auto] 发现: docker.container.rss-freshrss-1 = 127.0.0.1:8420->80/tcp | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.dfremote = 0.0.0.0:1235->1235/udp, [::]:1235->1235/udp | 状态: Up 17 hours

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 18 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 18 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 18 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 18 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 18 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 18 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 18 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 18 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 18 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 18 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 18 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 18 hours (healthy)

- [auto] 发现: docker.container.rss-freshrss-1 = 127.0.0.1:8420->80/tcp | 状态: Up 15 hours (healthy)

- [auto] 发现: docker.container.dfremote = 0.0.0.0:1235->1235/udp, [::]:1235->1235/udp | 状态: Up 18 hours

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 19 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 19 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 19 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 19 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 19 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 19 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 19 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 19 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 19 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 19 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 19 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 19 hours (healthy)

- [auto] 发现: docker.container.rss-freshrss-1 = 127.0.0.1:8420->80/tcp | 状态: Up 16 hours (healthy)

- [auto] 发现: docker.container.dfremote = 0.0.0.0:1235->1235/udp, [::]:1235->1235/udp | 状态: Up 19 hours

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 20 hours (healthy)

- [auto] 发现: docker.container.twenty-worker-1 =  | 状态: Up 20 hours

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 20 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 20 hours

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 20 hours

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 20 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 20 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 20 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 20 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 20 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 20 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp | 状态: Up 20 hours (healthy)

- [2026-05-26] [OP] AUTO_SKILL_PROTOCOL 部署: CLAUDE.md 新增死规则 — CC 完成复杂任务后智能评估 → macg_op_delegate 委托 Sisyphus → Sisyphus 加载 auto-skill 判断 → 满足 ≥2 条标准则执行 create-skill.py 封装 | 全自动闭环，禁止询问确认
- [2026-05-26] [OP] 发现: anti-restart-loop.sh | 机制: 每60秒扫描journal "Scheduled restart job"，>10次/60秒→systemctl stop | 今天15:59因strace调试导致14次崩溃→触发stop | strace已部署 --trace=signal --signal=SIGTERM -f 监控原始问题
- [2026-05-26] [OP] 失败学习: anti-restart-loop watchdog | 错误: 检测"Scheduled restart job"后stop服务，但Restart=on-failure触发重启→无限循环 | 修复: 禁用timer，改用systemd原生StartLimitBurst+StartLimitIntervalSec限流 | 原因: 看门狗与systemd重启机制冲突