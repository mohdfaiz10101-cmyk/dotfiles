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

## 2026-10-18 OpenWrt ADB Transport Recovery

- If Matrix shows an old newest message while SchildiChat itself can connect,
  inspect `wechat-matrix-incremental.service` before clearing client cache.
  On this date its old FRP-only ADB transport stopped at message `213761`;
  the phone export still contained 828 newer rows.
- `wechat-matrix-incremental-sync` now selects ADB in this order: attached USB
  (`ff3ef385`), OpenWrt Wi-Fi (`192.168.5.211:5555`), then legacy FRP/overlay
  fallbacks. It also passes the selected transport to media prefetch.
- USB serials must be checked with `adb devices`, not `adb connect`: they are
  already attached devices and are not host names.

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

## 2026-09-21 SchildiChat media fidelity repair

- User-visible problem: restored SchildiChat rooms were mostly text
  placeholders. WeChat voice messages did not play, and many WeChat
  sticker/emoji messages showed only `[表情]`.
- Voice root cause: WeChat voice files under `voice2` are named `.amr` but many
  begin with `#!SILK_V3` / `\x02#!SILK_V3`, so Matrix clients cannot play them
  as AMR. `wechat-matrix-sync-export` now detects WeChat SILK and transcodes it
  to Ogg/Opus before upload.
- Voice decoder/runtime:
  - Python venv: `~/.local/state/wechat-matrix-media-fix/venv`
  - Package: `silk-python`
  - Cache: `~/.local/cache/wechat-matrix-media/voice-opus`
  - Override env: `WECHAT_MATRIX_SILK_PYTHON`, `WECHAT_MATRIX_VOICE_CACHE`
- Voice verification: smoke ledger
  `~/.local/state/wechat-matrix-mediafix-voice-smoke-20260921/ledger.db`
  contains `msgId=66` and `msgId=67` as Matrix `m.audio` with uploaded media.
- Emoji/sticker root cause: many local WeChat emoji files are encrypted and
  extensionless. `wechat-matrix-sync-export` now loads the local emoji AES key
  from `EmojiInfo catalog=153`, decrypts the first 1024 bytes, and uploads
  decoded GIF/PNG/JPEG/WEBP as Matrix `m.image`.
- Emoji cache: `~/.local/cache/wechat-matrix-media/emoji-decoded`; override
  with `WECHAT_MATRIX_EMOJI_CACHE`.
- Emoji verification: smoke ledger
  `~/.local/state/wechat-matrix-mediafix-emoji-smoke-20260921/ledger.db`
  contains `msgId=452` (`message.type=47`) as Matrix `m.image`.
- WeChat `wxgf` caveat: proprietary `wxgf`/HEVC stickers are not uploaded as
  fake images unless this host has an HEVC-capable ffmpeg decoder. Current host
  ffmpeg lacks HEVC decode support, so `wxgf` falls back to text and writes a
  `.failed` cache marker. Smoke ledger
  `~/.local/state/wechat-matrix-mediafix-wxgf-smoke-20260921-0101/ledger.db`
  verifies `msgId=55` stays `m.text` with no `media_url`.
- Existing Matrix events are immutable. Old `[表情]` placeholders and old
  unplayable voice uploads will not mutate in place. For WeChat-like playback
  in SchildiChat, run a clean restore into new rooms with a new state directory,
  room prefix, and transaction prefix, then reconcile timestamps and membership.
- `wechat-matrix-timeline-restore-run` accepts `TXN_PREFIX` in the environment
  for clean reimports. Keep old restore rooms until the user explicitly asks to
  archive/delete them.
- Do not join the phone viewer account to a large restore while events are
  still being imported with current Matrix send timestamps. SchildiChat caches
  timeline timestamps in `disk_store.realm`; later server-side timestamp fixes
  do not reliably update already cached bubbles or room-list times. Preferred
  flow: import with `--defer-viewer-join`, fix timestamps per batch and at the
  end, then run room reconcile once so the phone sees already-correct events.
- `wechat-matrix-timeline-restore-run` now runs
  `wechat-matrix-fix-event-timestamps` after each batch when
  `FIX_TIMESTAMPS_EACH_BATCH=1`. The timestamp fixer updates both
  `events.origin_server_ts` and `event_json.unsigned.age_ts`; checking only
  `events.origin_server_ts` is not enough for mobile clients.
- If a SchildiChat test import was already viewed with wrong times, the local
  cache is
  `/data/data/de.spiritcroc.riotx/files/<session>/disk_store.realm`. Back it up
  before clearing. Do not touch `matrix-sdk-auth.realm`, `crypto_store.realm`,
  or `rustFlavor/matrix-sdk-crypto.sqlite3` unless intentionally logging out or
  resetting encryption state.

## Expected evidence

## 2026-10-05 complete-history restoration path

Use the v2 production workflow below instead of the old full-DB polling path.
The old `wechat-matrix-sync.timer` is disabled because it copied about 446MB
and force-stopped WeChat on every run.

- Root-direct incremental exporter:
  `~/.local/bin/wechat-phone-incremental-export`
- Phone helper source/runtime:
  `~/.local/share/wechat-matrix-sync/phone-helper/`
- The helper dynamically links WeChat's own `libWCDB.so`, reads the live DB via
  a consistent WCDB snapshot, and writes only a small plaintext subset. The DB
  key travels over stdin and must never appear in argv or logs.
- The helper is automatically redeployed after phone reboot if its
  `/data/local/tmp/wechat-matrix-helper` files are absent.
- Root-direct verification on 2026-10-04 exported 5 new rows (`msgId`
  213152–213156) in a 64KB SQLite file without stopping WeChat. A subsequent
  check after `213156` returned zero rows in under one second.
- Large phone media packages must use
  `~/.local/bin/adb-resume-pull`; ordinary `adb pull` twice discarded partial
  data at 52%/96%. The resumable pull verifies remote/local size and SHA-256.

Production history state is under
`~/.local/state/wechat-matrix-history-v2/production/`:

- Four room-stable shard runners: `~/.local/bin/wechat-matrix-history-shard`
- Durable service template: `wechat-matrix-history@.service`
- Five-minute recovery monitor: `wechat-matrix-history-watch.timer`
- Root-direct future sync: `wechat-matrix-incremental.timer`
- Media prewarm/cache:
  `~/.local/bin/wechat-matrix-media-prewarm` and
  `~/.local/state/wechat-matrix-history-v2/media-uploads.db`

The base corpus has 193,690 messages across 368 talkers. Message rows are
sorted by `(createTime, msgId)` before send, and every talker stays in one
shard. The importer sends through the appservice with Matrix `?ts=` so
`origin_server_ts` is the original WeChat time. A live four-room audit found
zero timestamp mismatches and zero stream-order inversions.

Media recovery evidence:

- 31,574 media-class rows audited.
- Initial local miss count: 5,325.
- Root phone recovery extracted 6,700 files and resolved 1,556 nested `.ref`
  pointers; remaining miss count: 3,216. Voice misses fell from 581 to zero.
- CDN emoji prefetch recovered 4,247/4,275 referenced objects.
- Media prewarm completed 22,002/22,002 jobs with zero upload failures and
  cached 21,712 unique MXC objects. Repeated files are reused by SHA-256.
- Missing source video is represented as an image thumbnail with
  `com.charlie.wechat.unavailable_video` metadata, never as a fake playable
  video.

Semantic fixes now include packed low-16-bit WeChat types, XML fallback for
`AppMessage.type`, native `m.location`, readable contact/system/call events,
native Matrix replies where the target exists, type-8/type-47 sticker images,
original document names, nested `.ref` payloads, and fully expanded merged
forward summaries. The largest merged forward in this corpus has 90 child
items; all 90 are now shown instead of truncating at 80.

Synapse 1.155.0 on this host does not contain MSC2716 `batch_send`, and its
SQLite engine declares itself single-threaded. Do not attempt direct DB event
insertion or claim `/batch_send` acceleration. The shard ledger and Matrix
transaction IDs provide safe idempotent resume; the recovery timer restarts an
incomplete shard after failure or reboot.

Current acceptance commands:

```bash
systemctl --user is-active wechat-matrix-history-{0,1,2,3}.service
systemctl --user list-timers --all | rg 'wechat-matrix-(history-watch|incremental)'
python3 -m py_compile ~/.local/bin/wechat-matrix-sync-export \
  ~/.local/bin/wechat-phone-incremental-export \
  ~/.local/bin/wechat-matrix-history-watch \
  ~/.local/bin/wechat-matrix-incremental-sync
pytest -q ~/.local/share/wechat-matrix-sync/tests/test_phone_media_prefetch.py
```

The current test suite has 41 passing tests. Do not declare the production
restore complete until all four `complete-0..3` markers exist, the combined
ledger count matches the source corpus plus post-baseline incrementals, and a
phone-side SchildiChat screenshot confirms a production room's ordering and
media controls.

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

## 2026-09-23 Final Media-Fixed Historical Restore

Final restore state:

- State directory:
  `~/.local/state/wechat-matrix-timeline-restore-mediafinal-20260921`
- Source DB:
  `~/.local/state/wechat-matrix-timeline-restore/EnMicroMsg.restore.db`
- Imported messages: `191368 / 191368`, max WeChat `msgId=210834`
- Rooms joined to `@charlie:100.120.189.27`: `365`, reconcile errors: `0`
- Matrix msgtypes in the final ledger:
  `m.text=174650`, `m.image=9164`, `m.audio=6504`, `m.file=552`,
  `m.video=498`
- Final timestamp check:
  `wechat-matrix-fix-event-timestamps --ledger-path .../ledger.db` returned
  `updated=0 skipped=191368 missing=0`, meaning every imported event already
  had a matching corrected timestamp.

Phone-side verification after the user switched Wi-Fi:

- ADB recovered through `192.168.123.22:5555` with device `PKR110`.
- Phone curl to
  `https://charlie1990.duckdns.org/_matrix/client/versions` returned
  `200 ssl=0`.
- SchildiChat package `de.spiritcroc.riotx` foregrounded
  `im.vector.app.features.home.HomeActivity`.
- SchildiChat overview displayed restored rooms under `正常优先级` with unread
  badge `274` and visible previews such as `[图片]`, `[语音] 10s`, `[分享]`,
  and WeChat emoji text like `[旺柴]`.

Important interpretation:

- Room-list dates such as `9月20日` / `9月19日` are the original WeChat message
  times, not the import execution date.
- The final import intentionally joined `@charlie` only after all events were
  imported and timestamps were fixed, to avoid SchildiChat caching the wrong
  timeline order.

2026-09-23 follow-up fixes after phone review:

- The final restore rooms were renamed from `微信完整复原｜<name>` to the original
  WeChat display names for all `365` rooms, and the English backfill room topic
  was cleared. Log:
  `~/.local/state/wechat-matrix-timeline-restore-mediafinal-20260921/room-rename-wechat-original-20260923.jsonl`.
- Synapse had stored uploaded WeChat media as authenticated media
  (`local_media_repository.authenticated=1`). SchildiChat `1.6.62.sc92` did not
  fetch those through the legacy `/media/v3/download` path, so visible media
  looked unavailable even when the Matrix event had `mxc://...`.
- Backup before the compatibility update:
  `/var/mnt/ai/cache/auto-migrate/.openclaw/workspace/homeserver.db.bak-wechat-media-auth-20260923-020339`.
- Exact compatibility update: only media IDs referenced by the final WeChat
  ledger were changed to `authenticated=0`; rows updated: `16718`.
- Verification after update:
  `/ _matrix/media/v3/download/100.120.189.27/<media_id>` returned `200` for
  JPEG, Ogg, MP4, and ZIP samples, and phone curl over
  `https://charlie1990.duckdns.org` returned `200 image/jpeg`.
- Not all WeChat media rows had source files available. Final ledger still has
  text placeholders for missing/unmatched source media, including
  `1202` images, `581` voice rows, `1283` videos, `853` app files, and many
  stickers. Example: recent voice msgIds `210819-210821` have XML
  `voiceurl/aeskey` in `message.content` but no `voiceinfo` row and no local
  file under the pulled media root, so they remain text placeholders unless
  WeChat private media is pulled again or CDN recovery is implemented.
- At this point phone ADB worked over `192.168.123.22:5555`, but root was not
  available to shell: `su` was inaccessible/not found even though Magisk
  packages existed. `wechat-matrix-media-pull --serial 192.168.123.22:5555`
  therefore could not read `/data/data/com.tencent.mm/...` until root shell
  access is restored.

2026-09-23 USB follow-up:

- After the phone was plugged in, USB ADB briefly appeared as `ff3ef385` and
  wireless ADB stayed available at `192.168.123.22:5555`.
- Root still did not recover on either path: `su` returned `inaccessible or not
  found`, and Magisk Manager (`io.github.vvb2060.magisk`) showed `当前 无法获取`.
- Existing local archives `voice2.tar` and `image2.tar` did not contain sample
  missing media filenames such as `071041091726747eed2f038100` or
  `th_d16681c9fbcf5a5bab0e770e0b2bf4c8`.
- Therefore remaining text placeholders require restoring Magisk/root access
  before rerunning `wechat-matrix-media-pull --serial <serial>` against
  `/data/data/com.tencent.mm/...`, or implementing WeChat CDN recovery from
  `message.content` `voiceurl/aeskey` metadata.

2026-09-23 later phone-side route/media findings:

- USB ADB instability was caused by enabled `ws-scrcpy-web.service` and
  `ws-scrcpy-web-redroid.service`. Their bundled ADB servers on ports `5039`
  and `5040` claimed the physical USB interface before the main ADB server.
  Both services were stopped and disabled from user autostart; main ADB then
  showed `ff3ef385 device usb:1-6`.
- Caddy was changed back to public LAN `80/443` for Matrix while avoiding the
  Tailscale-owned `100.120.189.27:443`: every site block now has
  `bind 192.168.123.209 192.168.123.71`, and global ports are
  `http_port 80` / `https_port 443`.
- Old Fedora firewalld forward ports `443 -> 2443` and `80 -> 2080` were
  removed with sudo. Direct host verification with SNI works:
  `curl --noproxy '*' --resolve charlie1990.duckdns.org:443:192.168.123.209
  https://charlie1990.duckdns.org/_matrix/client/versions` returns `200`.
- Padavan VTS entries `x65` and `x67` were updated from
  `192.168.123.71` to `192.168.123.209` for public `443` and `80`; runtime
  NAT was also inserted at the top of `vserver`. Despite that, phone curl to
  `https://charlie1990.duckdns.org/_matrix/...` still timed out from the
  cellular/public path, while `http://charlie1990.duckdns.org:19876` and
  `http://100.87.171.39:8008` both returned media successfully.
- Verified phone media downloads through working paths:
  `100.87.171.39:8008` returned `200 image/jpeg`, `200 audio/ogg`,
  `200 video/mp4`; `charlie1990.duckdns.org:19876` returned the same sample
  media successfully.
- SchildiChat `de.spiritcroc.riotx` currently shows red banner
  `到服务器的连接已丢失`. Without root, the app's private homeserver/session DB
  cannot be edited directly (`run-as` says package not debuggable and
  `/data/user/0/de.spiritcroc.riotx` is private). If it remains pinned to
  broken `https://charlie1990.duckdns.org` / `100.120.189.27` routes, the
  practical recovery choices are:
  1. restore Magisk/root and patch SchildiChat private config/cache to a working
     base URL;
  2. relogin SchildiChat manually using a verified working homeserver URL such
     as `http://charlie1990.duckdns.org:19876` or `http://100.87.171.39:8008`;
  3. repair router/public `443` from outside the LAN until phone curl without
     `-k` returns `200` for `https://charlie1990.duckdns.org/_matrix/client/versions`.

## 2026-09-25 Rooted Media Repair And Importer UI Cleanup

- Live media repair now selectively pulls matching files from rooted WeChat
  private storage with `wechat-matrix-sync-export --pull-phone-media`.
- SILK voice files are transcoded to Ogg/Opus. Uploaded repair media is marked
  unauthenticated for compatibility with SchildiChat's legacy media endpoint.
- Repair batches use `--skip-text-fallback`, so missing phone files retain the
  original placeholder instead of creating a duplicate text event.
- Repair result for msgIds `210835..212206`: `155` media replacements
  (`87` images, `68` audio); `27` unavailable source files were skipped.
- All `233` current imported rooms are in `m.direct`, so SchildiChat displays
  the WeChat contact/group name instead of the technical `wechat_import` user.
- Imported room topics were cleared through the Matrix API and the resulting
  topic state events were redacted. A SchildiChat initial sync was then run to
  remove cached notices. Final phone UI counts were zero for `wechat_import`,
  the backfill topic, the profile rename notice, and the topic removal notice.
- New imported rooms omit `m.room.topic` entirely and are created as direct
  rooms, preventing these implementation details from returning.
- Critical integrity rule: never rewrite signed fields such as top-level
  `event_json.origin_server_ts` or signed event content in Synapse SQLite.
  Event IDs hash the signed JSON. Timestamp maintenance may update only the
  database event timestamp/unsigned metadata unless events are recreated via a
  supported Matrix endpoint.
- Media-prefetch regression suite:
  `pytest -q ~/.local/share/wechat-matrix-sync/tests/test_phone_media_prefetch.py`.

## 2026-10-03 Cached Media Repair Finalization

- Re-ran all eight repair shards and merged unique non-text rows by
  `wechat_msg_id`. The ledger contained `6455` native events: `4382 m.image`,
  `1638 m.audio`, `160 m.video`, and `275 m.file`; duplicate message IDs: `0`.
  Important correction: this was a ledger/API-success count, not a media-byte
  integrity result. A later full content audit found only `4913` valid payloads
  and `1542` invalid payloads (`1121` undecoded WXGF images and `421` files
  whose entire payload was only UUID text). Never call all `6455` valid again.
- `wechat-matrix-sync-export` now retries transient Matrix send timeouts and
  connection errors with bounded backoff. Deterministic transaction IDs make
  retries safe. It also maps a stale bare USB serial to the matching active
  mDNS ADB transport when possible.
- Phone-prefetch tests no longer assume historical USB serial `ff3ef385`.
  Set `WECHAT_TEST_PHONE_SERIAL` to override the bounded current candidates.
  Final regression result: `9 passed`.
- Before writes, backups were created at:
  - `~/.local/state/wechat-matrix-media-repair-20260925/ledger.db.pre-merge-20261003-134306`
  - `/var/mnt/ai/cache/auto-migrate/.openclaw/workspace/homeserver.db.bak-media-finalize-20261003-134456`
    (`PRAGMA integrity_check=ok`).
- Timestamp finalization updated `6300` rows and found `155` already correct at
  the server database layer. Only `events.origin_server_ts` and unsigned age
  metadata were adjusted; signed root JSON, hashes, and signatures were
  preserved. Existing SchildiChat Realm entries can retain the import-time
  timestamp because direct server database edits do not emit a new sync event;
  do not claim phone timestamp correctness without a fresh-client/cache check.
- Finalizer redacted all `6455` original placeholders. Server audit found
  `6455` targets with redactions and `0` missing. Retried requests produced
  `6610` matching redaction events, which is harmless and idempotent at the
  target level.
- The first phone proof used the real route, not Fedora-only health:
  `192.168.123.22:5555` ADB and
  `https://charlie1990.duckdns.org/_matrix/client/versions` returned HTTP 200
  with TLS verification success. SchildiChat `1.6.62.sc92` rendered a native
  image and a native 3-second audio control; the audio entered playing state,
  no adjacent text duplicate was visible. The later root-assisted audit below
  supersedes the broad media-validity conclusion from that small sample.
- Residual audit: `1482` rows have no local source bytes (`497` video, `539`
  files, `442` images, `4` stickers). Legacy `cdnattachurl` values are CDN file
  IDs backed by `attachid`/AES metadata and require an authenticated legacy
  WeChat CDN session or reacquired phone files. Do not substitute the newer
  iLink `/c2c/download` protocol or fabricate Matrix media events.

## 2026-10-03 Root-Assisted Full Media Integrity Correction

- Root access on the phone is available through Magisk (`su` reports
  `uid=0`, SELinux domain `u:r:magisk:s0`). SchildiChat private state is under
  `/data/user/0/de.spiritcroc.riotx`; use root for read-only Realm/log evidence,
  but do not patch the live Realm directly. Stop the app before copying Realm,
  restart it immediately, and use server/API repair for durable media changes.
- Full byte-level audit command:
  `wechat-matrix-media-audit --ledger <ledger.db> --synapse-db /var/mnt/ai/cache/auto-migrate/.openclaw/workspace/homeserver.db --media-store /var/mnt/ai/cache/auto-migrate/.openclaw/workspace/media_store --workers 16 --output <report.json>`.
  It rejects UUID-only payloads, verifies images with Pillow, probes audio, and
  structurally validates MP4 rather than trusting the ledger, extension, or
  HTTP success alone.
- Installed static FFmpeg/ffprobe under
  `~/.local/libexec/wechat-media/` because the host FFmpeg lacked a working
  HEVC decoder. The importer now sniffs content, rejects UUID placeholders,
  converts WXGF even after stale `.failed` markers, and no longer trusts a
  misleading filename extension.
- Recovered all `1121` WXGF records into valid image events. Merged ledger:
  `~/.local/state/wechat-matrix-media-integrity-repair-20261003/ledger-merged.db`.
  Content audit: `1121/1121` valid, `0` invalid. Server verification: `1121`
  replacement events present, `1121` old bad events have redactions, `1121`
  event/unsigned timestamps match their WeChat time, `0` media rows missing,
  and all media rows have `authenticated=false`. Actual repository MIME split:
  `1019 image/jpeg`, `102 image/png`.
- Consistent pre-finalization backup:
  `/var/mnt/ai/cache/auto-migrate/.openclaw/workspace/homeserver.db.bak-wxgf-finalize-20261003-211332`
  (`PRAGMA integrity_check=ok`, `475782` events).
- Real phone verification used ADB serial `127.0.0.1:15555`, restarted
  SchildiChat, opened a repaired Matrix event permalink, displayed multiple
  repaired images in the room, and opened one in the full-screen media viewer.
  Evidence:
  `~/.local/state/schildichat-debug/schildichat-wxgf-open2.png` and
  `schildichat-wxgf-viewer.png`. Current private log at `21:53` contained
  `0` matches for `Unauthorized`, `Glide`, and `HttpException`.
- Remaining known invalid native events: `421` UUID-only payloads (`286`
  images, `105` files, `30` videos). Their real source bytes are absent; they
  are not repaired and must not be reported as working. This is separate from
  the `1482` original source-missing text placeholders. Restore media only from
  reacquired bytes or an authenticated legacy WeChat source; never fabricate
  replacement media.
- Regression suite after importer/auditor changes: `20 passed`.

## 2026-10-04 WeChat `.ref` Pointer Recovery

- Correction to the preceding residual conclusion: the `421` 36-byte UUID
  payloads were not missing media. Newer WeChat storage uses those files as
  pointers to real bytes under the media family's `.ref/d/<UUID>` path; a
  `.ref/c/<UUID>` cache/thumbnail may also exist. Examples were confirmed
  directly with phone root: an attachment `.ref/d` was a real ZIP and an
  `image2/.ref/d` payload was a real WXGF image.
- `wechat-matrix-sync-export` now expands matched UUID pointer files to both
  `.ref/d` and `.ref/c` during the single phone-side tar operation, prefers
  `.ref/d`, replaces only the derived local cache copy with the real bytes,
  and allows type-3 WXGF candidates to reach the existing normalization stage.
  It does not modify WeChat private storage.
- One 271 MiB ADB pull failed at 95% while the live WeChat sync timer was using
  the same transport. Recovery used nine 32 MiB-or-smaller parts with per-part
  retry and whole-archive SHA-256 verification. Future large root pulls should
  use resumable parts by default and avoid overlap with
  `wechat-matrix-sync.service`.
- Extracted `1302` archive members and resolved `429` pointer paths (duplicate
  messages can share refs). Exact message matching then found `421/421`, with
  zero missing: `286` images, `30` videos, and `105` files.
- Final repair ledger:
  `~/.local/state/wechat-matrix-media-ref-repair-20261004/ledger.db`.
  Byte-level audit before and after finalization: `421/421` valid, `0` invalid.
  All `421` old UUID fake-media events have redactions, all new event and
  unsigned timestamps match WeChat time, no event/media row is missing, and
  all `421` media rows have `authenticated=false`.
- Pre-finalization consistent SQLite backup:
  `/var/mnt/ai/cache/auto-migrate/.openclaw/workspace/homeserver.db.bak-ref-finalize-20261004-034032`.
  Source and backup were both `1741099008` bytes; backup schema and events table
  were readable. Foreground `quick_check` was interrupted because this slow
  mount kept it in kernel I/O wait for minutes. Do not use full/quick integrity
  scans as a blocking foreground gate here; use an online SQLite backup plus
  byte-size/readability/core-table checks, and schedule the expensive scan in
  the background when needed.
- SchildiChat initially showed offline because phone DNS to DuckDNS timed out,
  while LAN Matrix returned `200` and explicit mihomo proxy
  `127.0.0.1:7890` returned `200`. Restored Android global proxy to
  `127.0.0.1:7890`, restarted SchildiChat, and the app resumed syncing.
- Durable proxy conflict fix: `phone-network-stabilize status` previously
  cleared Android `http_proxy` to `:0` every five minutes. It now preserves the
  current proxy unless `PHONE_FORCE_GLOBAL_PROXY=1` or
  `PHONE_CLEAR_GLOBAL_PROXY=1` is explicitly set. The proxy watchdog now uses
  reachable ADB transport `127.0.0.1:15555` and writes all three Android proxy
  settings. Restarting the watchdog restored `127.0.0.1:7890`; a subsequent
  real `phone-network-stabilize status` run preserved it and reported mihomo,
  Play proxy, and DuckDNS checks healthy.
- Real-phone proof then passed for all three recovered classes: an image
  rendered and opened full-screen, an MP4 rendered and played full-screen, and
  a PDF downloaded/opened with visible page content. Current SchildiChat
  private log counts were `Unauthorized=0`, `HttpException=0`, `Glide=0`.
  Evidence:
  `~/.local/state/schildichat-debug/schildichat-ref-image-opened.png`,
  `schildichat-ref-video-playing.png`, and
  `schildichat-ref-file-opened.png`.
- Correct final content-valid total is now `6455 = 4913 + 1121 + 421`.
  The only remaining media recovery set is the separate `1482` original
  source-missing text placeholders (`497` video, `539` files, `442` images,
  `4` stickers).
- Regression suite: `22 passed`.

## 2026-10-05 Production room visibility and formatting

- A room that looks sparse can be the wrong duplicate room, not missing source
  data. For `58480079050@chatroom`, SchildiChat was displaying the old
  media-only room (`510` messages); the first production room contained all
  `2114/2114` source messages. Resolve the current phone room ID from
  `dumpsys activity top` `TimelineArgs(roomId=...)` before auditing counts.
- Production `rooms-*.json` membership was verified directly in Synapse:
  all `304/304` mapped rooms had `@charlie` membership `join`. The large
  SchildiChat “邀请” count was stale/legacy rooms and did not prove production
  membership was missing.
- Historical per-conversation imports must always pass
  `--room-context-format`. Without it, visible bodies include audit headers
  such as `[timestamp] room / sender #msgId`. The durable shard wrapper now
  includes this flag.
- Do not bulk-repair thousands of old events with `m.replace` on SchildiChat
  `1.6.62.sc92`. Relation events occupy the newest `/sync` timeline window but
  render invisibly, pushing original events behind pagination and producing a
  blank timeline. A single edit works; a room-sized edit flood does not.
- Recovery for a room already affected by a relation flood: rename it clearly
  as old/broken, re-import into a clean room with `--room-context-format`, keep
  the viewer out while the room is incomplete, then invite/join only after the
  source count, timestamp order, phone sync, and visible timeline pass.
- Reusable tools:
  `~/.local/bin/wechat-matrix-clean-room-format` is suitable only for bounded
  spot edits; `~/.local/bin/wechat-matrix-priority-procurement-clean` performs
  the clean priority-room import.
- Clean full-history rebuild is now the only enabled production path:
  `~/.local/bin/wechat-matrix-history-clean-shard`,
  `~/.local/bin/wechat-matrix-history-clean-watch`, and
  `wechat-matrix-history-clean-watch.timer`. State lives under
  `~/.local/state/wechat-matrix-history-v2/production-clean-v3/`.
  It always uses `--room-context-format --defer-viewer-join`; do not expose a
  shard room to `@charlie` until its source/ledger/timestamp/media audit passes.
  The old `wechat-matrix-history-watch.timer` is disabled.
- The verified clean seed room for `58480079050@chatroom` is
  `!HvAbRWHcEYvTiMyMdP:100.120.189.27`: `2114/2114`, zero missing events,
  zero timestamp mismatches, zero stream-time inversions, zero visible audit
  headers, zero media events without an MXC URL, and zero relation events.
  SchildiChat phone proof showed the 09:47 image rendered before the 09:50
  call event. Evidence:
  `~/.local/state/schildichat-debug/schildichat-production-clean-final2.png`
  and `schildichat-production-clean-older.png`.

## 2026-10-05 Prefix-free clean rebuild and legacy retirement

- The final clean-room naming rule is exact WeChat conversation names: no
  `微信完整历史｜`, `微信｜`, `旧版`, version, pilot, or audit prefix. Both the
  production and priority wrappers now pass `--no-room-name-prefix`.
- Existing clean-v3 rooms were renamed in place. Audit result: `331/331`
  room maps and server `m.room.name` states are prefix-free.
- Legacy cleanup helper: `~/.local/bin/wechat-matrix-retire-old-rooms`. It
  excludes clean-v3 IDs, then leaves and forgets mapped legacy rooms. The
  2026-10-05 run retired `1322/1322`; database verification showed zero legacy
  `join`/`invite` and every legacy leave event marked forgotten.
- Always query *all* current `@charlie` `join`/`invite` memberships after the
  map-based cleanup. Four old test rooms (`v2`/`v3`/`pilot`) and one stale
  prefixed invite were not present in historical room-map files. They were
  separately left, allowed to sync to the phone, then forgotten. Final server
  membership was exactly one joined clean seed room and zero invites.
- Do not immediately forget a room while SchildiChat is offline if the phone
  already cached it. Synapse can omit already-forgotten leave rooms from a
  later `/sync`, leaving stale local tiles. Correct order is: restore phone
  connectivity, leave/reject, confirm the tile disappears, then forget.
- If the server is clean but SchildiChat permanently retains stale rooms,
  root may rebuild only the SDK timeline store while preserving auth and
  crypto: force-stop `de.spiritcroc.riotx`, move the active session's
  `disk_store.realm`, lock, and management directory to a recoverable backup,
  then start `im.vector.app.features.MainActivity`. Do **not** delete
  `matrix-sdk-auth.realm`, `matrix-sdk-global.realm`, `crypto_store.realm`, or
  `matrix-sdk-crypto.sqlite3`. The 2026-10-05 recoverable backup is under
  `/data/user/0/de.spiritcroc.riotx/files/9a8e3348a6abb5d33f7a751621adde9b/root-clean-backup-20261005-1200/`.
- Phone Tailscale `100.120.189.27:8008` was unreachable during cleanup. A
  runtime-only, SchildiChat-UID-specific Android NAT rule redirected that
  destination to LAN `192.168.123.71:8008`; this allowed real `/sync` without
  changing the stored homeserver URL. It is not persistent across reboot.
- The media joins expand eight duplicate SQL result rows. Completion counts
  must use distinct `message.msgId`: per-shard expected counts are
  `23035, 20304, 132422, 17921` (`193682` total), not the raw joined-row total
  `193690`. The clean watcher uses the distinct counts so completed shards do
  not restart forever.
- Final phone proof after the cache rebuild showed only `采购 信息汇总`; UI
  counts were zero for `旧版`, `微信完整历史｜`, `微信｜`, all old v2/v3/pilot
  rooms, and the stale invite. Evidence:
  `~/.local/state/schildichat-debug/schildichat-final-list.png`.

## 2026-10-05 Completed-room visibility recovery

- Imported clean-v3 messages are sent by `@_wechat_archive`, so the viewer
  cannot redact them while remaining at power level 0. Run
  `~/.local/bin/wechat-matrix-grant-manager` to grant
  `@charlie:100.120.189.27` power level 100 in all clean-v3 rooms while keeping
  the room `redact` threshold at 50. New importer-created rooms include this
  manager permission through `power_level_content_override`.
- Incremental sync and the management ledger must use
  `production-clean-v3/{rooms,ledger}-combined`, `--room-context-format`, and
  `--no-room-name-prefix`. The older `production` combined files and
  `微信完整历史｜` prefix must not be reintroduced after the clean rebuild.
- The ledger command listener uses `@charlie:100.120.189.27` and polls with an
  `OnActiveSec`/`OnUnitInactiveSec` timer so commands such as `!总结 最近50`,
  `!记忆最近20`, and `!建任务` work after being enabled long after boot.

- The clean-history watcher now automatically enables and starts
  `wechat-matrix-incremental.timer` only after all four clean-v3 ledgers reach
  their exact distinct-message counts. This prevents live incremental sync
  from competing with the bulk restore and prevents it from remaining disabled
  after an interrupted restore finally completes.
- The incremental timer uses `OnActiveSec=1min` for its first run when enabled
  long after boot, then `OnUnitInactiveSec=10min` after each completed sync.
  `OnBootSec` plus `OnUnitActiveSec` alone can remain permanently `elapsed`
  when the timer is enabled after the boot deadline.

- `--defer-viewer-join` correctly hides incomplete rooms, but leaving every
  completed shard unjoined makes SchildiChat appear to contain only the seed
  room. `~/.local/bin/wechat-matrix-clean-join-completed` now invites and joins
  only rooms from `complete-*` shard maps and rejects all legacy/versioned name
  prefixes. The clean watcher invokes it on every pass.
- The first catch-up joined `268` additional rooms (`270/270` completed rooms
  joined, zero pending invites, zero rejected prefixes). Adding many
  memberships at once produced one large SchildiChat `/sync`; pause shard
  import while that catch-up is pending instead of repeatedly rebuilding the
  client cache.
- If the initial catch-up times out, temporarily add `"limit":1` to SchildiChat
  filter `2` in Synapse `user_filters`, restart Synapse once, let the large
  `/sync` finish, then restore the original filter JSON in the database. On
  this slow SQLite mount, a Synapse restart can take about 17 minutes, so do
  not restart it repeatedly. The successful catch-up response was `733184B`
  with HTTP `200`; later `/sync` and `/keys/query` requests returned normally.
- Real-phone verification after relaunch showed eight different clean room
  names in the first viewport, no connection-loss banner, and no legacy name
  prefixes. Evidence:
  `~/.local/state/schildichat-debug/schildichat-270-rooms.png` and
  `schildichat-270-rooms.xml`.
- After the client catch-up, restore the normal filter in the database without
  forcing another costly restart, then resume
  `wechat-matrix-history-clean-watch.timer`. Incomplete shard rooms remain
  hidden and are automatically joined when that shard reaches its exact
  distinct-message count.
## SchildiChat selection basket and Hermes routing (2026-10-06)

- Universal mobile selection UX: add the `🧺` reaction to each imported
  message or file. Selections are per Matrix user and may span rooms.
- Commands handled by `~/.local/bin/wechat-matrix-ledger`:
  - `!已选` lists the active basket.
  - `!清空已选` clears it.
  - `!处理已选 <instruction>` builds a manifest and creates a Hub task.
- Job manifests and attachment symlinks live under
  `~/.local/state/wechat-matrix-ledger/selection-jobs/<job-id>/`.
- The listener reads `m.reaction`, `m.room.redaction`, and `m.room.message`
  directly from the local Synapse event stream. Read `event_id`, `room_id`,
  `sender`, and `type` from the `events` table because `event_json.json` does
  not always repeat those top-level fields.
- MIME and Matrix content metadata determine recommended Hermes skills. Hub
  stores `skills`, `artifact_paths`, and uses assignee `hermes` with execution
  policy `approved_hermes_skills`.
- Approval boundary: basket submission creates only a `pending_approval` Hub
  task. Approval starts Hermes. Gmail/email work is marked `gmail_draft` or
  `gmail_send`; no external action runs at selection time.
- Successful submission redacts the temporary `🧺` reactions so the phone
  UI basket visibly clears while the durable job keeps its source event IDs.
- Verified test job `wmj_20261006034741_257` created Hub task
  `pt_20261006034741_daf3e50a` with `ocr-and-documents, hermes-agent`, a real
  local JPEG attachment, and status `pending_approval`. It was cancelled after
  validation; no Hermes execution or email send occurred.

### SchildiChat white room-list recovery

- Symptom: an existing room still renders its history, but Back to the room
  list shows a blank white surface and the user perceives that all chats are
  gone.
- First verify the ledger before touching app data. On 2026-10-06 it still had
  `193799` messages, `370` rooms, and `0` Matrix-deleted messages.
- Do not clear storage, sign out, or re-import. Force-stop and relaunch only:
  `adb shell am force-stop de.spiritcroc.riotx`, then launch the package.
- Verified result: the SchildiChat Overview list immediately returned with the
  imported WeChat rooms and the Hermes assistant room. The failure was a
  client rendering/navigation state, not server-side deletion.
- Avoid forcing a `matrix.to` deep link into SchildiChat during routine phone
  verification; it can leave this build in a blank transition state.

### SchildiChat click freeze and Android share router

- Root cause of the 2026-10-06 click freeze was imported-room unread load, not
  deleted data or slow Synapse sync. Only 7 of 370 imported rooms had an
  `m.read` receipt. Repeated room navigation grew SchildiChat from about
  514 MB RSS to about 2.7 GB while `NotificationDrawer` and
  `HeapTaskDaemon` consumed high CPU; phone swap was nearly exhausted.
- Repair helper: `~/.local/bin/wechat-matrix-mark-read`. It posts one
  `read_markers` request per imported room using that room's latest Matrix
  event. Do not stop at the latest imported message because later power-level
  events will leave almost every room unread again.
  Verified result: 370/370 rooms have read receipts and app memory returned to
  about 281 MB after restart; the Overview unread badge cleared completely.
- SchildiChat source is not stored locally, so do not patch or re-sign its APK
  only to inject a context-menu item. Android does not allow another app to
  insert arbitrary actions directly into SchildiChat's private long-press
  menu.
- Installed companion package: `com.charlie.schchatshare`, display name
  `Hermes / Mattermost CRM`. Source:
  `~/workspace/schchat-share-router/`.
- Phone workflow: long-press an image/file in SchildiChat, choose Share, then
  choose `Hermes / Mattermost CRM`. The app offers:
  `让 Hermes 处理`, `归档到 Mattermost CRM`, and `提取客户并创建跟进`.
- The companion uploads to authenticated Hub endpoint `/api/share-intake`.
  Token path is `~/.config/hub/share-intake.token` (never print it). Port 9800
  has a firewalld rich rule limited to `192.168.123.0/24` for phone access.
- Verified on PKR110: Android image share chooser displayed the companion;
  submitting to Hermes created a `pending_approval` task. Test tasks and test
  CRM notes were removed after validation.

## 2026-10-22 Dual desktop accounts / iOS history staging

- The second Linux Flatpak account is `w422417869`; source:
  `~/.local/share/wechat-flatpak-2/home/xwechat_files/w422417869_448e/db_storage`.
  Main desktop source:
  `~/.var/app/com.tencent.WeChat/xwechat_files/wxid_bjo2p0swoxm822_fe61/db_storage`.
- Both live desktop account contact/message databases were successfully opened
  read-only with SQLCipher 4.12, including WAL. Keys must be cached separately
  under `~/.cache/wechat-desktop-accounts/<account>/keys.json` (0600, directory
  0700). Never print keys or overwrite the old shared finance key cache.
- Helper: `~/.local/bin/wechat-desktop-stage`; timer/service:
  `wechat-desktop-stage.timer` / `.service`, every 30 minutes.
- Output: `/var/mnt/ai/data/wechat-desktop-stage/`, mode 0700.
  `snapshots/YYYY-MM-DD/<account>/` contains encrypted contact/message DB
  snapshots. SQLite backup includes committed WAL and each snapshot passes
  quick_check. Each day's files are replaced atomically; old days are retained.
  This snapshots databases only, not media binaries or full iPhone history.
- `ledger.db` is a private plaintext local staging ledger. Account-specific
  contact names/remarks and source observations remain available. Same canonical
  username/group ID shares a conversation; names alone never merge identities.
- Cross-account message deduplication requires positive server ID plus equal
  conversation, sender, type, timestamp and normalized content. Missing identity
  information falls back to account/database/table/local-ID isolation.
  Desktop group audit: 60 shared group IDs, 327 other shared contact IDs;
  first full staging audit: 770 cross-account duplicate group messages.
- `status.json` explicitly reports `local_staging_only`, `matrix_sent: 0`.
  This job does NOT publish to Matrix or change existing Matrix rooms. Existing
  Android incremental sync remains separate and currently reports no reachable
  PKR110 ADB transport; do not describe it as healthy merely because its timer runs.
- iPhone was not accessible through idevice_id. Initial iPhone history transfer,
  the phone-side automatic-backup setting, media coverage, and eventual Matrix
  publication remain pending. A PC backup container is not automatically a
  readable desktop message DB; verify the specific transfer format first.
- Next step: user checks iPhone's chat-history management/migration screen while
  on the same Wi-Fi as the computer. Verify Linux target support in the actual
  client before promising automatic iOS-to-Linux backup. Do not log either
  account into a different primary phone or merge by display name.
- Reuse the main account's existing Matrix room mapping for exact matching IDs
  when building publication. Desktop staging's 770 duplicates do not prove
  deduplication against the existing Android Matrix history; reconcile by
  conversation and server message IDs before sending anything.
- Account key refresh: dynamically identify each running WeChat process by its
  HOME/open DB paths, then reuse `collect_db_salts` / `scan_memory_for_keys`
  from `~/.local/bin/wechat-finance` with an explicit PID and scoped database
  list. Validate against each DB salt and store account-local keys privately.
  Never reuse historical PIDs or `find_wechat_pid()` for dual-account work.
- Check: `systemctl --user show wechat-desktop-stage.service -p Result -p ExecMainStatus`;
  `cat /var/mnt/ai/data/wechat-desktop-stage/status.json`.
- Validation: live SQLCipher reads and encrypted snapshot quick_check passed;
  ledger quick_check=ok, duplicate source keys=0, unresolved conversations=0,
  undecodable message bodies=0. Six dedup boundary checks and zstd normalization
  roundtrip passed. Uses existing system libzstd because Python zstandard is absent.

## 2026-10-22 Windows iPhone backup migration (in progress)

- Confirmed iOS backup source: Windows `D:\xwechat_backup`, account
  `w422417869`; 8485 files, 28528762060 bytes. SHA-256 source manifest:
  `/var/mnt/ai/data/wechat-ios-backup/source-manifest.json`. Windows generated
  the manifest locally with 128 KiB reads; 4 MiB reads failed with MemoryError
  during severe Windows commit pressure. Never log backup keys or credentials.
- Destination: `/var/mnt/ai/data/wechat-ios-backup/backup`, private mode 0700.
  Shared as `wechat-backup` by user service `wechat-backup-smb.service`; image
  `ghcr.io/servercontainers/samba` pinned by digest. Bindings: Fedora Tailnet
  `100.120.189.27:445`, and current LAN `192.168.2.17:445`; only Windows
  `100.91.93.99` / `192.168.2.14` allowed, authenticated SMB3 encryption required.
  Private credential locations: `~/.config/wechat-backup-storage/` and Windows
  `C:\WeChatSync\fedora-storage-credential.json` (G/SYSTEM ACL only).
- Copy job: `wechat-backup-migrate.service`, Windows helper
  `C:\WeChatSync\fedora-backup-copy.py`, native connector
  `fedora_storage_connect.py`. Robocopy is additive/incremental (`/E`, no
  `/MIR` or source deletion). Current copy uses LAN. `/Z` was very slow; `/J`
  retries incomplete files while already-completed files are skipped.
- `WeChatFedoraStorage` scheduled task reconnects the authenticated share for
  interactive Windows use. Must verify it remains successful after changes.
- Pending: finish copy; compare every destination SHA-256 to source manifest;
  verify original source did not change; test Windows directory symlink and
  app recognition; only then remove verified local backup bytes. Do not report
  Windows space freed before measured evidence.
- Backup payload confirmed `RMFH` magic, 967 ChatPackage files and 5342 Media
  files. SQLCipher desktop/Android DB decryption does not decode this format.
  The audited ChatImportKit upstream explicitly does not decrypt message content.
  Matrix publication remains pending readable source/verified decryption.
- Read-only Matrix preflight: existing ledger 195366 records; staged desktop
  messages 5496; exact existing-room IDs 54; 2585 (conversation,server-ID)
  duplicate candidates still require full sender/type/time/body validation.
  Report: `/var/mnt/ai/data/wechat-desktop-stage/matrix-preflight-20261022.json`.
- Windows SSH PowerShell profile had recursive automatic OpenCode startup.
  Fixed `C:\Users\G\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`
  to require SSH_TTY + CHARLIE_SSH_OPENCODE_STARTED and child `-NoProfile`.
  Original `.pre-wechat-migration-20261022` retained. Removed 68 matching
  service-session recursive shells, preserving the user's console terminal.

2026-10-22 migration continuation:
- Source hashing completed in 96 seconds. Interactive Windows session 1 verified
  authenticated share access and persistent Credential Manager entry. Native
  Windows directory symlink read/removal probe passed.
- `wechat-backup-verify-cutover.service` is queued behind the ongoing copy. It
  verifies all SHA-256s, syncs the destination filesystem, requires an unchanged
  Windows source inventory and an interactive-ready credential probe, creates
  the original-path directory symlink, verifies metadata/ChatPackage reads, and
  only then removes the exact verified originals. Source changes or hash/link
  errors retain originals; link verification errors roll back the rename.
- Three isolated cutover tests passed: valid migration, tampered destination
  rollback, and changed-source refusal. Windows directory-symlink rmdir semantics
  were emulated in Linux tests and separately exercised by a native Windows probe.
- Helpers: `~/.local/bin/wechat-backup-storage-status`,
  `~/.local/bin/wechat-backup-verify-cutover`,
  `~/.local/bin/wechat-backup-smb-run`. Startup always uses stable Tailnet;
  current LAN binding is optional and added only while that address is present.
- `wechat-backup-resume-pending.timer` checks every 15 minutes and only resumes
  interrupted initial copies; it stops acting after completion or a verification
  failure requiring inspection. Future backups write directly through the link.
- Format audit: `/var/mnt/ai/data/wechat-ios-backup/format-audit.json`. User was
  asked whether optional iPhone backup encryption/password was enabled; no
  password should be sent through chat or stored in logs. iPhone automatic-backup
  setting is not verified; PC settings expose storage path and USB mode only.
- LAN was slow under load: 8 MiB native share write/fsync took 24.82 seconds;
  pings to Windows reached ~3 seconds while copying. Do not claim transfer
  complete or Windows disk space freed until migration-status says complete.

2026-10-22 23:23 throughput check: ~5.32/28.53 GB staged (~19%); 15.2-second LAN RX sample was 2.86 MB/s on ChinaNet-K2QE 2.4 GHz. File-size progress can stay flat during preallocated copies, so do not derive short-window throughput solely from target sizes. Remaining copy at that rate ~2.25 hours; storage estimate 2.5–3.5 hours including verification/variation. This is not a Matrix decryption/import ETA. For large migrations, measure throughput and report ETA early.

## 2026-10-22 Vladimir Univest quotation export

- User confirmed exact contact `wxid_txqirg0zx7hv12`, Bob (Vladimir) from
  Univest / remark Vladimir Univest. Never merge with Vladimir Khmil, Egorov
  or Vladislav by display name. Related groups were exported separately:
  `52222456833@chatroom` and `58710407602@chatroom`.
- Private output (current): `~/文档/客户资料/Vladimir-Univest-20261022/`.
  Previous `~/Documents/客户报价/Vladimir-Univest-20261022/` is a compatibility symlink.
  113 private messages (107 Matrix historical + 6 desktop staged), 18 group
  records; 17 original pictures, 1 video, 1 supplier quote PDF, all byte hashes
  verified. Range 2025-05-28 to 2026-10-21; this excludes the unreadable iOS
  RMFH backup and is explicitly incomplete.
- Created internal Excel (source message IDs, full chat, thumbnails), separate
  customer quote draft Excel/PDF/HTML, Obsidian vault, internal Notion ZIP and
  separate customer/internal ZIPs. No Notion cloud upload or customer message.
  PDF visual preview checked; both XLSX files reopened, 12 rows/10 embedded
  images each, no formulas from untrusted chat; all Markdown media links and
  19 original attachment SHA256 values verified.
- The group XLSX named `20260318乌克兰三套机器尺寸体积汇合版(1).xlsx`
  is a text fallback only; do not claim its bytes or logistics dimensions exist.
- The quote source PDF was extracted with existing `pdftotext -layout`; local
  fitz/pymupdf is absent. Tesseract eng+chi_sim OCR completed for 17 images;
  OCR is searchable evidence only and never authoritative pricing.
- Keep accepted prices, historical supplier offers, unanswered RFQs and internet
  reference prices separate. Do not sum alternative model choices, infer order
  quantities, convert exchange rates, or put supplier negotiation screenshots in
  the customer package. Retain original evidence internally.
- Private builder: `~/.local/share/wechat-quotation-export/build_vladimir_export.py`
  refuses to overwrite existing editable workbooks by default. Future incremental
  exports should create a new revision directory and deduplicate conversation +
  positive server ID, preserving manual quote edits.

## 2026-10-23 User-visible export location

- User wants files in the actual default Documents folder, easy to find.
- XDG Documents: `/var/mnt/ai/xdg/文档` (home alias `~/文档`).
- Customer exports: `~/文档/客户资料/<customer-project-date>/`.
- Vladimir package moved to `~/文档/客户资料/Vladimir-Univest-20261022/`;
  old Documents path remains a compatibility symlink. Default XDG desktop
  and `~/Desktop` have a `客户资料` directory shortcut; GTK3/GTK4 bookmarks
  both include the same folder. Builder path updated without regenerating files.
- Broad default now recorded in `~/AGENTS.md`; prefer visible file-manager
  routes in final replies, not hidden state paths or a separate English Documents.

## 2026-10-23 Incremental metadata refresh after cutover refusal

- Initial 8485-file / 28,528,762,060-byte copy finished 02:45; SHA256 verification completed 02:58. Cutover correctly refused because Windows metadata changed. Original Windows backup remained intact.
- Diff found no added/removed files and only 5 metadata files totaling 41,401 bytes: backup_time.dat, detail.dat, phoneid.dat, phone_history.dat, pkg_info.dat; detail.dat changed mtime only.
- Windows fedora-backup-manifest.py now reuses hashes only when path, size and mtime_ns match the previous manifest, with stable before/after stat checks. Refreshed baseline in 3 seconds: 8480 cached hashes, 5 rehashed. Old baseline/verified markers archived with .pre-metadata-refresh-20261023 suffix.
- Incremental robocopy completed; full destination verification restarted at 12:32. wechat-backup-verify-cutover.service handles verified cutover and removal of exact originals automatically. Check migration-status.json for terminal status; do not call storage complete from copied bytes alone.
- RMFH iOS content remains undecrypted and no new iOS Matrix events have been sent. Storage completion does not imply Matrix completion.

## 2026-10-23 Vladimir visual quote revision

- User rejected scattered exports and detached thumbnails: primary deliverables must be Excel and Word with left product image and matching quantity, unit price, currency and amount on the right. Use consistent product IDs; missing images stay explicitly missing.
- New visible delivery: `~/文档/客户资料/Vladimir_清晰图文报价/{Vladimir_图文报价.xlsx,Vladimir_图文报价.docx}`. Earlier evidence archive retained. Six product groups, eight mower options; 3 actual source crops embedded in Word and 4 image occurrences in Excel.
- Workbook: primary visual table, separate eight-option mower comparison, concise evidence map. Blue quantity cells editable; formulas return blank until numeric quantity and price exist. No overall total across options or currencies. Test copy recalculated 2*23000=46000 and 3*820=2460; blank quantity remains blank.
- Word rendered in LibreOffice and all 4 landscape A4 pages visually checked; workbook all 5 print pages checked. Remove outer cantSplit around nested tables to avoid whole-product page jumps; reduce compact card content to avoid orphan source lines.
- Sugar image/41800 USD is historical 10-lane supplier configuration, not requested 4–6 lanes. Mower shared appearance crop is not a verified photo for any of eight variants; original image's $450 must never be mapped to their $756–2044 prices. No paper/lid/test-cup photos recovered. Historical 500pcs each cup samples do not become new order quantity.
- Builder: `~/.local/share/wechat-quotation-export/build_visual_quote.py`; explicit `--rebuild-generated` required to overwrite editable deliverables. Keep source crops and ID mapping in the 配图 subdirectory.

## 2026-10-23 Account correction and deferred Vladimir extraction

- User explicitly corrected source: Vladimir must come from WeChat account `w422417869`, after its full iOS history is imported into Matrix. Previous mixed Android/desktop exports are NOT the requested delivery. Both old output folders carry a visible account-source mismatch notice; preserve originals. Do not assume the prior account's contact ID proves the target account's Vladimir identity. Resolve within target account after import.
- Requested layout: portrait contract-style Excel and Word; each product is a two-column block, original image left, vertically stacked editable product/specification/quantity/unit price/amount/terms right; repeat product blocks down the page. No wide multi-column product sheet as the primary delivery.
- At 12:45:19 storage completed: 8485 files verified, 28,528,762,060 bytes stored on Fedora, Windows original path now directory symlink to encrypted authenticated SMB share. 28,545,056,768 allocated Windows bytes freed. iOS RMFH content is still undecrypted; matrix_sent=0. Do not claim full task or Matrix completion.
- Outstanding sequence: obtain readable full source for w422417869, account-scoped dedup/provenance-aware Matrix import and validation, then target-account Vladimir extraction and contract-style Excel/Word regeneration. No background decryption/import automation is proven running.

## 2026-10-23 RMFH probe and direct iPhone fallback

- User explicitly requires continuing decryption before Matrix/Vladimir work. Do not imply an unproven decryption daemon is working in the background.
- Native samples prove RMFH frame header=128 bytes and RMFT footer=128 bytes (backup.attr 258 bytes has 2-byte payload). ChatImportKit's inferred 16-byte header is not sufficient for this backup. Do not treat its inferred header fields as a verified specification.
- Bounded AES-GCM candidate test: `~/.local/bin/wechat-rmfh-key-probe`, report `.../wechat-ios-backup/research/key-probe.json`; 2 candidate keys, 14,432 trials, zero authenticated successes on backup.attr. This only rejects the tested candidates/layouts, not all possible decryption. No plaintext or keys logged; original backup untouched.
- No iPhone visible via Fedora idevice_id USB or network. Windows native cfgmgr32 Apple USB presence check also empty; standard Apple MobileSync directories absent; Windows pairing record count zero. Mobile backup key not obtained. Current Windows Weixin 4.1.15.56 running; no proof desktop memory contains the mobile RMFH key.
- Requested user connect the source iPhone to Fedora, unlock and Trust. This physical source/trust step is required for the currently prepared alternative; no password should be put in chat.
- Acquisition helper `~/.local/bin/wechat-ios-direct-backup`: default status-only; explicit `--backup` writes default-incremental idevicebackup2 data directly to `/var/mnt/ai/data/wechat-ios-direct-source/MobileSync/Backup`. Refuses ambiguous devices, validates pairing, checks a conservative device-used bound plus 10GiB free reserve, never restores or changes encryption. Check Status.plist SnapshotState and Manifest.plist encryption before exposing app data. Account remains unverified until examined; refuse Matrix import based on intended-account label alone. Syntax passed; no-device check returned needs_iphone_usb_trust. Actual backup path has NOT been device-tested.
- Fedora data disk currently 147GiB free. If conservative whole-phone upper bound does not fit, inspect capacity before starting; do not exhaust the disk.

## 2026-10-23 Source iPhone connected; filtered backup running

- Fedora USB pairing validated; device fingerprint `3eeba0dc137b`. iOS WeChat version 8.0.75.33. Read-only pymobiledevice3 `backup2 encryption` reports off; no backup encryption setting changed.
- Device-used upper bound ~171.6GB exceeded Fedora data free ~156.8GB, so do not run the original whole-device conservative path. Installed isolated pymobiledevice3 11.43.1 at `~/.local/share/wechat-ios-tools/venv`; CLI supports --only-regex.
- User service `wechat-ios-direct-backup.service` runs helper `wechat-ios-direct-backup --backup --wechat-only`. Filter `com\.tencent\.xin(?:[./-]|$)` includes main app and app-group domains. Other payload bytes are drained, not stored; device may still transfer substantial data. Manifest may retain unrelated metadata; never treat this as a restorable whole-phone backup. No --full or --patch-manifest.
- Backup started 13:38; phone passcode prompt appeared and was dismissed at 13:38:06. Destination `/var/mnt/ai/data/wechat-ios-direct-source/MobileSync/Backup/`; private backup.log. Service guards 10GiB disk reserve and preserves partial files on failure. Initial snapshot entries include zero-byte discard placeholders which are cleaned after completion; do not report placeholder counts as messages recovered.
- HouseArrest VendContainer and VendDocuments for com.tencent.xin were read-only tested and refused InstallationLookupFailed; no direct AFC shortcut established. Do not retry without changed evidence.
- Post-backup helper `~/.local/bin/wechat-ios-source-audit` is gated by shared backup lock and successful completion state. It parses LoginInfo2.dat username/alias, requires exact target w422417869, examines SQLite headers, and locates Vladimir candidates without exporting chat content. Actual account verification remains pending backup completion. Syntax check and active-backup refusal tested. Modern MMKV fallback may be needed if LoginInfo2.dat does not identify target.
- Primary references: https://doronz88.github.io/pymobiledevice3/cli/backup2/ and https://github.com/BlueMatthew/WechatExporter . Read-only parser source retained under direct-source/research for schema verification; do not infer complete data from upstream formats alone.

## 2026-10-23 First filtered backup FAILED payload completeness; file-ID retry

- First transfer ended ~14:16 (38m20s), but end-to-end audit found 94,680 WeChat manifest entries and only 104 main-app payloads / 1 app-group payload actually preserved. All essential Documents/DB SQLite files and LoginInfo2.dat were missing. This is NOT a successful chat acquisition despite CLI 100%/exit0. Old source-audit renamed source-audit.first-filter-missed-payloads.json.
- Cause: CLI regex applies to device-side paths during transfer. Those paths do not reliably contain the bundle ID; the earlier regex kept only configs whose names included com.tencent.xin. Do not repeat domain regex filtering during first transfer on this phone. No Matrix messages sent.
- Full index confirms Documents/dda3d19568edb8ced00218da22f32eb9/DB/{MM.sqlite,message_1.sqlite..message_4.sqlite,WCDB_Contact.sqlite}, plus Documents/MMappedKV/mmsetting.archive.w422417869. Hash is MD5(w422417869), but verify actual LoginInfo2 before publishing.
- Built private `.../direct-source/wechat-selector.db` from complete manifest, 94680 exact WeChat main/group/plugin file IDs. New helper `~/.local/bin/wechat-ios-fileid-backup` matches incoming host payload basename to these IDs; synthetic known opaque-path match and unrelated-ID rejection passed. It writes transfer-progress.json with actual percent + kept/discarded counts and private filter-path-samples.json for diagnostics.
- Existing direct helper now refuses the failed regex fallback, uses file-ID helper, supports --reacquire-missing, guards 10GiB reserve, and requires essential DB payloads present before declaring completion. User unit currently has one-off --reacquire-missing (forced full replay); REMOVE that argument after successful reacquisition so later backups are incremental. Refresh selector from completed index if paths evolve.
- File-ID retry started 14:36, phone requested passcode again. User told to enter it on device, never in chat. Source audit service queued after retry. This is a trusted, standard MobileBackup2 operation; no jailbreak or iOS root access obtained.

## 2026-10-23 Verified iPhone source and SchildiChat route diagnosis

- Standard trusted MobileBackup2 acquisition completed; no iOS jailbreak/root. LoginInfo2 verified account `w422417869`. Four message databases contain **414686** records, not 415686. All core SQLite quick checks passed. Compatible dict ID 5 at `/var/mnt/ai/data/wechat-ios-stage/MsgDict.dict` SHA256 `6413a19197f497ff9d45b18c5e7c78376b7a1020bcdaec8b5a0e04d03bd21a8c` decoded 128537 Zstd messages without failure. Source: darkskygit/ChatImporter `packages/chat_importer/src/matcher/ios_wc/MsgDict.dict`.
- Local adapter `/var/mnt/ai/data/wechat-ios-stage/normalized.db`, helper `wechat-ios-stage`. Target Bob/Vladimir Univest `wxid_txqirg0zx7hv12`: 459 records. Includes source DB/table/local IDs, stable synthetic Android-adapter IDs, media-quality audit. OpenIMContact and CustAsstContact must be included; Friend alone left 579 unresolved records, full contact tables reduced this to 16. Do not merge unresolved IDs by nickname.
- Old clean-v3 195400 events all have sender `@_wechat_archive`, with room membership display name `_wechat_archive`. Phone UI confirmed technical sender name plus a duplicated sender line. This requires identity-aware chronological reconstruction, not global profile renaming or mass m.replace.
- Phone actual homeserver is HTTPS DuckDNS; explicit HTTP proxy localhost:7890 means app-UID DNAT is ineffective (removed after zero-hit diagnostic). SchildiChat log showed SSLPeerUnverifiedException, certificate for unrelated nigirocloud host, then sync timeouts. Phone proxy domain resolution used public 125.110.234.23 instead of current Fedora LAN.
- Runtime-only mihomo hosts override `charlie1990.duckdns.org: 192.168.5.144`, domain DIRECT, DNS use-hosts enabled. Original private config saved to `~/.local/state/schildichat-debug/current-20261023/mihomo-before.private.yaml`; persisted phone YAML was not changed. Reload via controller PUT /configs payload. Phone proxied HTTPS returned200/ssl0. Do not use static LAN mapping off LAN; guard/restore needed before claiming durable multi-network repair.
- First catchup took191s and client timed out; subsequent retry succeeded51.538s,329091B. Do not restart Synapse or clear cache just because first catchup times out. Phone UI subsequently showed Oct23 messages (14:56 service notification,13:02 Charlie&Maksym,12:35 procurement), connection banner gone. Technical sender issue remains pending merge.
- `wechat-dual-merge-audit` builds source-preserving local index at `/var/mnt/ai/data/wechat-dual-merge/`, never publishes. Android delta snapshot since213151 produced1659 records through214879. Preserve user deletions and selection/CRM links during cutover.

- Durable LAN route helper `~/.local/bin/schildichat-matrix-route-ensure` and 2-minute user timer verify proxied HTTPS, apply runtime-only domain hosts override from the unchanged persisted config when needed, and reload the persisted baseline when no LAN endpoint is reachable. Does not disable TLS verification or clear auth/crypto. Off-LAN public path is not yet verified.

- Hot Synapse SQLite migrated to `~/.local/share/matrix-hot/homeserver.db` on SSD; original configured path is now a symlink, prior main/sidecars retained with `.before-ssd-20261023`. SQLite backup quick_check ok; source/destination event counts both767466. A health guard restarted the server during copy, so final cutover temporarily masked the persistent unit (runtime mask is lower priority than ~/.config user units and was insufficient). Original unit restored, all masks removed, service and incremental timer active. API versions200/7ms and whoami200/3ms after restart. No bulk media moved. Keep future hot operational DBs on SSD; data-volume SMR random I/O caused multi-minute scans/fsync and 60s mobile sync failures.

## 2026-10-23 Sender-aware dual publication in progress

- Active units `wechat-dual-publish@0..7.service`, helper `wechat-dual-matrix-publish`; deterministic SHA256(talker)%8 shards, per-room timestamp order, appservice per-contact puppets, self profiles distinguish main vs w422417869, system/pat/group-call messages use system profile. Native file/image/voice/video and MD5-verified sticker media. Rooms remain hidden until complete/audited.
- Source-preserving merge index `/var/mnt/ai/data/wechat-dual-merge/merge-index.db` now symlinks to `~/.local/share/matrix-hot/dual-merge-index.db`; iOS normalized.db similarly points to hot/ios-normalized.db. Prior cold copies retained with before-ssd suffix. Source rows Android195400 (59 original events preserved from Matrix), iOS414686; 311 shared conversations. 132823 strict duplicates +3521 platform/system/recall/inline-emoji variants linked. Body normalization must strip only the actual sender UID, never arbitrary Chinese headings followed by a colon. Both raw account observations retained.
- 59 baseline ledger records were absent from both recent native snapshots; reconstructed from original Matrix events with provenance. All authors resolved: 33system,12self,9unique original source displayname,5 incoming Charlie resolved to wxid_pdrrqzmopfcp29 using Android-only alias candidates excluding own main account. Never merge another Charlie (Meinme30) from iOS by nickname. Three old videos resolved from native videoinfo2.human. Sixteen iOS records still lack canonical conversation identity; preserved locally and not silently merged.
- `wechat-dual-identity-refine`: media prefixes can be `uid:6171:0` or `uid:0:1:...`; parse direct XML fromusername for iOS and treat app types62/107 as system notices. Current all known-conversation authors resolved.
- `wechat-ios-emoji-stage` recovered7437 downloaded+198 cached exact-MD5 files; 22source failures+16invalid payloads rejected;7930unique message MD5s,7673eligible CDN URLs,23690 sticker messages. Allow only validated actual Tencent CDN hostnames. Video thumb aliases recovered2983 where original is absent, explicitly labelled unavailable original. SILK->OGG tested ffprobe duration1.9465.
- First hidden Vladimir pilot566 (Android107/iOS459) had zero timestamp inversions and proper profiles. It was retained in hot/dual-publication.pilot-before-native.db; original hidden room !ihmmaBugCkfilATppA:100.120.189.27 is not viewer-joined. Final replay uses improved media and source formatting. Do not confuse this hidden pilot with phone-visible completion.
- `wechat-dual-room-cutover` / wechat-dual-cutover.timer exposes10 audited complete rooms per45s, merges canonical ledger rows/source mappings and main/shard room maps, marks historical events read, leaves exact prior room; never forget before mobile sync. Crash journal preserves old_room even if map was updated before a failure. Visible list tracked in hot/dual-publication.db.visible_rooms.
- Production combined ledger now symlinks to hot/production-ledger.db (195405 at transfer), source backup before-ssd retained. Ledger listener init creates message_versions/messages_all_versions; old selections and queued job manifests remain resolvable. One queued basket job preserved, no active selected rows at cutover setup.
- Legacy incremental.timer stopped; old incremental main exits if hot/dual-mode.json says legacy_import_disabled. Do not re-enable old Archive sender after cutover. Sender-aware fresh-tail importer still needs completion.
- root USB SSD fsync probe measured33durable commits/sec (NoCoW34.7, no improvement). Only rebuildable publication state + derived dual-ledger connections use WAL synchronous=NORMAL; canonical Synapse database and operational production ledger retain durable defaults. Transaction IDs are deterministic for replay after interrupted publication.
- SQLite query-planner pitfall: without ANALYZE, joining matches+iOS+Android on source/local_id planned an80billion Cartesian loop. Force matches CROSS JOIN records on exact PKs or ANALYZE first; explain plans before large joins.
- Incremental iOS file selector now learns exact trusted WeChat app container only from known fileID+authoritative path, then accepts new payloads only when SHA1(domain-relativePath) matches actual fileID. Self-test passes known, new, unrelated and wrong-ID cases. Parent refuses missing new payloads before selector refresh. Future actual incremental device run remains untested; do not claim unattended iOS auto backup.

- Found and fixed the main mid-import performance regression: every worker resent identical puppet displaynames, and restarts re-triggered profile fanout. Synapse had448 completed update_join_states jobs,14cancelled,1active; current membership profile mismatches were0 for both self puppets and system. Publisher now checks profiles first and skips unchanged profile PUTs/registration and already-joined room joins. No pending core-task deletion or speculative Synapse patch was performed.

## 2026-10-23 Restart idempotence, full text and live-tail implementation

- Synapse1.155 AS requests without device_id have no persistent event_txn_id_device_id record. Two hidden complete rooms each had one exact duplicate after restart. Preserved derived DB snapshot and retired hidden room IDs; replayed rooms wxid_s3qcr9ym7fsy12 (99) and52512839880@chatroom(57), server counts now exact. Never modify core event hashes/JSON to repair duplication.
- Publisher preloads unrecorded room events once on resume, compares exact sender/timestamp/full content including source IDs, reuses accepted events. On HTTP retry also checks actual server events before PUT. Eight interrupted tail events were recoverable; future failures still require cutover count audit. Per-room flock prevents baseline/live workers publishing the same room concurrently.
- Cutover now records/defer audit_issues rather than stopping every later good room on an extra event. Counts exclude m.replace relations. Missing media remains deferred. Do not infer mobile UI success from server audit.
- Native max upload now512M; actual265318120-byte video upload succeeded in10s, stored blob SHA256 equals original. Existing media upload helper streams files. Full plain text bypasses old2000-char clipping; five already published clipped messages restored using same-sender m.replace, original event IDs retained. Oversized formatted payloads retain full rendered+raw content in a native JSON attachment to stay under Matrix event size limits.
- `wechat-dual-matrix-publish --append-known --talker <uid>` supports same-room chronological appends with a per-room lock; refuses late source rows older than the recorded latest timestamp. No-op Vladimir replay produced0 new events, still566, and cutover media/count audit passed.
- New `wechat-dual-incremental`: exact Android msgId cursor, trusted phone-side SQLite export, native media fetch, source observations/dirty rooms/review queue at hot/incremental/queue.db. Initial actual export21new rows through214900, all authors resolved. Strict cross-account matches keep existing iOS event canonical. Identity/content conflicts retain raw observation but identity_ok=0 until reviewed. Publisher rows now require identity_ok=1. Baseline-active rooms wait; completed rooms append and refresh canonical ledger/source maps without marking fresh messages read. New cold rooms over100 historical rows wait for baseline. append_jobs preserves interrupted live appends for next pass. This does not automate iPhone backups.
- `wechat-dual-incremental.timer` every10min; old Archive incremental remains disabled. `wechat-dual-import.target` enabled at user startup resumes8shards+cutover+incremental+progress+Spaces timers. Long bulk import is still incomplete; do not claim finished.
- `wechat-dual-progress` refreshes `~/文档/微信整合/当前进度.md` every minute; status JSON and1h throughput samples retained privately. Approx remaining is upper bound (before source deletions/internal duplicates), ETA dynamic.
- `wechat-matrix-spaces` creates private root微信资料, customer/supplier/todo and account/shared views, reuses audited room IDs with m.space.child/parent; never copies messages. Only certain customer identity or explicit category name terms classify business folders.20new rooms/pass every2min. Persistent IDs/links in hot/spaces.json. Verify actual phone presentation later; currently foreground WeChat, do not steal focus or tap stale SchildiChat coordinates.
- Route guard now prefers attached USB ff3ef385 and falls back to FRP15555. Verified runtime HTTPS200/ssl0 on LAN; off-LAN still unverified.

## 2026-10-23 Vladimir corrected delivery and phone proof

- Relevant Vladimir room566 was already imported/audited, so its verified iOS459 observations could be used while the other rooms continue in background. Correct new delivery is `~/文档/客户资料/Vladimir_w422417869_图文报价_20261023/`: `Vladimir_图文报价_竖版.xlsx`, `.docx`, `Vladimir_图文报价_预览.pdf`.26cards (20requirements/offers +6historical),22paired images/video frames,4explicit missing-image positions. Both actual PDF renderings26A4portrait pages; inspect montage and first pages in 内部核对/{Word,Excel}预览. Full-text source-ID membership and all459iOS event links checked. Never reuse the two older wrong-account exports as this delivery.
- Builders in `~/.local/share/wechat-quotation-export/`: extract_target_ios.py (source-specific, exact459guard; uses actual decoded Matrix media blobs rather than encrypted/WXGF.pic), recover_quote_forward_images.py (6nested pictures), prepare_target_quote.py (reviewed26cards and provenance), build_target_portrait.py (refuses overwrite unless --rebuild-generated). Do not rerun over manual edits; create a new revision when user edits exist.
- Nested forward images are in authoritative selector OpenData/<conversation hash>/<native localID>/<dataid>.(pic|record_dat|record_thumb); match embedded dataid exactly. Recovered pool, two roll-material photos, float, unquoted fence and pad. Never assign $10/strip to the fence: those same-forward pictures show a roll material, 22*3350 without units, formal product name pending.
- Exact source workbook1400cc HS006J5A columnC3=52800元. Mower550A Longxin224cc row8I=8800; WPS DISPIMG ID_BE7DD25E21BC400DBFBD18F6874FE41C resolves through xl/cellimages.xml/rels to xl/media/image6.jpeg, so use that exact picture. Float chat$18/块 vs screenshot internet23–25 explicitly distinguished. Do not import main-account23,000USD straw-line price into this account-only quote; no directly linked numeric price in target iOS discussion.
- Word/Excel include original quantities separately from blank current PI qty; no default1, no cross-currency/alternative grand total. Actual LibreOffice recalc of test copy:2×8800=17600, blank second quantity stays blank.26trusted formulas, no external workbook links. Hidden navigation sheet must NOT have explicit print_area=A1:A1, or LibreOffice appends a27th page even when hidden.
- Fedora ffmpeg lacks HEVC decoder. Use existing `~/.local/libexec/wechat-media/ffmpeg-static` for native video stills. Its MJPEG images may lack JFIF/EXIF header recognized by python-docx: re-encode with PIL RGB JPEG before embedding. All script syntax checked.
- Physical USB SchildiChat verification19:09: room link now says打开 (previously加入). Opened final room and screenshot `~/.local/state/schildichat-debug/current-20261023/vladimir-real-timeline-loaded.png` visibly shows Vladimir Univest, 我（w422417869）, Oct21business messages, noArchive sender. Sept17history also readable. Did not claim native-image playback verified: later history scroll ended at Home; screenshot renamed home-after-history-scroll.png. Returned foreground to WeChat after check. Other large rooms still showArchive until bulk completion.
- Actual incremental pass initially21new through214900, completed three histories527/427/273, then followup captured3more through214903. A repeat pass source_rows0/new_rows0 completed with no identity reviews. Some dirty rooms wait baseline or cutover lock; timer every10min. Keep append_jobs for interrupted live publication, no old Archive importer.

-19:15 progress:23667published,446viewer-visible,499complete/684known conversations;8shards running/resultsuccess,0audit/media/identity issues. Rough remaining450083records at6.1/s≈20.4h; full import NOT complete.16unknown-conversation iOS records remain local; MD5 lookup against7726known UID candidates found no canonical match.
-19:16 phone root direct HTTPS probes to stable Tailscale100.120.189.27 and NetBird100.87.171.39 timed out while LAN route works. Do not pin these overlays or claim5G/off-LAN repair. Existing verified-LAN runtime guard unchanged.

-2026-10-23 22:32 user asked why20h: current actual114684published,653/684complete and visible,8.14events/s,359068approx remaining→12.25h dynamic ETA.5s/proc sample Synapse26.2% of one core,hostiowait8.7%,rootSSD sdc busy82.6%,mediaHDDsdd9.8%. Evidence points to storage/serialized SQLite event persistence rather than CPU saturation;8workers already running. Remaining31conversations are large, so room-completion percentage must not be presented as message percentage. EarlierArchive sender design requires chronological event reconstruction; decryption/indexing already complete.
