# 核心经验（≤50行，2026-05-18 精简）

<!-- DEAD_RULE: search命中backup/恢复/灾难/永久化类文件名时，MUST先read该文件全文再执行任何操作 -->

## 行为规则
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

- [auto] 发现: router.port_forward.17699 = TCP 17699→192.168.123.209:17699 (nixos-ai)

- [auto] 发现: router.port_forward.19890 = TCP 19890→192.168.123.209:19890 (Sisy-19890)

- [auto] 发现: router.port_forward.3456 = TCP 3456→192.168.123.209:9800 (Hub-API)

- [auto] 发现: router.port_forward.7681 = TCP 7681→192.168.123.209:7681 (ttyd)

- [auto] 发现: router.port_forward.19892 = TCP 19892→192.168.123.209:19892 (Sisy-19892)

- [auto] 发现: router.port_forward.8888 = TCP 8888→192.168.123.209:18789 (OpenClaw-GW)

- [auto] 发现: router.port_forward.7000 = TCP 7000→192.168.123.209:7000 (frps)

- [auto] 发现: router.port_forward.18700 = TCP 18700→192.168.123.209:18700 (openagents-net)

- [auto] 发现: router.port_forward.19891 = TCP 19891→192.168.123.209:19891 (Sisy-19891)

- [auto] 发现: router.port_forward.2222 = TCP 2222→192.168.123.209:22 (NixOS-SSH)

- [auto] 发现: router.port_forward.8080 = TCP 8080→192.168.123.209:8080 (OpenCode-Sisy)

- [auto] 发现: router.port_forward.19893 = TCP 19893→192.168.123.209:19893 (Sisy-19893)

- [auto] 发现: router.port_forward.18300 = TCP 18300→192.168.123.209:18300 (Sisy-18300)

- [auto] 发现: router.port_forward.8283 = TCP 8283→192.168.123.209:8284 (Letta-MCP)

- [auto] 发现: router.port_forward.2223 = TCP 2223→192.168.123.209:2223 (nixos-ssh)

- [auto] 发现: router.port_forward.18090 = TCP 18090→192.168.123.209:18090 (Sisy-18090)

- [auto] 发现: router.port_forward.24801 = TCP 24801→192.168.123.209:24801 (ydotool)

- [auto] 发现: router.port_forward.17698 = TCP 17698→192.168.123.209:17698 (win-ai)

- [auto] 发现: router.port_forward.18091 = TCP 18091→192.168.123.209:18091 (Sisy-18091)

- [auto] 发现: docker.container.khoj-server-1 = 0.0.0.0:42110->42110/tcp, [::]:42110->42110/tcp | 状态: Up 2 hours

- [auto] 发现: docker.container.khoj-database-1 = 5432/tcp | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 10 hours

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 10 hours

- [auto] 发现: docker.container.letta-chromadb =  | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.khoj-server-1 = 0.0.0.0:42110->42110/tcp, [::]:42110->42110/tcp | 状态: Up 3 hours

- [auto] 发现: docker.container.khoj-database-1 = 5432/tcp | 状态: Up 4 hours (healthy)

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 11 hours

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 11 hours

- [auto] 发现: docker.container.letta-chromadb =  | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 11 hours (healthy)

- [2026-05-24] [OP] waybar永久化: 根因是home-manager `xdg.configFile."waybar/config".force=true` 会在每次rebuild时覆盖symlink。之前手动 `ln -sf config.override config` 是临时方案。永久方案: waybar.service 的 ExecStart 加 `--config config.override --style style.override.css`，绕开home-manager symlink。第二bar(19:08的24px bar)因nix store GC已不可恢复。
- [auto] 发现: docker.container.khoj-server-1 = 0.0.0.0:42110->42110/tcp, [::]:42110->42110/tcp | 状态: Up 4 hours

- [auto] 发现: docker.container.khoj-database-1 = 5432/tcp | 状态: Up 5 hours (healthy)

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 12 hours

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 12 hours

- [auto] 发现: docker.container.letta-chromadb =  | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 12 hours (healthy)

- [2026-05-25] [OP] opencode-web端口已改为8081（非8080），但dstate-watchdog/health-monitor脚本仍检查8080导致持续失败。修复：禁用旧watchdog+创建8080→8081 TCP代理。
- [2026-05-25] [OP] mem0-file-sync/mem0-watchdog因mem0-bridge Docker未运行导致TimeoutError持续失败 — 已禁用timer。
- [2026-05-25] [OP] waybar双bar恢复: 第二bar(24px)含custom/chain(链路呼吸灯)+custom/finance(财务还款), CSS加到style.override.css。永久化: waybar.service用--config config.override绕开home-manager symlink覆盖。# cis-test
# cis-debug
# t1
# t2

- [2026-05-25] [OP] nixos_persistence: 创建/修改系统服务MUST用systemctl --user + ~/.config/systemd/user/，禁止往/etc/systemd/system/写文件。脚本MUST放~/bin/或~/.local/bin/，禁止放/usr/local/bin/。每次nixos-rebuild后自动跑systemctl --user list-units --state=failed验证。# final-cis-test 1779639485
# final-cis-test2 1779639540

- [2026-05-25] [OP] 记忆系统故障根因: opencode-session-recorder.py 脚本存在但无systemd服务, tmux kill后会话内容全部丢失。mem0-file-sync/mem0-watchdog timer未启用。daily/目录存在但无自动生成机制。修复: 创建recorder service(daemon模式)+mem0 timers启用+TimeoutStartSec→300+daily-log-generator定时器。# array-test 1779639613

- [auto] 发现: docker.container.khoj-server-1 = 0.0.0.0:42110->42110/tcp, [::]:42110->42110/tcp | 状态: Up 5 hours

- [auto] 发现: docker.container.khoj-database-1 = 5432/tcp | 状态: Up 6 hours (healthy)

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 13 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 13 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 13 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 13 hours

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 13 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 13 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 13 hours (healthy)

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 13 hours

- [auto] 发现: docker.container.letta-chromadb =  | 状态: Up 13 hours (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 43 minutes (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 13 hours (healthy)

- [2026-05-25] [OP] 失败学习: config-immutable-snapshot | 错误: inotifywait+while-read管道中set -eo pipefail导致while循环静默退出 | 正确: 移除set -e，用显式错误处理替代 | 原因: pipefail+set -e组合在管道子命令返回非零时立即终止管道，不产生任何输出或日志
- [auto] 发现: docker.container.khoj-server-1 = 0.0.0.0:42110->42110/tcp, [::]:42110->42110/tcp | 状态: Up 6 hours

- [auto] 发现: docker.container.khoj-database-1 = 5432/tcp | 状态: Up 7 hours (healthy)

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 14 hours

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 14 hours

- [auto] 发现: docker.container.letta-chromadb =  | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.khoj-server-1 = 0.0.0.0:42110->42110/tcp, [::]:42110->42110/tcp | 状态: Up 8 hours

- [auto] 发现: docker.container.khoj-database-1 = 5432/tcp | 状态: Up 8 hours (healthy)

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 15 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 15 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 15 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 15 hours

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 15 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 15 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 15 hours (healthy)

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 15 hours

- [auto] 发现: docker.container.letta-chromadb =  | 状态: Up 15 hours (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 15 hours (healthy)

- [auto] 发现: docker.container.khoj-database-1 = 5432/tcp | 状态: Up 9 hours (healthy)

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 16 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 16 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 16 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 16 hours

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 16 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 16 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 16 hours (healthy)

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 16 hours

- [auto] 发现: docker.container.letta-chromadb =  | 状态: Up 16 hours (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 4 hours (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 16 hours (healthy)

- [auto] 发现: docker.container.khoj-server-1 = 0.0.0.0:42110->42110/tcp, [::]:42110->42110/tcp | 状态: Up 9 hours

- [auto] 发现: docker.container.khoj-database-1 = 5432/tcp | 状态: Up 10 hours (healthy)

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 17 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 17 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 17 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 17 hours

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 17 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 17 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 17 hours (healthy)

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 17 hours

- [auto] 发现: docker.container.letta-chromadb =  | 状态: Up 17 hours (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 5 hours (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 17 hours (healthy)

- [auto] 发现: docker.container.khoj-server-1 = 0.0.0.0:42110->42110/tcp, [::]:42110->42110/tcp | 状态: Up 10 hours

- [auto] 发现: docker.container.khoj-database-1 = 5432/tcp | 状态: Up 11 hours (healthy)

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 18 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 18 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 18 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 18 hours

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 18 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 18 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 18 hours (healthy)

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 18 hours

- [auto] 发现: docker.container.letta-chromadb =  | 状态: Up 18 hours (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 6 hours (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 18 hours (healthy)

- [auto] 发现: docker.container.khoj-server-1 = 0.0.0.0:42110->42110/tcp, [::]:42110->42110/tcp | 状态: Up 11 hours

- [auto] 发现: docker.container.khoj-database-1 = 5432/tcp | 状态: Up 12 hours (healthy)

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 19 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 19 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 19 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 19 hours

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 19 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 19 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 19 hours (healthy)

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 19 hours

- [auto] 发现: docker.container.letta-chromadb =  | 状态: Up 19 hours (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 7 hours (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 19 hours (healthy)

- [auto] 发现: docker.container.khoj-server-1 = 0.0.0.0:42110->42110/tcp, [::]:42110->42110/tcp | 状态: Up 12 hours

- [auto] 发现: docker.container.khoj-database-1 = 5432/tcp | 状态: Up 13 hours (healthy)

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 20 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 20 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 20 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 20 hours

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 20 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 20 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 20 hours (healthy)

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 20 hours

- [auto] 发现: docker.container.letta-chromadb =  | 状态: Up 20 hours (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 8 hours (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 20 hours (healthy)

- [auto] 发现: docker.container.khoj-server-1 = 0.0.0.0:42110->42110/tcp, [::]:42110->42110/tcp | 状态: Up 13 hours

- [auto] 发现: docker.container.khoj-database-1 = 5432/tcp | 状态: Up 14 hours (healthy)

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 21 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 21 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 21 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 21 hours

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 21 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 21 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 21 hours (healthy)

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 21 hours

- [auto] 发现: docker.container.letta-chromadb =  | 状态: Up 21 hours (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 9 hours (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 21 hours (healthy)

- [2026-05-25] [OP] 添加 git 桌面通知: memory-auto-commit → git commit 后弹出 "记忆备份: {文件名}"; git-backup.sh → 完成后弹出总结(失败时带 ⚠️ 警告)
- [auto] 发现: docker.container.khoj-server-1 = 0.0.0.0:42110->42110/tcp, [::]:42110->42110/tcp | 状态: Up 15 hours

- [auto] 发现: docker.container.khoj-database-1 = 5432/tcp | 状态: Up 16 hours (healthy)

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 23 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 23 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 23 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 23 hours

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 23 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 23 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 23 hours (healthy)

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 23 hours

- [auto] 发现: docker.container.letta-chromadb =  | 状态: Up 23 hours (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 23 hours (healthy)

- [auto] 发现: docker.container.khoj-server-1 = 0.0.0.0:42110->42110/tcp, [::]:42110->42110/tcp | 状态: Up 16 hours

- [auto] 发现: docker.container.khoj-database-1 = 5432/tcp | 状态: Up 17 hours (healthy)

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 24 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 24 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 24 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 24 hours

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 24 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 24 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 24 hours (healthy)

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 24 hours

- [auto] 发现: docker.container.letta-chromadb =  | 状态: Up 24 hours (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 24 hours (healthy)

- [2026-05-25] [OP] 修复"外网不通"频繁告警根因: (1) opencode-web hang导致8080/8081端口无响应 → 重启解决 (2) waybar-health.sh+waybar-score.sh的ck_ocpub检查走代理而非--noproxy'*'，代理慢时超时误报 (3) connectivity-chain-watchdog.sh wan_reachable变量未绑定导致set -euo pipefail崩溃 → 加${var:-default}保护- [2026-05-24] [OP] 8088页面加归档/删除按钮: smart-redirector.py PAGE_HTML加archive/delete JS函数+srow布局+sact样式+do_GET生成按钮行 | archive后端修复: 写opencode.db time_archived(旧版只写本地文件不写DB) + kill-window用_find_oc_window搜索(旧oc_{16}命名错误)

- [auto] 发现: docker.container.khoj-server-1 = 0.0.0.0:42110->42110/tcp, [::]:42110->42110/tcp | 状态: Up 17 hours

- [auto] 发现: docker.container.khoj-database-1 = 5432/tcp | 状态: Up 18 hours (healthy)

- [auto] 发现: docker.container.twenty-server-1 = 0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp | 状态: Up 25 hours (healthy)

- [auto] 发现: docker.container.twenty-db-1 = 5432/tcp | 状态: Up 25 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 25 hours (healthy)

- [auto] 发现: docker.container.langfuse = 127.0.0.1:3010->3000/tcp | 状态: Up 25 hours

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 25 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 25 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 25 hours (healthy)

- [auto] 发现: docker.container.n8n = 0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp | 状态: Up 25 hours

- [auto] 发现: docker.container.letta-chromadb =  | 状态: Up 25 hours (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 25 hours (healthy)
