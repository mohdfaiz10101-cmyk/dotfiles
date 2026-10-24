# Firefox 重复 Hermes 标签（2026-10-24）

- 证据：Firefox previous.jsonlz4 共289标签，其中284指向同一个 localhost:8648/session/...。
- 根因：旧 hermes-studio-8648.service 启动 CLI 未传 --no-open，execSync(xdg-open) 会阻塞到浏览器退出；Type=forking 启动超时或重启会再开标签，并可能杀死同 cgroup 的 Firefox。
- 当前拓扑：系统 FRPS 占8648；frpc fedora-hermes-groupchat-8648 -> 127.0.0.1:8787。旧 Studio 直接绑定8648报 EADDRINUSE。
- 修复：disable --now hermes-studio-8648.service；保留10-no-browser.conf强制 --no-open 防回退。hermes-port-lock.sh 按HTTP验证FRP入口，hermes-stability-check.sh 不再拉起旧Studio，入口故障修复frpc。
- Firefox 独立由 firefox.service 托管；不要在后台服务内打开浏览器。未修改或删除用户的浏览器会话文件。
- 验证：两个巡检 Result=success；8648及19976 HTTP200；旧Studio inactive、NRestarts=0；Firefox窗口可见且标签数稳定。
