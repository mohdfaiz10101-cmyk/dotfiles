# Runbook: Mattermost

Mattermost is the channel collaboration layer for Hub, OP, FastGPT, and automation.

## Desired State

- Service: `mattermost.service`
- Compose directory: `/var/home/charlie/apps/mattermost-docker`
- Compose files: `docker-compose.yml` + `docker-compose.without-nginx.yml`
- Environment: `/var/home/charlie/apps/mattermost-docker/.env`
- URL: `http://100.120.189.27:8065/`
- Hub entry: `http://127.0.0.1:9800/go/mattermost`
- Hub health: `http://127.0.0.1:9800/api/mattermost/status`

## Verify

```bash
systemctl --user is-active mattermost.service
curl -sS http://127.0.0.1:8065/api/v4/system/ping | jq
docker ps --format 'table {{.Names}}\t{{.Status}}' | rg 'mattermost-docker|NAMES'
```

## Restart

```bash
systemctl --user restart mattermost.service
```

## Notes

- Uses Mattermost Team Edition `11.7.0`.
- The app runs without the bundled nginx; direct app port is `8065`.
- Mattermost app bind mounts need `:Z` under rootless Podman/Silverblue, otherwise `/mattermost/config/config.json` can fail with permission denied.
- The Docker Hub path can fail through the local proxy; `mattermost/mattermost-team-edition` was pulled through `docker.m.daocloud.io`.
