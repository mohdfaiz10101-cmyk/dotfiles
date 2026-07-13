# Runbook: Plane

Plane self-hosted project management. It is the project-progress source of truth; Hub, Zulip, OpenCode, and FastGPT should sync around it.

## Desired State

- Service: `plane.service`
- Compose directory: `/var/home/charlie/apps/plane-selfhost`
- Compose file: `/var/home/charlie/apps/plane-selfhost/plane-app/docker-compose.yaml`
- Environment: `/var/home/charlie/apps/plane-selfhost/plane-app/plane.env`
- Mobile web/HTTPS URL: `https://fedora-termhive.tail60cff7.ts.net/`
- Setup/Admin fallback URL: `http://100.120.189.27:8090/god-mode/`
- Local URL: `http://127.0.0.1:8090/god-mode/`
- Hub entry: `http://127.0.0.1:9800/go/plane`
- Hub health: `http://127.0.0.1:9800/api/plane/status`

## Verify

```bash
systemctl --user is-active plane.service
curl -k -sS https://fedora-termhive.tail60cff7.ts.net/api/instances/ | jq '{self_managed: .config.is_self_managed, setup_done: .instance.is_setup_done}'
curl -sS -o /dev/null -w 'plane=%{http_code}\n' http://127.0.0.1:8090/god-mode/
curl -sS http://127.0.0.1:9800/api/plane/status | jq
docker ps --format 'table {{.Names}}\t{{.Status}}' | rg 'plane-app|NAMES'
```

## Restart

```bash
systemctl --user restart plane.service
```

## Notes

- The official `setup.sh start` health wait can return failure under Podman even when containers are usable, so `plane.service` runs `docker compose up -d` directly.
- First install required explicit `docker.io/makeplane` image names because Podman short-name resolution cannot prompt without a TTY.
- Do not delete Plane compose volumes after first user/workspace setup unless a full reset is explicitly requested.
- After first login, generate a Plane API token before implementing Hub task creation and status sync.
- For first setup, open `/god-mode/` with the trailing slash. Plane v1.3.x can show a blank SPA shell on `/god-mode` without the trailing slash.
- Plane Community Edition v1.3.1 works through mobile browser/PWA at `https://fedora-termhive.tail60cff7.ts.net/`.
- The official Plane mobile app is not usable with Community Edition self-hosting. It can accept the URL, then fail on missing mobile auth routes such as `/auth/m/` with 404/detail-not-found. Plane documents mobile app login for self-hosted instances as requiring Commercial Edition v1.5.0 or newer.
- Plain `http://IP:8090` can be rejected as an invalid self-host address by the app, but switching to HTTPS does not unlock mobile app auth on CE.
- Tailscale Serve maps HTTPS root to Plane and keeps Hub available at `https://fedora-termhive.tail60cff7.ts.net/hub`.
