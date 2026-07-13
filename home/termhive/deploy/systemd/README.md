# TermHive systemd deployment

The production layout uses two user services:

- `termhive-daemon.service` owns agent processes and listens only on
  `127.0.0.1:3210`.
- `termhive-web.service` serves the UI/API/WebSocket on `127.0.0.1:3200`.

Install:

```bash
npm run build
mkdir -p ~/.config/systemd/user ~/.config/termhive
cp deploy/systemd/termhive-*.service ~/.config/systemd/user/
cp deploy/systemd/server.env.example ~/.config/termhive/server.env
chmod 600 ~/.config/termhive/server.env
systemctl --user daemon-reload
systemctl --user enable --now termhive-daemon.service termhive-web.service
```

Replace the example password before starting the web service. Users sign in
through TermHive's login screen; the resulting HttpOnly session cookie is used
by both REST and WebSocket connections.

## Recommended phone access: Tailscale HTTPS

Install and log into Tailscale on both the server and phone, then run on the
server:

```bash
sudo tailscale up --hostname=fedora-termhive
sudo tailscale serve --bg http://127.0.0.1:3200
tailscale serve status
```

Open the HTTPS URL reported by `tailscale serve status`. Tailscale encrypts the
transport; TermHive Basic Auth remains enabled as a second boundary.

Do not publish port 3200 directly to the internet. Basic Auth alone does not
encrypt credentials or terminal traffic.
