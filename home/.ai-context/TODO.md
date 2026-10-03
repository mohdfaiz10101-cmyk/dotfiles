# Pending Tasks

## SchildiChat WeChat media repair (partially completed; corrected 2026-10-03)

Status: byte-level verification corrected the earlier ledger-only completion
claim. `6034` native media events are now content-valid (`4913` previously
valid plus `1121` recovered WXGF images). `421` UUID-only fake-media events and
`1482` original source-missing placeholders still require real source bytes.
No repair worker or finalizer is running.

### Durable state

- Stable encrypted source snapshot:
  `~/.local/state/wechat-matrix-media-repair-20260925/EnMicroMsg.repair.db`
- Original text-event ledger:
  `~/.local/state/wechat-matrix-ledger/ledger.db`
- Existing replacement ledgers:
  `~/.local/state/wechat-matrix-media-repair-20260925/ledger.db` and
  `ledger-shard-0.db` through `ledger-shard-7.db`
- Room map:
  `~/.local/state/wechat-matrix-full-export/rooms-by-talker.json`
- Cached phone media:
  `~/.local/cache/wechat-matrix-media/phone-full-repair`
- Cached renamed attachments:
  `~/.local/cache/wechat-matrix-media/phone-attachment-repair`
- Validated CDN emoji cache:
  `~/.local/cache/wechat-matrix-media/emoji-decoded/cdn`

### Current verified result

- The old `6455` figure counted ledger/API successes, not valid bytes. Initial
  full audit: `4913` valid, `1542` invalid (`1121` WXGF plus `421` UUID text).
- All `1121` WXGF images were re-decoded and re-imported. New-ledger audit:
  `1121` valid, `0` invalid; all `1121` old bad events have redactions and all
  new server-side timestamps match WeChat time.
- Current total content-valid native events: `6034`. Remaining invalid native
  events: `421` (`286` images, `105` files, `30` videos) with no real bytes.
- Still unavailable because no matching source bytes exist locally: `1482`:
  `497` videos, `539` files, `442` images, `4` stickers.
- All shards `0..7` reached `batch_done`; their unique non-text rows were
  merged into the main repair ledger with `0` duplicate message IDs.
- Root-assisted SchildiChat verification passed on the actual phone: repaired
  images rendered in-room and opened in the full-screen viewer; latest private
  log had zero `Unauthorized`, `Glide`, and `HttpException` matches. Existing
  Realm cache can retain import-time display timestamps despite server fixes.
- Regression suite: `20 passed`.

### Durable completion artifacts

- Main ledger backup before shard merge:
  `~/.local/state/wechat-matrix-media-repair-20260925/ledger.db.pre-merge-20261003-134306`
- Consistent Synapse backup before timestamp/finalizer writes:
  `/var/mnt/ai/cache/auto-migrate/.openclaw/workspace/homeserver.db.bak-media-finalize-20261003-134456`
- Corrective WXGF merged ledger and backup:
  `~/.local/state/wechat-matrix-media-integrity-repair-20261003/ledger-merged.db`
  and
  `/var/mnt/ai/cache/auto-migrate/.openclaw/workspace/homeserver.db.bak-wxgf-finalize-20261003-211332`
- Phone evidence:
  `~/.local/state/schildichat-debug/schildichat-list-current-20261003.png`,
  `schildichat-audio-room3-20261003.png`, and
  `schildichat-audio-playing-20261003.png`; corrective image evidence:
  `schildichat-wxgf-open2.png` and `schildichat-wxgf-viewer.png`.

### Optional future recovery

- The remaining legacy WeChat attachment metadata includes `cdnattachurl`,
  `attachid`, `aeskey`, and hashes, but the URL values are legacy CDN file IDs,
  not directly downloadable public URLs. Recovery requires a valid legacy
  WeChat CDN session/auth/DNS context or reacquiring the source files from the
  phone/account.
- Do not feed these IDs to the newer iLink `/c2c/download` protocol, create new
  text fallbacks, or rewrite signed Matrix event JSON.

### Code completed before pause

- Importer can select exact placeholder IDs from a source ledger, exclude
  completed repair ledgers, shard by stable talker hash, use explicit media
  roots without scanning defaults, resolve `appattach.fileFullPath`, and fetch
  CDN stickers with MD5 validation.
- Upload timeout is `600s`; media compatibility SQLite updates retry locks.
- Finalizer supports concurrent redaction with `--workers`.
- Regression suite: `9 passed` in
  `~/.local/share/wechat-matrix-sync/tests/test_phone_media_prefetch.py`.
