# Runbook: FRP Tunnel

FRP 客户端，连接本地 frps，暴露内网服务。

## Desired State

- `frps.service`（system level）— 本地 FRP 服务端
- `frpc.service`（user level）— FRP 客户端，配置 `~/.config/frpc/frpc.toml`
- `frpc` 连接 `frps` 后建立代理隧道（如 `fedora-console-18080`）

## Verify

```bash
systemctl --user is-active frpc
# frps 状态
curl -s 'http://admin:frp%40charlie2026@127.0.0.1:7500/api/proxy/tcp' | jq
```

### Phone FRPC Checks

When phone FRPC reports `EOF`, `session shutdown`, or `i/o timeout`, classify
the failure before changing FRPS:

```bash
# Fedora: manual frpc tests must not inherit proxy vars.
env | rg -i '^(http|https|all|no)_proxy='
env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u all_proxy \
  ~/.local/bin/frpc -c /path/to/test-frpc.toml

# FRPS and dashboard should be same-version with client.
/usr/local/bin/frps --version
~/.local/bin/frpc --version
systemctl is-active frps.service

# Phone: check DNS fake-ip, route, VPN UID, and runtime config.
adb shell 'su -c "nslookup charlie1990.duckdns.org 2>/dev/null || ping -c 1 charlie1990.duckdns.org"'
adb shell 'su -c "ip route show table all | head -120; ip rule show"'
adb shell 'su -c "ps -A -o PID,PPID,ARGS | grep -E '\''frpc_smart|frpc|toybox timeout'\'' || true"'
adb shell 'su -c "tail -80 /data/local/tmp/frpc.log; tail -40 /data/local/tmp/frpc_smart.log"'
adb shell 'su -c "grep -E '\''serverAddr|serverPort|loginFailExit'\'' /data/local/tmp/frpc.runtime.toml"'
```

Known 2026-07-08 phone state:

- `charlie1990.duckdns.org` resolved on phone to fake-ip `198.18.0.29`.
- Phone `wlan0` was down; active Internet was cellular `rmnet_data2` with CGNAT
  IPv4 `10.53.246.204`.
- Phone could ping public DNS, but could not reach home public `125.110.213.91:2228`.
- Tailscale VPN was online, but only selected app UIDs were routed; shell/root
  FRPC did not get `100.120.189.27:7000`.
- AidLux is `com.aidlux` UID `10510`, but it was not included in the Tailscale
  Android VPN UID list. Haven is `sh.haven.app` UID `10371` and was included.
  Running FRPC as UID `10371` fixed the tunnel.
- Router persistent DNAT exists: public `2228/TCP -> 192.168.123.71:7000`.
- `frps` and `frpc` are both `0.69.0`; old FRPS backup is
  `/usr/local/bin/frps.0.63.0.bak`.

Working 2026-07-08 phone FRPC state:

- `/data/adb/service.d/frpc.sh` starts
  `su 10371 -c "/system/bin/sh /data/local/tmp/frpc_smart.sh ..."` so FRPC uses
  the Haven/Tailscale UID.
- `/data/local/tmp/frpc.toml` exposes:
  - `phone-adb`: local `127.0.0.1:5555` -> remote `15555`
  - `phone-ssh`: AidLux SSH local `127.0.0.1:8022` -> remote `8022`
  - `phone-haven-mcp`: local `127.0.0.1:8730` -> remote `18700`
- Verify ADB over FRP:

```bash
adb connect 127.0.0.1:15555
adb devices
```

## Restart

```bash
# 客户端
systemctl --user restart frpc

# 服务端（需 sudo）
sudo systemctl restart frps
```

## Known Issues

- FRP 代理注册成功不保证 Windows 本地转发正常
- `frpc.toml` 中 `fedora-console-18080` 必须指向本地 ttyd `127.0.0.1:8080`，不是 `19092`（桌面 PiP）
- 优先用 Tailscale 直连绕过 FRP
