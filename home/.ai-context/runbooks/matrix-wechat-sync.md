# Runbook: Matrix WeChat Sync

Created: 2026-08-16

## Purpose

- Import Android WeChat message history into Matrix.
- Keep incremental sync running on a timer.
- Keep the live `matrix-wechat` bridge separate from the offline importer.

## Durable artifacts

- Import script: `~/.local/bin/wechat-matrix-sync-export`
- Media pull script: `~/.local/bin/wechat-matrix-media-pull`
- Timer/service:
  - `~/.config/systemd/user/wechat-matrix-sync.timer`
  - `~/.config/systemd/user/wechat-matrix-sync.service`
- State/log:
  - `~/.local/state/wechat-matrix-sync/state.json`
  - `~/.local/state/wechat-matrix-sync/history.jsonl`
- Matrix room currently used by the importer:
  - live rich room: `!gkLEhwUaLlMRAjQFKR:100.120.189.27`
  - old low-fidelity room: `!vDpPCOkEsJrrfrRrwh:100.120.189.27`
- Matrix sender account for WeChat import:
  - `@wechat_import:100.120.189.27`
- Public Matrix client API:
  - `http://charlie1990.duckdns.org:19876`
- LAN Matrix client API:
  - `http://192.168.123.71:19876`

Do not store Matrix tokens, appservice tokens, `listen_secret`, or WeChat DB
decrypt keys in this runbook.

## Import path

`wechat-matrix-sync-export --pull-phone` copies the encrypted Android WeChat DB
to `/sdcard/Download/EnMicroMsg.matrix-sync.db`, splits it on the phone into
8MB parts, pulls parts to `/tmp/wechat-matrix-sync/parts`, assembles
`/tmp/wechat-matrix-sync/EnMicroMsg.db`, verifies the assembled byte count, then
reads messages incrementally by `msgId`.

The script uses Matrix transaction IDs based on `msgId`, so retries are
idempotent at the Matrix send API level.

The live timer must use the dedicated Matrix sender account
`@wechat_import:100.120.189.27`, not `@hermes:100.120.189.27`. Hermes is only a
processing assistant and should handle WeChat content when explicitly mentioned,
commanded, or selected by a future rules engine. Do not route full realtime
WeChat ingestion through Hermes.

The live sync state is intentionally set to the current maximum `msgId` when
switching to realtime mode, so old historical group messages are not dumped into
the phone's conversation list. Backfill should be a separate manual/rate-limited
job in a separate room.

Rich formatting currently restores:

- contact display names from `rcontact`
- group names from `chatroom`
- group sender names from the `wxid:\nbody` content prefix
- app/share titles and descriptions from `AppMessage`
- image/video/voice/emoji placeholders from message media metadata

Actual image/video/voice file upload requires pulling WeChat media directories
from the phone (`image2`, `video`, `voice2`, emoji storage). The DB alone stores
references and metadata, not all binary media files.

## WeChat-like history import acceptance

Do not run broad historical import unless these checks pass first:

- Each WeChat `talker` maps to exactly one Matrix room. Do not import all chats
  into one room.
- Room name carries the conversation name. Message bodies must not repeat the
  group/conversation name or the timestamp; Matrix clients already render time.
- Group message bodies may show sender display name plus content. Private chat
  incoming messages should normally be content only; outgoing messages may show
  `我` only if the client UI cannot distinguish sender.
- Image/video/voice/file messages must be real Matrix media events
  (`m.image`, `m.video`, `m.audio`, `m.file`) uploaded to the Matrix media
  repository, not text placeholders.
- Media import must verify local availability before sending history:
  - WeChat DB rows: `message`, `ImgInfo2`, `videoinfo2`, `voiceinfo`,
    `AppMessage`
  - Media directories/files: `image2`, `video`, `voice2`, `Download`/files,
    emoji store, avatar/contact images when available
  - Optional file index DBs such as `WxFileIndex.db` when present
- Completeness audit must compare expected vs imported counts per talker and per
  type: text, image, video, voice, file/app, emoji, system messages.
- If media roots are empty, stop after dry-run/audit. Do not send DB-only
  historical rooms to the user's phone.

When the phone ADB/root path is back online, pull media first:

```bash
~/.local/bin/phone-frp-fallback-status
~/.local/bin/wechat-matrix-media-pull --list-only
~/.local/bin/wechat-matrix-media-pull --dirs image2 video voice2 emoji attachment download
```

The media pull script writes under
`/var/home/charlie/workspace/wechatbackup/media` and logs to
`~/.local/state/wechat-matrix-backfill/media-pull-history.jsonl`. It uses
Magisk/root `su -c`, creates tar archives on the phone, splits them into parts,
pulls parts with `adb-record`, and extracts locally. Do not run historical
Matrix import until the preflight audit reports nonzero local media files and
acceptable per-type coverage.

Media pull robustness learned on 2026-08-16:

- Large `video` pulls can leave ADB `offline` repeatedly. Resume by reconnecting
  `127.0.0.1:15555` and `100.87.37.3:5555`; do not assume either path is
  permanently healthier.
- Never mix local split parts from different remote tar generations. The media
  pull script now stores a per-directory part manifest and clears local parts
  when the remote manifest changes.
- If a complete remote tar/parts set already exists and its part byte sum equals
  the tar size, reuse it instead of rebuilding the tar. Rebuilding multi-GB tar
  archives over unstable ADB is less reliable than resuming existing parts.
- Keep skip logs sparse; per-part success/retry and every 25th skip is enough.

Verified local media pull on 2026-08-16:

- `image2`: 17,462 files
- `voice2`: 6,515 files
- `emoji`: 3,954 files
- `attachment`: 503 files
- `video`: 2,764 files, archive
  `/var/home/charlie/workspace/wechatbackup/media/_archives/video.tar`

Current rich-media coverage audit:

- `message.type=3` images: 9,148 / 9,167 matched to local files
- `message.type=34` voice: 6,468 / 6,501 matched to local files
- `message.type=43` video: 1,704 / 1,715 matched to local files
- `AppMessage.type=6` files: 552 matched local attachment files from 1,368 file
  messages; the rest appear absent from pulled local attachment storage and
  should remain text fallback unless recovered from another source.
- Audit file:
  `~/.local/state/wechat-matrix-backfill/media-coverage-audit.json`

Importer fixes required for WeChat-like rendering:

- Join `voiceinfo` by `voiceinfo.MsgLocalId = message.msgId`; voice files are
  named like `msg_<FileName>.amr`, not just `message.imgPath`.
- Strip WeChat filename marker `⌖` when indexing and uploading media.
- For videos, prefer `<video_path>.mp4` before thumbnail/stem matches; otherwise
  Matrix may receive a video event pointing at a JPEG thumbnail.
- Use `AppMessage.type=6`, not only `message.type=49`, to detect file messages.
- In per-conversation rooms, keep group/conversation name out of message body;
  the room name already carries it. Do not include timestamps in message body.
- For WeChat group rooms, do not prefix the Matrix room name with `微信群｜`.
  Prefer the real WeChat room title from `rcontact.conRemark` /
  `rcontact.nickname`, then `chatroom.chatroomnick`, then `chatroom.displayname`
  only as a fallback. Private/direct chats may keep the `微信｜` prefix.

Sample validation room created on 2026-08-16:

- Room: `!BFHfoDPxQUplwUVRMH:100.120.189.27`
- Sent and API-verified sample Matrix `msgtype`s:
  `m.text`, `m.image`, `m.audio`, `m.video`, `m.file`
- Corrected video sample verified as `m.video` with MIME `video/mp4`.

Rejected attempts on 2026-08-16:

- Single-room historical backfill: rejected because it does not match WeChat's
  conversation list.
- Per-room v2/v3 backfill without media: rejected because images/videos/files
  were missing.
- Message body with repeated timestamp or group name: rejected because Matrix
  already shows time and the room name already identifies the conversation.

## Why split pull is required

The FRP ADB path `127.0.0.1:15555` can drop large `adb pull` transfers around
the 40% range for a 431MB DB and may temporarily show the device as `offline`.
Do not return to a single full-file `adb pull` for timer sync.

Required behavior:

- Use phone-side `split -b 8m`.
- Retry per part.
- Skip already complete local parts when resuming.
- Treat `offline` as transient and reconnect with bounded retries.

2026-08-29 realtime repair notes:

- Keep realtime and historical backfill state separate. Realtime uses
  `~/.local/state/wechat-matrix-sync/state.json`; historical backfill must use a
  separate state file such as `backfill-state.json`, otherwise a slow backfill
  can make phone-side realtime sync appear stuck.
- The live wrapper is `~/.local/bin/wechat-matrix-live-sync`. It uses `flock`
  and passes multiple ADB serial candidates:
  `127.0.0.1:15555,100.87.37.3:5555,charlie1990.duckdns.org:15555`.
- `wechat-matrix-sync-export` must clear local `/tmp/wechat-matrix-sync/parts`
  before assembling a new phone DB snapshot. Mixing old and new split parts can
  produce a SQLCipher database with malformed schema/rootpage errors.
- A clean realtime run on 2026-08-29 pulled 52 parts, loaded messages after
  `msgId=206690`, sent 226 Matrix events through `@wechat_import`, updated
  `state.json` to `last_msg_id=206916`, fixed 226 event timestamps, and found
  no missing ledger deletions.
- Existing Matrix room names are not changed by future room creation logic.
  Strip stale `微信｜` prefixes by sending `m.room.name` state events through the
  Matrix Client API. On 2026-08-29, 61 existing rooms were renamed and Synapse
  current state then reported zero prefixed room names.
- SchildiChat stores room/timeline cache in `disk_store.realm`. Removing it can
  temporarily make the app show an empty room list even when auth and crypto
  data remain. Prefer server-side room rename plus natural client sync; if
  cache surgery is attempted, back up and be ready to restore
  `disk_store.realm*`.
- PKR ADB can flip all transports to `offline` during UI/cache checks. Restart
  the local ADB server and reconnect `127.0.0.1:15555` and DuckDNS before
  drawing phone-side conclusions. Fedora/Synapse success alone does not prove
  the phone UI has refreshed.

2026-08-30 PKR SchildiChat sync repair notes:

- Realtime WeChat import was healthy: timer/service exited successfully, the
  live state was at `last_msg_id=206983`, and a later run loaded zero new
  messages after that point. If the phone does not show new data, first check
  the Matrix client route before changing the importer.
- SchildiChat package on PKR is `de.spiritcroc.riotx`, version
  `1.6.62.sc92`; launcher alias is
  `de.spiritcroc.riotx/im.vector.application.features.Alias`.
- Root cause was the client route, not the importer: Synapse `user_ips` had no
  SchildiChat `/sync` entry, while phone sockets showed SchildiChat trying old
  `100.120.189.27:443` / DuckDNS `:443` paths. The working HTTP Matrix entry
  was `http://charlie1990.duckdns.org:19876`, but SchildiChat rejected HTTP
  homeserver login.
- Durable fix for SchildiChat is HTTPS on standard DuckDNS `443`:
  - `/etc/caddy/Caddyfile.monitor` now serves `charlie1990.duckdns.org` with
    Matrix `/.well-known/matrix/*` and `/_matrix/*` reverse-proxied to
    `127.0.0.1:8008`.
  - Caddy loads the existing acme.sh certificate from
    `/etc/caddy/certs/charlie1990.duckdns.org.fullchain.cer` and
    `/etc/caddy/certs/charlie1990.duckdns.org.key`; do not rely on live
    HTTP/TLS ACME validation from this home WAN path.
  - Fedora firewalld must include service `https`.
  - Padavan persistent VTS must include `443 -> 192.168.123.71:443` and
    `80 -> 192.168.123.71:80`. `80` is useful for future ACME/debug even
    though the current cert is installed from acme.sh.
- Verification evidence after repair:
  - Phone curl to `https://charlie1990.duckdns.org/_matrix/client/versions`
    returned `200` with `ssl_verify_result=0`.
  - Synapse `user_ips` showed `@charlie:100.120.189.27` with user agent
    `SchildiChat/1.6.62.sc92` from the phone route.
  - SchildiChat was no longer on the login screen, no Google password prompt
    was visible, and UI prefix count was zero.
- For automated text entry on this Android 16 phone:
  - `adb shell input text` can be corrupted by IME/autocorrect for URLs and
    Matrix IDs.
  - Temporarily install/use ADBKeyBoard and `ADB_INPUT_B64` for URL/Matrix ID.
  - For passwords with special characters, either avoid UI automation or use a
    simple alphanumeric temporary password. Do not print passwords or dump
    password fields into ADB logs.
- SchildiChat data was backed up on the phone before clearing/re-login:
  `/sdcard/Download/schildichat-data-backup-20260830_032714.tar.gz`.
  This backup contains app auth/cache data and must be treated as sensitive.
- Local Matrix password file used for the old account is
  `~/.local/state/matrix-local/charlie.password`. Do not print it. Existing
  `charlie-android-login.password` returned 403 and should not be used.

## 2026-09-09 realtime rich-media enablement notes

- Root cause for live Matrix rooms showing text but not WeChat multimedia was
  the live wrapper `~/.local/bin/wechat-matrix-live-sync` passing
  `--no-media-upload` to `wechat-matrix-sync-export`.
- The live wrapper no longer passes `--no-media-upload`; when media roots are
  present, realtime import can upload WeChat image/video/voice/file messages as
  Matrix `m.image`, `m.video`, `m.audio`, and `m.file` events.
- `wechat-matrix-sync-export` now also tries WeChat `message.type=47` emoji
  media by `imgPath`/`reserved`/`content` candidates and sends matches as
  Matrix `m.image` for broad client compatibility. Treat this as image
  fallback, not native WeChat sticker protocol parity.
- The importer logs `media_index_loaded` with `roots_present`, plus
  `media_roots_missing` or `media_index_empty`, so missing media directories no
  longer silently degrade to text-only imports.
- Current default media roots are `/tmp/wechat-matrix-sync/media` and
  `/var/home/charlie/workspace/wechatbackup/media`. On 2026-09-09 both were
  absent, so old media must be restored or pulled again before multimedia can
  appear for newly imported rows.
- The live wrapper runs `phone-frp-fallback-status` before the expensive phone
  DB pull. If phone ADB is offline it writes an `adb_preflight_offline` event to
  `~/.local/state/wechat-matrix-sync/history.jsonl`, touches
  `~/.local/state/wechat-matrix-sync/skip-post`, and exits successfully.
- `wechat-matrix-sync.service` ExecStartPost commands are gated by `skip-post`
  so offline preflight skips timestamp repair and ledger reconciliation instead
  of reading a stale `/tmp/wechat-matrix-sync/EnMicroMsg.db`.
- Verification on 2026-09-09: `bash -n ~/.local/bin/wechat-matrix-live-sync`,
  `python3 -m py_compile ~/.local/bin/wechat-matrix-sync-export`, and
  `systemd-analyze --user verify ~/.config/systemd/user/wechat-matrix-sync.service`
  passed. Manual service start with phone offline ended `inactive (dead)` /
  success, while `wechat-matrix-sync.timer`, `matrix-synapse.service`, and
  `matrix-wechat.service` stayed active.
- Current phone blocker from `phone-frp-fallback-status`:
  `fallback_defined_but_phone_client_offline`; next recovery action is
  one-time USB ADB or phone root shell:
  `sh /data/adb/service.d/frpc.sh`.
- 2026-09-09 login account reset: use Matrix localpart `charlie`
  (`@charlie:100.120.189.27`) for client login. The password is stored only in
  `~/.local/state/matrix-local/charlie.password`; do not copy it into runbooks,
  logs, or final answers. Reset was verified through
  `/_matrix/client/v3/login` with `access_token_present=True`.

## Commands

```bash
systemctl --user status wechat-matrix-sync.timer wechat-matrix-sync.service --no-pager -l
tail -80 ~/.local/state/wechat-matrix-sync/history.jsonl
cat ~/.local/state/wechat-matrix-sync/state.json
python3 -m py_compile ~/.local/bin/wechat-matrix-sync-export
~/.local/bin/phone-frp-fallback-status
```

Manual one-shot verification:

```bash
systemctl --user reset-failed wechat-matrix-sync.service
systemctl --user start wechat-matrix-sync.service
```

## Full historical export service

For user-requested full WeChat history export, use the bounded, resumable
per-conversation service. It runs the rich importer in batches and continues
until no new rows remain.

- Service: `wechat-matrix-full-export.service`
- Wrapper: `~/.local/bin/wechat-matrix-full-export-run`
- Unit: `~/.config/systemd/user/wechat-matrix-full-export.service`
- State directory: `~/.local/state/wechat-matrix-full-export`
- State file: `~/.local/state/wechat-matrix-full-export/state.json`
- Log file: `~/.local/state/wechat-matrix-full-export/history.jsonl`
- Room map: `~/.local/state/wechat-matrix-full-export/rooms-by-talker.json`
- Hermes handoff: `~/.hermes/data/wechat-matrix-full-export-handoff.md`

Operational commands:

```bash
systemctl --user status wechat-matrix-full-export.service --no-pager -l
tail -80 ~/.local/state/wechat-matrix-full-export/history.jsonl
cat ~/.local/state/wechat-matrix-full-export/state.json
systemctl --user stop wechat-matrix-full-export.service
systemctl --user start wechat-matrix-full-export.service
```

Do not route the full historical stream through Hermes. Hermes Matrix gateway
state can be disconnected/retrying, and Hermes should only process WeChat
content on explicit mention/command or a future allowlisted rule engine.

Hermes-facing operations are wrapped by:

```bash
~/.local/bin/wechat-matrix-hermes-ops status
~/.local/bin/wechat-matrix-hermes-ops summary
~/.local/bin/wechat-matrix-hermes-ops smoke
~/.local/bin/wechat-matrix-hermes-ops export-knowledge 1000
~/.local/bin/wechat-matrix-hermes-ops ntfy-summary
```

This wrapper is the default entrypoint for future Hermes/Codex agents before
they inspect individual scripts. It summarizes canonical rooms, services,
ledger paths, knowledge queue paths, ntfy routing, and accepted Matrix commands.

## Matrix deletion, archive, and knowledge ledger

Matrix deletion is redaction, not WeChat-style destructive cross-device delete.
For WeChat imports, keep a local ledger between WeChat `msgId` and Matrix
`event_id` so later Matrix redactions, source-side deletion checks, and
knowledge-base export can be reconciled safely.

- Ledger manager: `~/.local/bin/wechat-matrix-ledger`
- Ledger DB: `~/.local/state/wechat-matrix-ledger/ledger.db`
- Knowledge queue: `~/.local/state/wechat-matrix-ledger/knowledge-queue.jsonl`
- Sync service: `~/.config/systemd/user/wechat-matrix-ledger-sync.service`
- Sync timer: `~/.config/systemd/user/wechat-matrix-ledger-sync.timer`
- Importer ledger flag: `--ledger-path`

Operational commands:

```bash
~/.local/bin/wechat-matrix-ledger status
~/.local/bin/wechat-matrix-ledger matrix-sync
~/.local/bin/wechat-matrix-ledger export-knowledge --limit 1000
~/.local/bin/wechat-matrix-ledger reconcile-source
```

Use `reconcile-source --redact` only when the source DB snapshot is known fresh.
For the Android source DB, a fresh snapshot means the main `EnMicroMsg.db` and
any matching `EnMicroMsg.db-wal` / `EnMicroMsg.db-shm` sidecars were copied
together, or WeChat was force-stopped first so SQLite checkpointed cleanly.
Do not directly mutate the WeChat Android database for delete sync. Mark
Matrix-deleted or WeChat-missing messages as `knowledge_state='excluded'` so
FastGPT/Hermes memory imports skip them.

If Synapse is rebuilt with a clean homeserver DB, do not reuse old room ids or
old Matrix event ids from `rooms-by-talker.json` / `ledger.db`; back them up,
reset the active room map and ledger, reimport by `talker`, then run
`wechat-matrix-room-reconcile` and `wechat-matrix-fix-event-timestamps`.

Supported Matrix management commands on replies:

- `!归档` / `!archive` marks the replied imported message as archived.
- `!记忆` / `!remember` marks the replied imported message for memory export.
- `!忽略` / `!ignore` excludes the replied imported message from knowledge export.

Batch/message processing commands:

- Assistant room: `微信整理助手｜Hermes命令入口`
- Assistant room ID: `!ZiiCTZiSnWwqdvAlXJ:100.120.189.27`
- In any WeChat-imported room, send `!总结 最近50` to summarize the latest
  50 imported messages in that room.
- Send `!状态` to show ledger counts.
- Send `!记忆最近20` to mark the latest 20 imported messages in that room for
  memory export.
- Send `!建客户 名字｜公司` to create or update a CRM contact in
  `/mnt/ai/apps/crm/crm.db`.
- Send `!建机会 标题` to create an opportunity note in the CRM notes table with
  recent room context.
- Send `!建任务 标题` to create a Hub project task under project `trade-crm`.
  If Hub is unavailable, the payload is appended to
  `~/.local/state/wechat-matrix-ledger/crm-actions.jsonl`.
- CRM command audit queue:
  `~/.local/state/wechat-matrix-ledger/crm-actions.jsonl`

Element X / mobile client caveat:

- Matrix clients usually expose deletion as `Remove message` / redaction, not
  as WeChat-style delete.
- Imported messages are sent by `@wechat_import:100.120.189.27`; a viewer such
  as `@matrixcharlie:100.120.189.27` may not see a delete option unless room
  power levels allow redacting other users' messages.
- `wechat-matrix-ledger set-power-levels` grants `@matrixcharlie` high power in
  rooms where `@wechat_import` can still edit power levels. Some older rooms may
  fail with `403` and need admin/manual repair or command-based redaction.
- Matrix mobile clients do not provide a reliable cross-client multi-select API
  for sending arbitrary selected messages to a bot. Use range commands such as
  `!总结 最近50` instead of manual multi-select.

## Expected evidence

- Timer is `active (waiting)` and enabled.
- Service exits with `status=0/SUCCESS`.
- Log includes:
  - `pull_done` with `parts: 52` for a ~431MB DB snapshot.
  - `batch_loaded` with `dry_run: false`.
  - `batch_done` with `sent` greater than zero.
- State file advances `last_msg_id`.

Verified on 2026-08-16:

- Phone DB assembled to `431533056` bytes from 52 parts.
- Matrix batch sent 50 messages.
- State advanced from `last_msg_id=10` to `last_msg_id=60`.
- Next timer trigger was scheduled after successful service completion.
- Public client entry `19876 -> 192.168.123.71 -> 127.0.0.1:8008` is the
  working path. `19876/tcp` is already open in Fedora firewalld; router
  `vserver` runtime NAT is inserted before the DMZ catch-all. Router persistent
  script write failed once with `No space left on device`, so re-check
  persistence after router storage cleanup/reboot.
- Public login user `@matrixcharlie:100.120.189.27` was created and joined to
  the WeChat sync room. The 12-digit login code is stored locally at
  `~/.local/state/matrix-public-login-code.txt`.
- After user feedback, low-fidelity text-only timer was stopped. Rich realtime
  room `!gkLEhwUaLlMRAjQFKR:100.120.189.27` was created, `@matrixcharlie` was
  joined, a visible notice was posted, sender was changed to
  `@wechat_import:100.120.189.27`, and live state was moved to current max
  `msgId` so only new messages sync from now. Do not restart the timer until
  `~/.local/bin/phone-frp-fallback-status` reports a reachable ADB path.

## Live bridge and 12-digit activation

The offline importer does not need the 12-digit WeChat activation code.

The live `matrix-wechat` bridge still requires a connected
`matrix-wechat-agent` on `bridge.listen_address` before `login` can complete.
If logs show `no agent connection avaiable`, fix the agent connection first.

Avoid running duplicate bridge services:

- Keep `matrix-wechat.service` for the actual appservice bridge.
- Keep `wechat-matrix-bridge.service` disabled unless it is explicitly
  reconfigured with required Matrix credentials and a non-conflicting purpose.

Verified on 2026-09-10:

- PKR phone ADB was reachable through FRP fallback: `127.0.0.1:15555` and
  `100.87.37.3:5555` both reported `device`; LAN `192.168.123.22:5555` was not
  reachable and was not required for this workflow.
- `wechat-matrix-live-sync` now leaves Matrix media upload enabled, preflights
  phone ADB with `phone-frp-fallback-status`, and skips post-processing when
  phone ADB is offline instead of reusing stale `/tmp/wechat-matrix-sync` DBs.
- `wechat-matrix-sync-export` now indexes existing media roots and attempts
  WeChat `message.type=47` emoji/sticker media matching from `imgPath`,
  `reserved`, and `content`.
- `wechat-matrix-media-pull` needed the root shell invocation fixed: pass
  Android `su 0 -c` as one shell string with `shlex.quote(...)`; split argv
  broke multi-line commands on device.
- Pulled local media roots under
  `/var/home/charlie/workspace/wechatbackup/media`: `voice2` 6515 files,
  `emoji` 3954 files, `attachment` 503 files, `image2` 17462 files, and
  `video` 2764 files. `download` was missing on the phone snapshot.
- Video pull used 279 remote split parts and recovered from repeated ADB
  `device offline`, `connect failed: closed`, and partial pull failures via
  per-part retries.
- Media index verification found one present root and 45943 index entries:
  `/var/home/charlie/workspace/wechatbackup/media`.
- A live DB sync successfully pulled `EnMicroMsg.db` (`439438336` bytes, 53
  parts) plus WAL/SHM sidecars. That run loaded `count=0`, meaning no new
  WeChat rows were beyond the live state at that moment; media upload will be
  exercised by the next new image/voice/video/sticker message.
- SchildiChat old text placeholders do not mutate automatically after media is
  pulled. Matrix send transaction IDs are idempotent, so reusing the original
  `txn-prefix` returns the original text event. To refresh old media, send a
  bounded media-only backfill with a new transaction prefix and a separate
  state/ledger, then run `wechat-matrix-fix-event-timestamps` against that
  separate ledger.
- On 2026-09-10 a 20-message media-only refresh smoke used state/ledger under
  `~/.local/state/wechat-matrix-media-refresh`, `--only-media`, and
  `--txn-prefix wechat_media_refresh_`. It sent 10 `m.image`, 2 `m.audio`, 4
  `m.video`, 1 `m.file`, and 3 text fallbacks for unmatched emoji, then fixed
  timestamps with `updated=20 missing=0`.
- Later on 2026-09-10 this media-only append approach was rejected because
  SchildiChat displays old appended media out of the original conversation
  position. The 20 smoke events were redacted, and the accepted approach became
  clean chronological restore rooms with prefix `微信复原｜`.
- Do not trust `matrix_msgtype='m.video'` alone. A bug briefly uploaded WeChat
  video thumbnails (`.jpg`) as Matrix `m.video` events. Verify Matrix event
  `content.info.mimetype` starts with `video/` and local file sniffing detects
  real MP4 (`ftyp`) before treating a restored event as video. The importer now
  rejects image MIME candidates for WeChat `message.type=43`.
- 2026-09-10 video coverage after MIME sniffing: WeChat DB had 1773 video rows;
  local media roots contained 505 real video matches and 1268 rows with only
  thumbnails or missing original video files. Missing originals must remain text
  placeholders unless recovered from another phone/backup source.

## 2026-09-20 SchildiChat Empty Room List After Restore

Symptom: Synapse restore/import was complete and the Android client showed a
large unread badge, but SchildiChat's overview page only showed the
`正常优先级` category header with an empty list.

Two separate issues were present:

- The public Matrix HTTPS entry on `charlie1990.duckdns.org:443` was served by
  user `caddy-hermes.service` with `tls internal`, so SchildiChat rejected sync
  with `UnrecognizedCertificateException` / `Trust anchor for certification
  path not found`.
- After sync recovered, the local SchildiChat room-list preference had
  `ROOM_LIST_ROOM_EXPANDED_正常优先级_ALL_null=false`, so all rooms under that
  category stayed hidden.

Repairs applied:

```bash
# user Caddy now uses the public ZeroSSL chain copied under user-readable config
systemctl --user restart caddy-hermes.service

# duplicate system Caddy monitor was disabled because it only failed on :443
sudo systemctl disable --now caddy-monitor.service

# phone-side preference backup and expand
adb shell 'su -c "cp /data/user/0/de.spiritcroc.riotx/shared_prefs/de.spiritcroc.riotx_preferences.xml /data/user/0/de.spiritcroc.riotx/shared_prefs/de.spiritcroc.riotx_preferences.xml.bak-20260920-expand"'
adb shell 'su -c "sed -i \"s/name=\\\"ROOM_LIST_ROOM_EXPANDED_正常优先级_ALL_null\\\" value=\\\"false\\\"/name=\\\"ROOM_LIST_ROOM_EXPANDED_正常优先级_ALL_null\\\" value=\\\"true\\\"/\" /data/user/0/de.spiritcroc.riotx/shared_prefs/de.spiritcroc.riotx_preferences.xml"'
```

Verification:

- `openssl s_client -connect charlie1990.duckdns.org:443 -servername
  charlie1990.duckdns.org -verify_return_error` returns the ZeroSSL/Sectigo
  chain with `Verify return code: 0`.
- Phone `curl` without `-k` can fetch
  `https://charlie1990.duckdns.org/_matrix/client/versions`.
- Synapse `user_ips` has a fresh `SchildiChat/1.6.62.sc92` row.
- SchildiChat overview renders imported rooms under expanded `正常优先级`.
