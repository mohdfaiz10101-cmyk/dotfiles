# WeChat Matrix SchildiChat Restore Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Rebuild PKR phone WeChat history into Matrix/SchildiChat as a clean chronological archive, with correct media rendering, merged-forward parsing, and a maintainable sync rule set.

**Architecture:** Treat WeChat DB and pulled media files as the source of truth. Matrix rooms/events are the server-side archive that SchildiChat syncs naturally. SchildiChat local cache must be treated as disposable client cache, not as the canonical editable database.

**Tech Stack:** Python, SQLCipher SQLite, Matrix Client API, Synapse local SQLite DB for tokens/timestamp repair, Android root/ADB media pull, systemd user services.

---

## Current Context

- Existing old Matrix rooms contain many `m.text` placeholders.
- Appending old media events into existing rooms causes SchildiChat timeline disorder.
- Directly editing SchildiChat local Realm/cache is not a sound primary strategy:
  - It will not change server-side Matrix history.
  - It risks corrupting client cache and crypto/account state.
  - It makes future phone/client changes hard to reproduce.
- Correct target is clean server-side restore rooms named with prefix `微信复原｜...`, imported once in chronological order.
- Current importer bugs already identified:
  - Media `body` used local filenames, so SchildiChat displayed file names as captions.
  - WeChat videos with only `.jpg` thumbnails were incorrectly sent as Matrix `m.video`.
  - Some image rows only have thumbnails locally; original files are absent from current phone storage.
- Merged-forward WeChat messages are usually `message.type=49` with `AppMessage.type=19`, with nested `recorditem` XML that needs dedicated parsing.

## Progress Update 2026-09-13

- `~/.local/bin/wechat-matrix-sync-export` now parses WeChat merged forwards:
  `AppMessage.type=19` / `recorditem` / `recordinfo` / `datalist` /
  `dataitem`. Output is a single readable `m.text` summary, not raw XML.
- Media formatting was tightened:
  - `m.image`, `m.audio`, and `m.video` body uses sender/room context, not local filenames.
  - Missing media text placeholders no longer include local path/stem values.
  - Video upload only occurs when the local file sniffs as real `video/*`.
- Added preflight gate: `~/.local/bin/wechat-matrix-restore-audit`.
  Full DB audit passed on 2026-09-13:
  - scanned `185502` rows
  - images: `9167`, original/mid `4134`, thumbnail `4120`, missing `913`
  - voices: `6501`, matched `6468`
  - videos: `1715`, real MP4 `504`, thumbnail/wrong-type `1200`, missing `11`
  - merged forwards: `365`, parsed `365`
  - bad media body: `0`
  - bad text placeholder: `0`
- `~/.local/bin/wechat-matrix-timeline-restore-run` now runs the audit before importing.
- A clean restore state was created at
  `~/.local/state/wechat-matrix-timeline-restore`.
  Earlier smoke states with bad placeholders were archived under
  `wechat-matrix-timeline-restore.smoke-bad-placeholder-*`.
- Smoke restore verification:
  - First 500 rows imported hidden from viewer; no `@charlie` membership.
  - Missing video samples `msgId=32/49` are readable text placeholders without filename stems.
  - Real video samples `msgId=2360/2398/2399/2402` imported as `m.video`
    with `mimetype=video/mp4`.
  - Synapse event JSON audit found `bad_video_mime=0`.
- Formal restore service is now running in background from the clean state:
  `systemctl --user status wechat-matrix-timeline-restore.service`.
  Keep `wechat-matrix-sync.timer` stopped until historical restore completes.
- Added completion monitor on 2026-09-13:
  - script: `~/.local/bin/wechat-matrix-restore-monitor`
  - service: `~/.config/systemd/user/wechat-matrix-restore-monitor.service`
  - timer: `~/.config/systemd/user/wechat-matrix-restore-monitor.timer`
  - status: `~/.local/state/wechat-matrix-timeline-restore/monitor-latest.json`
    and `monitor-latest.md`
  - behavior: every 2 minutes checks restore progress; restarts restore if it
    stops before completion; when complete, audits Synapse event JSON, fixes
    timestamps, runs `wechat-matrix-room-reconcile --preserve-names` to invite
    `@charlie:100.120.189.27`, then enables `wechat-matrix-sync.timer`.

## Non-Negotiable Rules

- Do not continue broad restore until media event formatting is fixed and validated.
- Do not use SchildiChat local DB/cache as the main sync target.
- Do not append historical media into old rooms.
- Do not mark JPG thumbnails as video.
- Do not put local media filenames in `body` for `m.image`, `m.audio`, or `m.video`.
- Keep live realtime sync state separate from historical restore state.
- Do not invite `@charlie:100.120.189.27` to restore rooms until the restore is complete and validated.

## Proposed Model

Use three layers:

- Source layer:
  - WeChat encrypted DB snapshot: `EnMicroMsg.restore.db`
  - Media roots: `/var/home/charlie/workspace/wechatbackup/media`
  - Optional recovered backup roots if found later.
- Restore layer:
  - New Matrix rooms with prefix `微信复原｜`
  - One room per WeChat talker.
  - Events sent oldest to newest.
  - Separate state and ledger under `~/.local/state/wechat-matrix-timeline-restore`.
- Client layer:
  - SchildiChat only syncs Matrix rooms normally.
  - Optional final SchildiChat cache refresh only after server-side restore is correct.

## Task 1: Freeze Bad Restore Output

**Objective:** Prevent more malformed restore events from being written.

**Files:**
- Inspect: `~/.local/state/wechat-matrix-timeline-restore/ledger.db`
- Inspect: `~/.local/state/wechat-matrix-timeline-restore/history.jsonl`

**Steps:**
1. Stop restore service:
   ```bash
   systemctl --user stop wechat-matrix-timeline-restore.service
   ```
2. Confirm inactive:
   ```bash
   systemctl --user is-active wechat-matrix-timeline-restore.service
   ```
3. Archive current bad restore state using `mv` with timestamp, preserving DB and ledgers.
4. Do not invite the SchildiChat user into bad restore rooms.

## Task 2: Redact Or Quarantine Bad Restore Rooms

**Objective:** Ensure malformed restore rooms do not remain visible or become the accepted archive.

**Files:**
- Read: `~/.local/state/wechat-matrix-timeline-restore.bad-*/rooms-by-talker.json`
- Read: `~/.local/state/wechat-matrix-timeline-restore.bad-*/ledger.db`

**Preferred approach:**
- Because the viewer was not invited to formal restore rooms, leave bad rooms unjoined and clearly mark their state folders as rejected.
- If any bad smoke rooms were joined or visible, redact events using the ledger and Matrix Client API.

**Validation:**
```bash
python3 - <<'PY'
import sqlite3
p='/var/home/charlie/.local/state/wechat-matrix-timeline-restore/ledger.db'
con=sqlite3.connect(p)
print(con.execute('select count(*) from messages').fetchone())
PY
```

## Task 3: Fix Media Event Body Formatting

**Objective:** Make SchildiChat render media naturally without showing local filenames as captions.

**Files:**
- Modify: `~/.local/bin/wechat-matrix-sync-export`

**Rules:**
- For `m.image`: `body` should be sender name or `[图片]`, not filename.
- For `m.audio`: `body` should be sender name or `[语音]`, not `msg_*.amr`.
- For `m.video`: `body` should be sender name or `[视频]`, not `*.mp4`.
- For `m.file`: keep a useful user-facing filename in `filename`; `body` may also use the document title or filename because file messages need names.

**Validation:**
Generate event content locally for sample `msgId` values:
- `15`: image
- `66`: voice
- `2360`: real MP4 video

Expected:
- `content.url` exists.
- `content.msgtype` is correct.
- `content.body` does not contain local file paths or hash-like media filenames.

## Task 4: Enforce Media Type Compatibility

**Objective:** Prevent thumbnails and wrong file types from being uploaded as the wrong Matrix media type.

**Files:**
- Modify: `~/.local/bin/wechat-matrix-sync-export`

**Rules:**
- `message.type=43` video must only send `m.video` when local file MIME starts with `video/` or file header indicates MP4 `ftyp`.
- JPEG/PNG/GIF candidates for video must be rejected.
- `message.type=3` image must only send `m.image` when MIME starts with `image/`.
- `message.type=34` voice must only send `m.audio` when MIME/extension is audio-like.
- Missing original video should become text placeholder, not fake video.

**Validation:**
```bash
python3 - <<'PY'
# Verify known thumbnail-only videos return no media path:
# msgId 32, 49, 107, 121 should not produce m.video.
# Verify known real videos:
# msgId 2360, 2398, 2399, 2402 should produce video/mp4.
PY
```

## Task 5: Improve Image Selection

**Objective:** Prefer better image candidates and avoid thumbnails when original/mid image exists.

**Files:**
- Modify: `~/.local/bin/wechat-matrix-sync-export`
- Possibly add audit helper: `~/.local/bin/wechat-matrix-media-audit`

**Rules:**
- For image messages:
  - Try `ImgInfo2.bigImgPath` first.
  - Then try decoded/cleaned original or middle image candidate names from XML content.
  - Then try `imgPath`.
  - Use `thumbImgPath` only as last fallback and label it internally as thumbnail coverage.
- Do not claim full original image restore when only `th_*` is available.

**Validation:**
Produce counts:
- total image rows
- original/mid image matched
- thumbnail-only matched
- missing

## Task 6: Parse WeChat Merged Forward Messages

**Objective:** Render WeChat merged forwards as readable nested content instead of raw placeholder/share text.

**Files:**
- Modify: `~/.local/bin/wechat-matrix-sync-export`
- Add tests or fixtures under a local test directory if available.

**Research basis:**
- Search GitHub and open-source WeChat exporters for `AppMessage.type=19`, `recorditem`, `recordinfo`, and `datalist` parsing patterns.
- Treat external code as reference only; implement local parsing against actual DB rows.

**Implementation shape:**
- Detect merged forward:
  - `message.type=49`
  - `AppMessage.type=19`
- Parse XML from likely fields:
  - `message.content`
  - `AppMessage.description`
  - `AppMessage` XML/body fields if present in DB schema.
- Extract nested records:
  - sender/title
  - timestamp
  - text
  - image/video/file references when available
- Render into Matrix as:
  - One `m.text` event with clear folded-style plain text summary, initially.
  - Later optional expanded multi-event restore only if order and media matching are reliable.

**Validation:**
- Count `AppMessage.type=19` rows.
- Generate dry-run output for 10 merged-forward rows.
- Confirm SchildiChat display is readable and not raw XML.

## Task 7: Build Preflight Audit Gate

**Objective:** Stop bad imports before they hit Matrix.

**Files:**
- Create or modify: `~/.local/bin/wechat-matrix-restore-audit`
- Modify: `~/.local/bin/wechat-matrix-timeline-restore-run`

**Audit checks:**
- Media index exists and is nonzero.
- Video event candidates have no non-video MIME.
- Media `body` fields do not contain obvious local filenames for image/audio/video.
- Merged-forward parser produces readable summaries.
- Sample Matrix upload can be downloaded through local and public Matrix media API.

**Validation output:**
```json
{
  "ok": true,
  "image_rows": 9167,
  "image_original_matches": 0,
  "image_thumbnail_matches": 0,
  "video_rows": 1773,
  "video_real_matches": 505,
  "video_thumbnail_only": 1268,
  "merged_forward_rows": 0
}
```

Use actual counts from the current DB.

## Task 8: Rebuild Clean Restore State

**Objective:** Start a fresh restore from `msgId=0` after fixes.

**Files:**
- State: `~/.local/state/wechat-matrix-timeline-restore`
- Script: `~/.local/bin/wechat-matrix-timeline-restore-run`
- Service: `~/.config/systemd/user/wechat-matrix-timeline-restore.service`

**Steps:**
1. Archive current restore state with a timestamp.
2. Create fresh state directory.
3. Copy latest verified `EnMicroMsg.restore.db` into the fresh state.
4. Start service.
5. Keep `--defer-viewer-join` enabled.
6. Import in bounded batches.

**Validation after first 500 to 1000 events:**
- Query restore ledger type counts.
- Query Synapse `event_json` for media events.
- Verify no `m.video` has `image/*` MIME.
- Verify image/audio/video `body` is not a filename.

## Task 9: Finish Full Restore And Fix Timestamps

**Objective:** Complete server-side chronological restore before exposing it to SchildiChat.

**Steps:**
1. Let restore run until `batch_done sent=0`.
2. Run timestamp repair against restore ledger:
   ```bash
   ~/.local/bin/wechat-matrix-fix-event-timestamps \
     --ledger-path ~/.local/state/wechat-matrix-timeline-restore/ledger.db \
     --limit 100000
   ```
3. Produce final counts:
   - total imported
   - per Matrix `msgtype`
   - per WeChat media type
   - missing media fallback counts
   - merged-forward parsed counts

## Task 10: Invite SchildiChat User Only After Validation

**Objective:** Make SchildiChat see only the final clean restore rooms.

**Files:**
- Use: `~/.local/bin/wechat-matrix-room-reconcile`

**Command:**
```bash
~/.local/bin/wechat-matrix-room-reconcile \
  --source-db ~/.local/state/wechat-matrix-timeline-restore/EnMicroMsg.restore.db \
  --room-map-path ~/.local/state/wechat-matrix-timeline-restore/rooms-by-talker.json \
  --log-path ~/.local/state/wechat-matrix-timeline-restore/room-reconcile.jsonl \
  --viewer-user '@charlie:100.120.189.27' \
  --preserve-names
```

**Validation:**
- SchildiChat sees rooms prefixed `微信复原｜`.
- Old malformed restore rooms are not visible.
- Media events open from SchildiChat.
- Timeline order is acceptable because rooms were populated oldest-to-newest before joining.

## Task 11: Optional SchildiChat Local Cache Handling

**Objective:** Use local cache only for refresh, not as the data store.

**Allowed operations:**
- Force SchildiChat sync/restart.
- Clear only safe cache after server-side validation and backup.
- Avoid editing `disk_store.realm` directly unless there is a tested schema-specific migration.

**Not recommended:**
- Writing WeChat records directly into SchildiChat local Realm/cache.
- Replacing Matrix event timeline locally without server events.

## Task 12: Live Sync Rule After Restore

**Objective:** Keep future WeChat messages correct after historical restore.

**Rules:**
- Live sync continues using `~/.local/state/wechat-matrix-sync/state.json`.
- Live sync should apply the same media formatting and MIME checks as restore.
- New media events should be real Matrix media events.
- New merged-forward messages should use the same parser once implemented.

## Tests And Verification Commands

Syntax:
```bash
python3 -m py_compile ~/.local/bin/wechat-matrix-sync-export ~/.local/bin/wechat-matrix-room-reconcile
bash -n ~/.local/bin/wechat-matrix-timeline-restore-run
systemd-analyze --user verify ~/.config/systemd/user/wechat-matrix-timeline-restore.service
```

Restore service:
```bash
systemctl --user status wechat-matrix-timeline-restore.service --no-pager -l
tail -n 80 ~/.local/state/wechat-matrix-timeline-restore/history.jsonl
cat ~/.local/state/wechat-matrix-timeline-restore/state.json
```

Ledger media audit:
```bash
python3 - <<'PY'
import sqlite3
p='/var/home/charlie/.local/state/wechat-matrix-timeline-restore/ledger.db'
con=sqlite3.connect(p)
print(con.execute('select count(*), min(wechat_msg_id), max(wechat_msg_id) from messages').fetchone())
for row in con.execute('select matrix_msgtype,count(*) from messages group by matrix_msgtype order by matrix_msgtype'):
    print(row)
PY
```

Synapse event JSON audit:
```bash
python3 - <<'PY'
import sqlite3, json
ledger='/var/home/charlie/.local/state/wechat-matrix-timeline-restore/ledger.db'
server='/var/mnt/ai/cache/auto-migrate/.openclaw/workspace/homeserver.db'
l=sqlite3.connect(ledger); l.row_factory=sqlite3.Row
s=sqlite3.connect(server); s.row_factory=sqlite3.Row
bad=[]
for r in l.execute("select wechat_msg_id,event_id from messages where matrix_msgtype='m.video'"):
    row=s.execute('select json from event_json where event_id=?',(r['event_id'],)).fetchone()
    if not row:
        continue
    content=json.loads(row['json']).get('content',{})
    if not str((content.get('info') or {}).get('mimetype','')).startswith('video/'):
        bad.append((r['wechat_msg_id'], content))
print('bad_video_count', len(bad))
print(bad[:5])
PY
```

## Risks And Tradeoffs

- Some old media cannot be fully restored because the original file is missing from current phone storage. Those must remain placeholders unless another backup is found.
- SchildiChat may display media `body` as a caption even when `url` is valid, so body text must be user-friendly.
- Matrix clients may order old events by stream insertion order despite repaired timestamps. The best mitigation is to import into clean rooms before joining the client user.
- Fully expanding merged-forward messages into nested events can disturb chronology; start with a readable single-event summary.
- Redacting already-created bad rooms can leave tombstone/redaction noise if the user has already joined them. Prefer not joining rejected restore rooms.

## Open Questions

- Should missing original images use thumbnail fallback, or should they remain `[图片，原图缺失]` text placeholders?
- Should merged-forward records be one summary event or expanded into multiple child events?
- Should restored rooms eventually replace old rooms, or should both remain with clear prefixes until manual cleanup?
