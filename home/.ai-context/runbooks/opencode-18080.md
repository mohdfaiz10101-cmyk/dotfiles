# Runbook: OpenCode/OpenClaw 18080

## Desired State
- `http://charlie1990.duckdns.org:18080/` returns ttyd HTML with HTTP 200.
- Router has persistent Padavan rule `18080|192.168.123.71|18080|TCP|OpenCode-18080`.
- `frps` listens on `*:18080`.
- `frpc` proxy `fedora-console-18080` is online.
- `fedora-console-18080` must forward to local ttyd `127.0.0.1:8080`;
  `127.0.0.1:19092` is desktop PiP and will return the wrong page.

## Fix Router Rule
```bash
/usr/bin/sshpass -p admin ssh -o StrictHostKeyChecking=no admin@192.168.123.1 '
/usr/sbin/nvram set vts_port_x23=18080
/usr/sbin/nvram set vts_ipaddr_x23=192.168.123.71
/usr/sbin/nvram set vts_lport_x23=18080
/usr/sbin/nvram set vts_proto_x23=TCP
/usr/sbin/nvram set vts_srcip_x23=
/usr/sbin/nvram set vts_desc_x23=OpenCode-18080
/usr/sbin/nvram set vts_num_x=24
/usr/sbin/nvram commit
/sbin/restart_firewall
'
```

## Verify
```bash
~/.local/bin/router-config-snapshot.sh
rg '^18080\|' ~/.local/state/router-port-forwards.cache
curl --noproxy '*' http://charlie1990.duckdns.org:18080/
```

## `oc` local entry

- `oc` connects directly to `http://127.0.0.1:4097`.
- It must start `opencode.service` and wait for `/session` before creating or
  attaching the `openclaw` tmux session.
- The attach loop should recover silently during a server restart; do not print
  `server not alive, waiting` into the visible TUI.
- `~/.local/share/opencode/openclaw-session` is the pinned active session.
  Background updates to another session must not kill or replace the current
  attach. Use `oc sync` to switch explicitly to the latest session, or
  `oc ses_...` to select a specific session.
- `oc restart [optional context]` must capture the pinned session and directory
  before restarting, then use `opencode run --attach --session --dir` to resume
  work in that same session. It must not create a replacement session.
- Do not restore the old `openclaw-skipped`/quick-exit rotation or a watcher
  that polls the latest session. Both cause intermittent attach churn.
- `ttyd-8080.service` wants and starts after `opencode.service`, but must not
  use `Requires=` because a manual OpenCode restart would otherwise stop ttyd.
- Keep ttyd on its native index with `rendererType=dom`. A custom index that
  sets `touch-action:none` or hides `.xterm-viewport` overflow breaks phone
  tapping, scrolling, soft-keyboard Enter, and interactive question selection.

## Automatic entry maintenance

- `opencode-entry-maintain.timer` runs every five minutes.
- It checks `opencode`, the 4096 Web proxy, and ttyd using local HTTP probes.
- It archives only empty/old sessions and caps visible root sessions at 30;
  the pinned session is always preserved and no session is permanently deleted.
- If the tmux screen shows an old selection prompt while the backend reports no
  pending question, it reconnects only the `opencode attach` child.
- Log: `~/.local/share/opencode/log/entry-maintain.log`.
