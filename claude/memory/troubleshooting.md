# 排障手册（2026-05-18 精简）

## LiteLLM 4000
- `/health` 返回 401 = 未传 api_key，服务本身正常
- `drop_params: false` → GLM 报 UnsupportedParamsError(thinking)，改为 true
- Docker `--port` 参数在 v1.77.7 被忽略，用 `PORT` 环境变量
- `strip_tools_proxy.py` 剥离非 function 类型的 tools（GLM 不支持 web_search type）

## Letta 8283
- MCP 调用超时 → 307 重定向，API 路径必须带尾部斜杠 `/v1/agents/`
- Docker 容器全消失 → GPU 崩溃后 containerd overlay 损坏，全量清理重建
- 宿主 systemd service 与 Docker 容器端口冲突 → 禁用宿主服务

## mihomo 7890
- Claude 403 → GLOBAL 被设 DIRECT，切回 `⚡ 自动选择`
- 全节点失效 → 更新订阅
- GLOBAL 反复变 DIRECT → 配置缺少 GLOBAL proxy-group，手动添加
- 自动选择选出的节点可能不通 CF → 检查 health check URL

## Hyprland
- 启动黑屏 → 检查 egl-wayland + nomodeset
- 崩溃 → explicit_sync 在 0.54+ 已废弃，删除配置
- 与 KDE 冲突 → 不同时启用

## Docker
- 16 容器同时启动资源争抢 → docker-ordered-start.sh 分层启动
- GPU 崩溃后容器损坏 → `sudo rm -rf docker/containerd docker/rootfs docker/containers docker/network`

## systemd
- oneshot timer 服务显示 failed → 检查 Result=success（正常退出）
- krdpserver SIGABRT 循环 → disable，用 wayvnc
- auto-fix-services 误杀 oneshot → SKIP_PATTERNS 加服务名
- 脚本无 `~/.local/bin` → 开头 export PATH
