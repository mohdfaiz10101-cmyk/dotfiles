# Runbook: TermHive

## Desired State

- `termhive-daemon.service` is enabled and active on `127.0.0.1:3210`.
- `termhive-web.service` is enabled and active on `127.0.0.1:3200`.
- HTTP APIs and WebSocket both require authentication.
- Browser users authenticate through the TermHive login page and receive an
  HttpOnly session cookie; Basic Auth remains available for scripts.
- `~/.config/termhive/server.env` is mode `0600`.
- Public router port `18081` remains disabled.
- Phone access uses `https://fedora-termhive.tail60cff7.ts.net/`.
- Tailscale Serve proxies HTTPS `443` to `http://127.0.0.1:3200`.

## Verify

```bash
systemctl --user is-active termhive-daemon.service termhive-web.service
source ~/.config/termhive/server.env
curl --noproxy '*' -u "$AGENT_ORG_AUTH" http://127.0.0.1:3200/api/daemon/status
curl --noproxy '*' -u "$AGENT_ORG_AUTH" http://192.168.123.71:18081/
```

Retrieve the current username/password locally:

```bash
sed -n 's/^AGENT_ORG_AUTH=//p' ~/.config/termhive/server.env
```

## Build and Restart

```bash
cd ~/termhive
npm run build
systemctl --user restart termhive-web.service
```

Restart `termhive-daemon.service` only when daemon/runtime code changes.
Restarting the web service alone preserves running agent processes.

## Tailscale HTTPS

Current node must first be authenticated:

```bash
sudo tailscale up --hostname=fedora-termhive
sudo tailscale serve --bg http://127.0.0.1:3200
tailscale serve status
```

Install Tailscale on the phone, sign into the same Tailnet, then open the HTTPS
URL reported by `tailscale serve status`.

## Safety

- Do not forward port `3200` directly through the router.
- Do not enable public `18081` while it is plain HTTP.
- Keep Basic Auth enabled even behind Tailscale.
