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
Do not directly mutate the WeChat Android database for delete sync. Mark
Matrix-deleted or WeChat-missing messages as `knowledge_state='excluded'` so
FastGPT/Hermes memory imports skip them.

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
