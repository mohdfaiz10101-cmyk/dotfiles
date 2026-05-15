
# 2026-05-14 Session Summary

## OpenAgents + Hermes 五层架构部署完成

### 当前状态
- ✅ Hermes Agent: systemd user service `hermes-agent.service` running (PID 3872479)
- ✅ OpenAgents Network: systemd user service `openagents.service` running (PID 37378, port 8700)
- ✅ OpenClaw Gateway: systemd user service `openclaw-gateway.service` running (port 18789)
- ✅ FRP Client: systemd user service `frpc.service` running (8 proxies online)
- ✅ OpenCode CLI: v1.14.50 at ~/.npm-global/bin/opencode

### OpenAgents 关键修复
1. **venv 依赖问题**：NixOS venv 隔离导致 pydantic/requests/grpcio 等包找不到
   - 解决：`pip install --target /mnt/ai/oa-venv/lib/python3.13/site-packages` 批量安装
2. **wrapper script 问题**：shebang `#!/mnt/ai/oa-venv/bin/python3` 需要显式 `sys.path.insert`
   - 解决：wrapper 已包含 `sys.path.insert(0, venv_sp)`
3. **gRPC 依赖 libstdc++.so.6**：pip 安装的 grpcio 需要系统 libstdc++
   - 解决：在 network.yaml 中移除 gRPC transport，仅保留 HTTP（port 8700）
   - systemd service 添加 `LD_LIBRARY_PATH=/nix/store/j2kgllgds4w7na8zqv1msi0mpvpjxda8-gcc-15.2.0-lib/lib`
4. **systemd user bus 间歇性断连**：非致命，进程实际运行正常

### OpenAgents 网络配置
- network.yaml: 4 agents (openclaw / stepclaw / opencode / hermes)
- HTTP 8700（MCP 33 tools），gRPC 8600 已禁用
- mode: centralized, topology: charlie-agent-network

### FRP 映射（当前）
- 2223 → SSH (22)
- 17699 → tty (7699)
- 60000-60002 → mosh
- 19890 → OpenCode Web (8080)
- 19891 → Hub API (9800)
- 19892 → Letta MCP (8284)
- **19893** → **OpenClaw Gateway (18789)**
- 18090 → OpenCode Sisy (8090)

### 待完成
- [ ] StepClaw 云端 WebSocket 配置（需用户在阶跃 AI App/网页版手动操作）
- [ ] OpenClaw → OpenCode coding-agent 端到端测试
- [ ] NixOS flake 模块化（可选，当前 user service 可工作）
- [ ] stepclaw-nixos-setup.md §6 FRP 表已更新，文档完整

### 关键文件
- `~/.openagents/network.yaml` — OpenAgents 4-agent 配置
- `~/.config/systemd/user/openagents.service` — OpenAgents systemd unit
- `~/.config/systemd/user/hermes-agent.service` — Hermes systemd unit
- `~/ai-config-sync/openclaw-config/stepclaw-nixos-setup.md` — 五层架构文档（355行）
- `/home/charlie/.local/bin/openagents` — wrapper script（含 sys.path fix）
