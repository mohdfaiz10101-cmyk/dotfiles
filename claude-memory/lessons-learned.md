
- [auto] 发现: router.port_forward.18700 = TCP 18700→192.168.123.209:18700 (openagents-net)

- [auto] 发现: router.port_forward.17698 = TCP 17698→192.168.123.209:17698 (win-ai)

- [auto] 发现: router.port_forward.7000 = TCP 7000→192.168.123.209:7000 (frps)

- [auto] 发现: router.port_forward.42111 = TCP 42111→192.168.123.209:42111 (Sisy-42111)

- [auto] 发现: router.port_forward.17699 = TCP 17699→192.168.123.209:17699 (nixos-ai)

- [auto] 发现: router.port_forward.8283 = TCP 8283→192.168.123.209:8284 (Letta-MCP)

- [auto] 发现: router.port_forward.7681 = TCP 7681→192.168.123.209:7681 (ttyd)

- [auto] 发现: router.port_forward.19890 = TCP 19890→192.168.123.209:19890 (Sisy-19890)

- [auto] 发现: router.port_forward.19892 = TCP 19892→192.168.123.209:19892 (Sisy-19892)

- [auto] 发现: router.port_forward.19893 = TCP 19893→192.168.123.209:19893 (Sisy-19893)

- [auto] 发现: router.port_forward.8888 = TCP 8888→192.168.123.209:18789 (OpenClaw-GW)

- [auto] 发现: router.port_forward.8080 = TCP 8080→192.168.123.209:8080 (OpenCode-Sisy)

- [auto] 发现: router.port_forward.2223 = TCP 2223→192.168.123.209:2223 (nixos-ssh)

- [auto] 发现: router.port_forward.18090 = TCP 18090→192.168.123.209:18090 (Sisy-18090)

- [auto] 发现: router.port_forward.18091 = TCP 18091→192.168.123.209:18091 (Sisy-18091)

- [auto] 发现: router.port_forward.19891 = TCP 19891→192.168.123.209:19891 (Sisy-19891)

- [auto] 发现: router.port_forward.18300 = TCP 18300→192.168.123.209:18300 (Sisy-18300)

- [auto] 发现: router.port_forward.2222 = TCP 2222→192.168.123.209:22 (NixOS-SSH)

- [auto] 发现: router.port_forward.12399 = UDP 12399→192.168.123.209:1235 (DF-Remote)

- [auto] 发现: router.port_forward.3456 = TCP 3456→192.168.123.209:9800 (Hub-API)

- [auto] 发现: router.port_forward.24801 = TCP 24801→192.168.123.209:24801 (ydotool)

- [auto] 发现: docker.container.letta-chromadb = 127.0.0.1:18000->8000/tcp | 状态: Up 37 minutes (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 38 minutes (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 38 minutes (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 38 minutes (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 38 minutes (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 38 minutes (healthy)

- [auto] 发现: docker.container.29cb7402b164_twenty-db-1 = 5432/tcp | 状态: Up 38 minutes (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 38 minutes (healthy)

- [auto] 发现: systemd.● = active

- [auto] 发现: systemd.● = active
- [2026-06-01] [OP] 修复: hermes FRP端口 | 根因: 19800/18092不在VPS allowPorts白名单 | 修复: 换18700(已在frps.toml白名单) | 教训: 新增FRP端口前先查~/ai-deploy/frps.toml

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 37 minutes (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 37 minutes (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 37 minutes (healthy)

- [auto] 发现: docker.container.29cb7402b164_twenty-db-1 = 5432/tcp | 状态: Up 37 minutes (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 37 minutes (healthy)

- [auto] 发现: docker.container.letta-chromadb = 127.0.0.1:18000->8000/tcp | 状态: Up 38 minutes (healthy)
- [2026-06-01] [OP] 修复: whisper重启风暴 | 根因: ggml-medium.bin缺失 | 修复: 停用服务 | 模型: 仅base可用 | 教训: 迁移后检查模型文件路径
- [2026-06-01] [OP] 修复: fcitx5搜索记忆丢失 | 根因: 0字节临时文件user.dict_yamBgz残留(04:00崩溃)+Wayland前端已知不稳定 | 修复: 清理残留文件+重启fcitx5+确认waylandim.conf已禁用 | 教训: fcitx5崩溃后可能留下0字节临时文件占用路径

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 45 minutes (healthy)

- [auto] 发现: docker.container.letta-chromadb = 127.0.0.1:18000->8000/tcp | 状态: Up 46 minutes (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 46 minutes (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 40 minutes (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 40 minutes (healthy)

- [auto] 发现: docker.container.letta-chromadb = 127.0.0.1:18000->8000/tcp | 状态: Up 56 minutes (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 56 minutes (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 56 minutes (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 49 minutes (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 56 minutes (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 56 minutes (healthy)

- [auto] 发现: docker.container.29cb7402b164_twenty-db-1 = 5432/tcp | 状态: Up 56 minutes (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 56 minutes (healthy)

- [auto] 发现: docker.container.musetalk = 0.0.0.0:9881->8000/tcp, [::]:9881->8000/tcp | 状态: Up 3 minutes

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 20 minutes (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 20 minutes (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 55 minutes (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 16 minutes (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 18 minutes (healthy)

- [auto] 发现: docker.container.letta-chromadb = 127.0.0.1:18000->8000/tcp | 状态: Up 18 minutes (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 24 minutes (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 15 minutes (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 15 minutes (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 26 minutes (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 27 minutes (healthy)

- [auto] 发现: docker.container.letta-chromadb = 127.0.0.1:18000->8000/tcp | 状态: Up 27 minutes (healthy)
- [2026-06-02] [OP] 分析: SSH多路径管理 | 发现: 已有SSH config v3(ControlMaster+多路径回退)+tmux+mosh+ttyd | 建议: 用ttyd作主入口+tmux持久化，SSH仅用于传输/转发

- [2026-06-02] [OP] 修复: context-pack未注入新任务 | 根因: memory-injector.py只从baseline.toml+lessons-learned提取，缺少user-preferences.md和decision-memory.md | 修复: 增强get_latest_memories()同时读取user-preferences.md(前6条偏好)+decision-memory.md(最近3条决策) | 教训: 任何新增的记忆文件类型都需要同步更新memory-injector的提取逻辑
- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 11 minutes (healthy)

- [auto] 发现: docker.container.musetalk = 0.0.0.0:9881->8000/tcp, [::]:9881->8000/tcp | 状态: Up 20 minutes

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 27 minutes (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 27 minutes (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 27 minutes (healthy)

- [2026-06-02] [OP] 网络拓扑系统化 | 创建 network-topology.md (统一视图+决策树) + port-allocator.sh (自动预检) + memory-injector 增强 (网络拓扑注入所有agent) | 解决问题: 每次新会话AI重新推理网络连接方式，FRP端口/路由器/公网等反复踩坑
- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 26 minutes (healthy)

- [auto] 发现: docker.container.e45c798cf3d5_litellm-litellm =  | 状态: Up 27 minutes (healthy)

- [auto] 发现: docker.container.29cb7402b164_twenty-db-1 = 5432/tcp | 状态: Up 27 minutes (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 27 minutes (healthy)

- [2026-06-02] [OP] 修复: 剪贴板不生效(node) | 根因: clip-sync 和 clipboard-sync-windows 两个服务同时运行，互相覆盖剪贴板内容 | 修复: 停用 clip-sync，保留 clipboard-sync-windows(直接PowerShell读Windows剪贴板更可靠) | 教训: 同类剪贴板同步服务只能保留一个- [2026-06-02] [OP] 部署 Termix | 端口: 9180 | 镜像: ghcr.io/lukegus/termix | 结果: 成功 | 位置: /mnt/ai/apps/termix/docker-compose.yml
