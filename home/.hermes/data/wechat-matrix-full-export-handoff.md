# WeChat Matrix Full Export Handoff

Updated: 2026-08-16 23:40 CST

## Current decision

- Full WeChat history export is handled by the dedicated Matrix importer, not by Hermes full ingestion.
- Hermes should only process WeChat/Matrix content when explicitly mentioned, commanded, or selected by a future rules engine.
- Reason: Hermes gateway Matrix platform is currently retrying with `failed to reconnect`, and full chat ingestion caused noisy/incorrect behavior previously.

## Running export

- Service: `wechat-matrix-full-export.service`
- Wrapper: `/var/home/charlie/.local/bin/wechat-matrix-full-export-run`
- Unit: `/var/home/charlie/.config/systemd/user/wechat-matrix-full-export.service`
- Source DB: `/var/home/charlie/workspace/wechatbackup/EnMicroMsg.db`
- Matrix sender: `@wechat_import:100.120.189.27`
- Mode: one Matrix room per WeChat talker, WeChat-like message body, real Matrix media events when local media exists.

## State and logs

- State: `/var/home/charlie/.local/state/wechat-matrix-full-export/state.json`
- History: `/var/home/charlie/.local/state/wechat-matrix-full-export/history.jsonl`
- Stdout: `/var/home/charlie/.local/state/wechat-matrix-full-export/stdout.log`
- Talker room map: `/var/home/charlie/.local/state/wechat-matrix-full-export/rooms-by-talker.json`

## Commands

```bash
systemctl --user status wechat-matrix-full-export.service --no-pager -l
tail -80 /var/home/charlie/.local/state/wechat-matrix-full-export/history.jsonl
cat /var/home/charlie/.local/state/wechat-matrix-full-export/state.json
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('/var/home/charlie/.local/state/wechat-matrix-full-export/rooms-by-talker.json')
print(len(json.loads(p.read_text())) if p.exists() else 0)
PY
```

Pause/resume:

```bash
systemctl --user stop wechat-matrix-full-export.service
systemctl --user start wechat-matrix-full-export.service
```

## Verification baseline

- Media coverage audit: `/var/home/charlie/.local/state/wechat-matrix-backfill/media-coverage-audit.json`
- Local media indexed by importer: 45,943 files from `/tmp/wechat-matrix-sync/media` and `/var/home/charlie/workspace/wechatbackup/media`
- Sample validation room: `!BFHfoDPxQUplwUVRMH:100.120.189.27`
- Verified event types: `m.text`, `m.image`, `m.audio`, `m.video`, `m.file`

## Do not do

- Do not restart the old `wechat-matrix-sync.timer` for historical backfill.
- Do not send all WeChat messages through `@hermes:100.120.189.27`.
- Do not import history into one room.
- Do not add timestamps or conversation names to every message body.
- Do not replace media with text placeholders when local media is available.

## Ledger and knowledge management update

Updated: 2026-08-16 23:58 CST

- Ledger manager: `/var/home/charlie/.local/bin/wechat-matrix-ledger`
- Ledger DB: `/var/home/charlie/.local/state/wechat-matrix-ledger/ledger.db`
- Knowledge queue: `/var/home/charlie/.local/state/wechat-matrix-ledger/knowledge-queue.jsonl`
- Timer: `wechat-matrix-ledger-sync.timer`
- Matrix redactions and reply commands are synced into the ledger.
- Knowledge export excludes messages with Matrix deletion or source deletion markers.
- Do not directly edit the Android WeChat DB for delete sync.
- Use `reconcile-source --redact` only after verifying the source DB snapshot is fresh.

Commands:

```bash
/var/home/charlie/.local/bin/wechat-matrix-ledger status
/var/home/charlie/.local/bin/wechat-matrix-ledger matrix-sync
/var/home/charlie/.local/bin/wechat-matrix-ledger export-knowledge --limit 1000
```

## CRM and Hub command update

Updated: 2026-08-17 00:46 CST

Matrix assistant commands now include:

- `!建客户 名字｜公司` creates/updates a CRM contact in `/mnt/ai/apps/crm/crm.db`.
- `!建机会 标题` creates a CRM opportunity note with recent room context.
- `!建任务 标题` creates a Hub project task under `trade-crm`; if Hub is unavailable, queue to `/var/home/charlie/.local/state/wechat-matrix-ledger/crm-actions.jsonl`.
- Audit/queue: `/var/home/charlie/.local/state/wechat-matrix-ledger/crm-actions.jsonl`
- Verified Matrix command path with `!状态` on assistant room `!ZiiCTZiSnWwqdvAlXJ:100.120.189.27`.

## PKR SchildiChat Sync Repair

Updated: 2026-08-30 03:58 CST

- WeChat -> Matrix realtime import is healthy. Latest verified live state:
  `last_msg_id=206983`; timer/service completed successfully and later loaded
  zero new messages after that point.
- User-facing room-name rule is durable: no `微信｜` or `微信群｜` prefix should
  appear in Matrix room names or repeated message bodies.
- PKR SchildiChat package: `de.spiritcroc.riotx`, version `1.6.62.sc92`.
  Launch with:
  `adb shell am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -n de.spiritcroc.riotx/im.vector.application.features.Alias`.
- Root cause of "phone has no Matrix sync" was homeserver reachability:
  SchildiChat was still on old HTTPS routes (`100.120.189.27:443` /
  DuckDNS `:443`), while Synapse `user_ips` had no SchildiChat `/sync`.
- Durable Matrix client endpoint for SchildiChat is now:
  `https://charlie1990.duckdns.org`.
  Caddy on standard `443` proxies Matrix API to `127.0.0.1:8008` using the
  existing acme.sh certificate installed under `/etc/caddy/certs/`.
- Do not use `http://charlie1990.duckdns.org:19876` for SchildiChat login:
  phone curl can reach it, but SchildiChat rejects HTTP homeservers. Keep
  `:19876` as a low-level probe/fallback API, not the SchildiChat endpoint.
- Verification after repair:
  - phone curl to `https://charlie1990.duckdns.org/_matrix/client/versions`
    returned `200` and `ssl_verify_result=0`;
  - Synapse `user_ips` showed `SchildiChat/1.6.62.sc92` for
    `@charlie:100.120.189.27`;
  - SchildiChat was past the login screen, no Google password-save prompt was
    visible, and prefix count was zero.
- Operational caveats:
  - SchildiChat app data backup before re-login:
    `/sdcard/Download/schildichat-data-backup-20260830_032714.tar.gz`
    on the phone. Treat it as sensitive.
  - Local account password file:
    `/var/home/charlie/.local/state/matrix-local/charlie.password`; never print
    or paste it into logs.
  - ADBKeyBoard was used only to avoid Android IME corruption while entering
    URL/Matrix ID. Restore the user's normal IME afterward.
  - If future UI dumps include chat text or password prompts, immediately
    redact `~/.local/state/adb-ops/history.jsonl` and any backup copies.
