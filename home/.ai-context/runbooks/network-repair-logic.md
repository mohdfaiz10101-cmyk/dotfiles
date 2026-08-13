# Runbook: Network Repair Logic

Fast path for Charlie-owned local/LAN/DuckDNS service failures. Use this before
broad searches or browser automation.

## First Classify The Path

For every URL, identify the actual client path first:

- Local Fedora: `127.0.0.1:<port>` or `localhost:<port>`.
- LAN phone: `192.168.123.71:<port>`.
- NetBird phone: current Fedora NetBird IP plus `<port>`.
- DuckDNS/public: `charlie1990.duckdns.org:<port>` through router DNAT, FRP,
  or local public proxy.
- USB reverse: phone `127.0.0.1:<external-port>` forwarded to Fedora.

Do not declare a phone-facing fix from Fedora curl alone. Verify with the path
the phone actually uses when the failure is mobile-facing.

## Common Decision Tree

1. Read `SYSTEM_MAP.md`, `FAILURE_BLACKLIST.md`, this runbook, and the service
   runbook.
2. Confirm the owner of the port with `ss -ltnp` and service/container status.
3. Probe the nearest backend first, then each public hop outward.
4. If local backend is healthy but DuckDNS fails, check router DNAT/firewalld,
   `frps.service`, `frpc.service`, and the specific FRP proxy name.
5. If LAN/phone fails while local succeeds, check phone route, VPN/proxy/Mihomo,
   and stale Fedora NAT rules before changing the application.
6. Record the root cause in the service runbook and memory after verification.

## Port-Specific Rules

### Hermes `8787` / DuckDNS `19976`

Expected path:

`DuckDNS -> router DNAT 19976 -> Fedora FRPS/frpc fedora-hermes-webui-19976 -> local auth proxy 127.0.0.1:18999 -> Hermes 127.0.0.1:8787`

Checks:

- `8787` healthy but `19976` dead: inspect `frps.service`, `frpc.service`, and
  `~/.config/frpc/frpc.toml` for `fedora-hermes-webui-19976`.
- `19976` opens but session fails: compare Hermes profiles. The BasicAuth user
  `charlie` must map to Hermes profile `default` in
  `~/.local/bin/hermes-8787-basic-auth-proxy.py`, matching local `8787`.
- `8787` and `8648` can run concurrently because they use separate profiles and
  service state. Do not collapse them into one shared profile when fixing
  session-load issues.

### Codex WebTTY `19899`

Expected path:

`router DNAT 19899 -> Fedora codex-public-19899-proxy.socket on 0.0.0.0:19899 -> systemd-socket-proxyd 127.0.0.1:19000`

Current rule:

- Do not restore a same-host FRPS loop for `19899` unless this runbook is
  deliberately changed.
- `19000-19007` are loopback-only gates; phones must use external
  `19899/19900/19902/19903/19904/19905/19906/19907` or USB reverse to those
  same external ports.
- A `401 Device Match` response can be the expected gate, not a backend outage.

Known stale NAT failure:

- Fedora nft rules once hijacked `19899/19900-19910` to `192.168.123.136`.
  Check stale handles in:
  - `ip nat PREROUTING`
  - `ip nat POSTROUTING`
  - `ip filter FORWARD`
- Remove only verified stale rules after confirming current intended listener
  and phone-visible path.

### OpenHands `3001` / public `19901`

On this host `127.0.0.1:3001` is OpenHands, not Open WebUI.

Expected path:

`OpenHands app container -> 127.0.0.1:3001`, public path
`DuckDNS 19901 -> openhands-public-proxy.service -> 127.0.0.1:3001`

If `/api/v1/app-conversations` returns 500:

- First check AI backends: `litellm.service`, `litellm-strip-proxy.service`,
  `letta-stack.service`, and `letta-podman-proxy.service`.
- Verify `http://127.0.0.1:4000/v1/models` and `http://127.0.0.1:8283`.
- Keep `SANDBOX_STARTUP_GRACE_SECONDS=60`.
- Keep OpenHands Letta MCP `LETTA_API=http://10.88.0.1:18283` for rootful
  sandboxes.
- Restart `openhands-gui.service` after changing `~/.config/openhands/openhands.env`
  or `~/.openhands/settings.json`.

### PKR110 Mihomo / Phone Control

- Do not judge phone reachability from Fedora alone. Use ADB-side probes when
  ADB is available.
- Old executable Mihomo backup scripts can duplicate root services. Backups
  under `/data/adb/service.d/97-mihomo.sh.*` should be non-executable.
- Desired root state is exactly one formal
  `sh /data/adb/service.d/97-mihomo.sh` and one
  `mihomo -d /data/adb/mihomo_netbird`.
- LAN bypass for `192.168.0.0/16` must remain in the MIHOMO chain so home LAN
  service probes are not intercepted.

## Memory Rule

After a verified network repair, update the smallest durable artifacts:

- This runbook or the service-specific runbook for topology/failure logic.
- `~/.claude/projects/-home-charlie/memory/router-infra.md` for router/DuckDNS
  evidence.
- Letta and memory-engine when they are healthy, using short factual entries.
