# Runbook: Huly

Huly is the all-in-one workspace for projects, tasks, documents, chat, and collaboration.

## Desired State

- Service: `huly.service`
- Compose directory: `/var/home/charlie/apps/huly-selfhost`
- Compose file: `/var/home/charlie/apps/huly-selfhost/compose.yml`
- Environment: `/var/home/charlie/apps/huly-selfhost/huly_v7.conf`
- URL: `http://100.120.189.27:8087/`
- Hub entry: `http://127.0.0.1:9800/go/huly`
- Hub health: `http://127.0.0.1:9800/api/huly/status`

## Verify

```bash
systemctl --user is-active huly.service
curl -sS -I http://127.0.0.1:8087/
docker ps --format 'table {{.Names}}\t{{.Status}}' | rg 'huly_v7|NAMES'
```

## Restart

```bash
systemctl --user restart huly.service
```

## Notes

- Generated with upstream `setup.sh`, host address `100.120.189.27:8087`, non-SSL.
- Huly is resource-heavy; expect Elasticsearch and Redpanda to show `starting` for a while after restart.
- Docker Hub access can fail with EOF/rate-limit. Huly images are pulled through `docker.1ms.run`; DaoCloud mirror rejected `hardcoreeng/*` as not allowlisted.
- The nginx config bind mount needs `:Z` under rootless Podman/Silverblue, otherwise nginx cannot read `/etc/nginx/conf.d/default.conf`.
- Redpanda healthcheck should use plain `rpk cluster info`; adding the generated superuser/pass flags caused `ILLEGAL_SASL_STATE` even though the broker and topics were healthy.
- If registration hangs on "connecting to server" and nginx logs show `POST /_accounts` timing out with 504, check `docker logs huly_v7-account-1`. On first deploy, `account_db_v13_update_workspace_fk_to_person` created `workspace_created_by_person_fk` but left `global_account._account_applied_migrations.applied_at` NULL. Marking that migration applied and restarting Huly fixed the loop:
  `UPDATE global_account._account_applied_migrations SET applied_at = now(), last_processed_at = now() WHERE identifier = 'account_db_v13_update_workspace_fk_to_person' AND applied_at IS NULL;`
