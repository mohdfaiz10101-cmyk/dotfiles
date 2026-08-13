# Android Root Overlay

Apply these platform fields to the generated profile:

```yaml
redir-port: 7892
external-controller: 127.0.0.1:9000
```

The Magisk service owns iptables redirection. It must bypass NetBird UID
`10573`, root UID `0`, loopback, private LAN ranges and the mesh range. Do not
start Clash Meta's VPN service while NetBird is connected.

To bypass another Android app, obtain its UID with:

```bash
adb shell 'cmd package list packages -U | grep <package-name>'
```

Then add an `iptables -m owner --uid-owner <UID> -j RETURN` rule before the
final TCP redirect in `/data/adb/service.d/97-mihomo.sh`.
