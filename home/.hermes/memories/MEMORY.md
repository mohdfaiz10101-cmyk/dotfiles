UPnP 绕过 frps allowPorts 暴露端口（无需sudo）：Fedora 服务对外暴露时，如果 frps allowPorts 不包含目标端口，可用 UPnP AddPortMapping 把 WAN:PORT → LAN_IP:PORT。Padavan 路由器 `192.168.123.1:3227` 支持 UPnP SOAP，脚本模板 `~/.local/bin/upnp-opencode-18910.py`。注意 urllib/curl 走 mihomo 时对 192.168.x 超时，须用裸 socket 或 `--noproxy '*'`。
§
路由器端口映射优先走 UPnP SOAP 直连，不要先想登录路由器 admin 后台。Padavan 固件内置 miniupnpd，用户态 SOAP 即可操作，无需 sudo/admin 密码。Control URL 是 `/ctl/IPConn`（注意大小写）。
§
手机 frpc 应优先用 Tailscale IP，不依赖局域网/WiFi。旧 NixOS IP 会导致 `i/o timeout`。手机 Haven MCP 通过本地 ADB 桥接，不是直接连 MCP。
§
Default model locked: step-router-v1 (stepfun)。Hermes Studio (8648/18648) API 需 auth，未认证返回 401。19976/8787/8648/18648 共享同一 config.yaml；改一处即改全部 surface。
§
NetBird 模式：Fedora 本机连自己 NetBird IP 可能超时（发夹式路由）；手机侧 curl/MCP 探测 Fedora NetBird IP 才可信。本机接口名 `wt0`；`wt0` 不存在不直接等于 NetBird 故障。
§
Deployment rule: 已有 skill 脚本时优先走 skill，不要绕过 `flexime-push.sh` / `install-to-phone.sh` 手跑 adb/pm install。
§
网络巡检 `network-workflow.py` 随服务迁移更新；retired service 的 unit/timer/script 一起清。手机远程不依赖单一 NetBird ADB；`100.87.37.3:8022` toybox nc 不稳定，长命令改走短 probe / 文件推送 / mihomo SOCKS5。Phone inventory 走 `/var/home/charlie/workspace/phone-inventory/` JSON/MD。
§
手机代理已升级为 Box for Root + nat REDIRECT workaround，legacy 97-mihomo.sh 禁用，NetBird tun0 共存已验证。
§
FRP: `frpc` 若有代理变量，即使 `no_proxy` 含 `127.0.0.1`，连 `frps:7000` 仍可能 EOF/session shutdown。排查顺序：`/proc/<pid>/environ` → `frpc.toml` 重复 `localPort` → `frps` 日志。`frpc.service` 建议 systemd override 清空代理变量。
§
冷记忆检索（本条不在上面即按需查）：分类库 `~/.hermes/memories/categories/*.md`[user-preference(9) ops(3) network(2) phone(2) router(2)]；语义检索 `~/.hermes/memories/vector_memory.db`；归档 `archive/<id>.json`；会话史用 session_search。
