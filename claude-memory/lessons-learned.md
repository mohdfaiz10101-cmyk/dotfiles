
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

- [2026-06-02] [OP] rofi keybinding冲突: 自定义kb-*在config.rasi中与rofi默认键位冲突，报"already bound"错误。修复: 移除所有自定义键位，依赖rofi默认(vim键位通过rofi原生支持，无需手动配置)。教训: rofi 2.0的kb-*配置会叠加而非覆盖默认键位，添加自定义键位前必须验证无冲突。
- [runbook] RB-20260602-wechat-crash: 微信uos coredump重启风暴 | detect: journalctl --user -u wechat-uos -n 5 | grep -c coredump | fix: systemctl --user stop wechat-uos && sleep 2 && systemctl --user start wechat-uos | verify: sleep 5 && systemctl --user show wechat-uos --property=ActiveState | grep -q active
- [runbook] RB-20260602-fcitx5-crash: fcitx5崩溃后0字节残留文件 | detect: ls -la ~/.local/share/fcitx5/pinyin/user.dict_* | grep " 0 " | fix: 清理残留文件+重启fcitx5 | verify: pgrep fcitx5 && test -s ~/.local/share/fcitx5/pinyin/user.dict
- [runbook] RB-20260602-frp-port: frp端口不在白名单 | detect: journalctl --user -u hermes -n 10 | grep "port.*not.*allowed" | fix: 查~/ai-deploy/frps.toml白名单，换已注册端口 | verify: systemctl --user restart hermes && sleep 2 && systemctl --user show hermes --property=Result | grep success
- [2026-06-02] [OP] 修复: wechat-uos崩溃重启风暴 | 根因: DISPLAY=:1 但实际XWayland只有:0 | 修复: 改DISPLAY=:0后正常 | 教训: 检查X11显示号与实际情况是否匹配
- [2026-06-02] [OP] rofi恢复+增强: 之前被其他AI改回dmenu模式。修复: (1) 改用原生drun模式(图标+分类) (2) 拼音通过生成~/.local/share/applications/pinyin-*.desktop文件注入Keywords字段 (3) drun-match-fields包含keywords实现拼音搜索 (4) sidebar-mode: true启用分类侧栏。教训: rofi 2.0的kb-*配置会叠加默认键位导致冲突，不要自定义键位。拼音搜索通过生成desktop条目注入Keywords比dmenu缓存更优雅。- [2026-06-02] [OP] 根因定位: Connection reset | 根因: verify-watch.service每次bun build峰值2.4GB→zram 92%满→swap风暴→TCP超时RST | 修复: verify-pipeline.sh加内存守卫(可用<4G跳过)+并发锁(5分钟冷却) | 频率: 今天已触发110次

- [2026-06-02] [OP] 诊断: "tool not allowed while generating summary" 反复出现 | 根因: OpenCode compaction 期间工具调用被拦截，系统提示词+工具定义过大(150+ skills, 大量MCP工具)导致频繁触发压缩 | 触发条件: 上下文超过 compaction.reserved=16384 tokens 阈值 | 影响: 任务执行中断，工具调用被拒绝 | 缓解方案: (1) 用户手动 /clear 重置会话 (2) 减少AGENTS.md体积(当前~2000行) (3) 增大reserved阈值延迟压缩 | 无法由OP自动修复: 需要修改opencode.json(CONFIG_PROTECT)或重构AGENTS.md
- [auto] 发现: docker.container.khoj-server-1 = 0.0.0.0:42110->42110/tcp | 状态: Up 3 minutes (healthy)

- [auto] 发现: docker.container.khoj-database-1 = 5432/tcp | 状态: Up 5 minutes (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 27 minutes (healthy)

- [auto] 发现: docker.container.termix = 30001-30006/tcp, 0.0.0.0:9180->8080/tcp, [::]:9180->8080/tcp | 状态: Up 5 minutes (healthy)

- [2026-06-02] [AUTO] 偏好: op-tasks执行位置 | 内容: 用户要求以后所有op-tasks在OpenClaw workspace处理，不等待其他agent- [2026-06-02] [OP] 修复: 剪贴板复制后粘贴内容不对(复发) | 根因: (1) clip-sync + clipboard-sync-windows 两个Windows同步同时运行竞争 (2) clipboard-sync-windows 的 get_win_clipboard() PowerShell命令引号嵌套在SSH传输中损坏，返回ParserError错误文本被当作"剪贴板内容"写入wl-copy | 修复: 停用clip-sync(duplicate)，修复PowerShell命令为简单的Get-Clipboard -Raw | 教训: 之前修过一次同类问题但clip-sync被重新启用，需要确保只有一个Windows同步服务

- [auto] 发现: docker.container.letta-chromadb = 127.0.0.1:18000->8000/tcp | 状态: Up 26 minutes (healthy)

- [auto] 发现: docker.container.khoj-server-1 = 0.0.0.0:42110->42110/tcp | 状态: Up 25 minutes (healthy)

- [auto] 发现: docker.container.khoj-database-1 = 5432/tcp | 状态: Up 26 minutes (healthy)

- [auto] 发现: docker.container.termix = 30001-30006/tcp, 0.0.0.0:9180->8080/tcp, [::]:9180->8080/tcp | 状态: Up 6 minutes (healthy)

- [2026-06-02] [OP] 修复: phone-connect-mcp.py 设备选择逻辑缺陷 | 根因: (1) _dedup_devices返回标签(phone-tailscale1)而非实际地址(100.108.28.44:5555)，导致adb -s用无效设备ID (2) ensure_connected默认方法跳过tailscale1(100.108.28.44)直接试tailscale2(离线)和FRP(不通ADB) (3) force_method匹配用标签子串但设备列表已变为实际地址 | 修复: (1) _dedup_devices改为返回实际地址 (2) 新增DEVICE_PHYSICAL映射表用于物理设备去重 (3) 默认方法加入tailscale1作为第一优先 (4) force_method匹配改用_device_label()转换 | 教训: MCP连接地址≠标签名，_dedup_devices返回的值必须adb -s可直接使用
[2026-06-02] [OP] Termix Cloudflare 隧道: 用 cloudflared tunnel --url http://127.0.0.1:9180 暴露 Termix 到公网。之前 tailscale serve/funnel DNS 在手机端解析超时，换 Cloudflare 临时隧道绕过。域名: dublin-third-delayed-geology.trycloudflare.com。已创建 systemd 用户服务 cloudflared-termix.service 持久化。
[2026-06-02] [OP] Termix 公网双隧道: (1) Cloudflare quick tunnel → dublin-third-delayed-geology.trycloudflare.com (2) FRP → charlie1990.duckdns.org:19180。Termix Docker 容器已设置 restart: always。frps 服务改为 systemd --user 管理，避免端口冲突。
- [auto] 发现: docker.container.termix = 30001-30006/tcp, 0.0.0.0:9180->8080/tcp, [::]:9180->8080/tcp | 状态: Up 3 minutes (healthy)

- [auto] 发现: docker.container.letta-chromadb = 127.0.0.1:18000->8000/tcp | 状态: Up 21 minutes (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 21 minutes (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 21 minutes (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 21 minutes (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 21 minutes (healthy)

- [auto] 发现: docker.container.a33ac849549c_litellm-litellm =  | 状态: Up 21 minutes (healthy)

- [auto] 发现: docker.container.29cb7402b164_twenty-db-1 = 5432/tcp | 状态: Up 20 minutes (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 20 minutes (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 20 minutes (healthy)

- [auto] 发现: docker.container.letta-chromadb = 127.0.0.1:18000->8000/tcp | 状态: Up 20 minutes (healthy)

- [auto] 发现: docker.container.a33ac849549c_litellm-litellm =  | 状态: Up 20 minutes (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 20 minutes (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 20 minutes (healthy)

- [auto] 发现: docker.container.letta-chromadb = 127.0.0.1:18000->8000/tcp | 状态: Up 19 minutes (healthy)

- [auto] 发现: docker.container.29cb7402b164_twenty-db-1 = 5432/tcp | 状态: Up 19 minutes (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 19 minutes (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 19 minutes (healthy)

- [auto] 发现: docker.container.a33ac849549c_litellm-litellm =  | 状态: Up 19 minutes (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 19 minutes (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 19 minutes (healthy)

- [auto] 发现: docker.container.29cb7402b164_twenty-db-1 = 5432/tcp | 状态: Up 18 minutes (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 18 minutes (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 18 minutes (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 18 minutes (healthy)

- [auto] 发现: docker.container.a33ac849549c_litellm-litellm =  | 状态: Up 18 minutes (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 18 minutes (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 19 minutes (healthy)

- [auto] 发现: docker.container.letta-chromadb = 127.0.0.1:18000->8000/tcp | 状态: Up 16 minutes (healthy)

- [auto] 发现: docker.container.29cb7402b164_twenty-db-1 = 5432/tcp | 状态: Up 16 minutes (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 16 minutes (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 16 minutes (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 16 minutes (healthy)

- [auto] 发现: docker.container.a33ac849549c_litellm-litellm =  | 状态: Up 16 minutes (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 16 minutes (healthy)

- [auto] 发现: docker.container.letta-chromadb = 127.0.0.1:18000->8000/tcp | 状态: Up 14 minutes (healthy)

- [auto] 发现: docker.container.29cb7402b164_twenty-db-1 = 5432/tcp | 状态: Up 14 minutes (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 14 minutes (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 14 minutes (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 14 minutes (healthy)

- [auto] 发现: docker.container.a33ac849549c_litellm-litellm =  | 状态: Up 14 minutes (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 14 minutes (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 14 minutes (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up About a minute (healthy)

- [auto] 发现: docker.container.letta-chromadb = 127.0.0.1:18000->8000/tcp | 状态: Up 15 minutes (healthy)

- [auto] 发现: docker.container.29cb7402b164_twenty-db-1 = 5432/tcp | 状态: Up 15 minutes (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 15 minutes (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 15 minutes (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 15 minutes (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 15 minutes (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 35 minutes (healthy)

- [auto] 发现: docker.container.letta-chromadb = 127.0.0.1:18000->8000/tcp | 状态: Up About an hour (healthy)

- [auto] 发现: docker.container.29cb7402b164_twenty-db-1 = 5432/tcp | 状态: Up About an hour (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up About an hour (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up About an hour (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up About an hour (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up About an hour (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up About an hour (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 9 minutes (healthy)

- [auto] 发现: docker.container.letta-chromadb = 127.0.0.1:18000->8000/tcp | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.29cb7402b164_twenty-db-1 = 5432/tcp | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up About an hour (healthy)

- [auto] 发现: docker.container.letta-chromadb = 127.0.0.1:18000->8000/tcp | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.29cb7402b164_twenty-db-1 = 5432/tcp | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 3 hours (healthy)

- [auto] 发现: docker.container.litellm-litellm =  | 状态: Up 2 hours (healthy)

- [auto] 发现: docker.container.letta-chromadb = 127.0.0.1:18000->8000/tcp | 状态: Up 4 hours (healthy)

- [auto] 发现: docker.container.29cb7402b164_twenty-db-1 = 5432/tcp | 状态: Up 4 hours (healthy)

- [auto] 发现: docker.container.twenty-redis-1 = 6379/tcp | 状态: Up 4 hours (healthy)

- [auto] 发现: docker.container.langfuse-db = 5432/tcp | 状态: Up 4 hours (healthy)

- [auto] 发现: docker.container.litellm-redis = 127.0.0.1:6379->6379/tcp | 状态: Up 4 hours (healthy)

- [auto] 发现: docker.container.letta = 4317-4318/tcp, 5432/tcp, 6379/tcp, 0.0.0.0:8283->8283/tcp, [::]:8283->8283/tcp | 状态: Up 4 hours (healthy)

- [auto] 发现: docker.container.letta-db = 5432/tcp | 状态: Up 4 hours (healthy)
