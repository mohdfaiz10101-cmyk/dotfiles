# Pending Tasks

## SchildiChat WeChat media repair (paused 2026-09-25 08:25 CST)

Status: paused at user request. No repair worker or finalizer is running.

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

### Verified checkpoint

- Successful unique native-media replacement events: `4091`.
- Replacement types: `2350` images, `1235` audio, `143` video,
  `267` files, and `96` sticker/image events.
- Remaining text-media rows: `3952`.
- Already cached and recoverable next run: `2470`:
  `1508` stickers, `534` images, `403` audio, `17` videos, `8` files.
- Currently unavailable: `1482`:
  `497` videos, `539` files, `442` images, `4` stickers.
- Shards `0,1,3,4,5,7` reached `batch_done`. Shards `2` and `6` were
  interrupted during retry, but their committed rows are safe in their ledgers.
- Original text placeholders have NOT yet been redacted. Replacement events
  have NOT yet received the final timestamp pass. The phone can therefore show
  duplicates/import-time items until finalization is completed.
- No Synapse ratelimit override is active. `@charlie` admin remained/restored
  to `0` after the attempted admin call was rejected.

### Resume procedure

1. Run repair shards `0..7` again, preferably two at a time. For each shard,
   use the same `--repair-shard-count 8 --repair-shard-index N`, and exclude
   both `ledger.db` and that shard's `ledger-shard-N.db`. Use both explicit
   roots `phone-full-repair` and `phone-attachment-repair`. The importer adds
   the CDN emoji cache automatically. Keep `--skip-text-fallback`,
   `--txn-prefix wechat_media_repair_20260925_`, and the stable repair DB.
2. Merge all non-text rows from `ledger-shard-0.db` through
   `ledger-shard-7.db` into the main repair `ledger.db` by `wechat_msg_id`.
3. Run:
   `wechat-matrix-fix-event-timestamps --ledger-path ~/.local/state/wechat-matrix-media-repair-20260925/ledger.db`
4. Run:
   `wechat-matrix-media-repair-finalize --replacement-ledger ~/.local/state/wechat-matrix-media-repair-20260925/ledger.db --original-ledger ~/.local/state/wechat-matrix-ledger/ledger.db --workers 8`
5. Trigger SchildiChat's in-app initial sync, then verify on the phone that
   media controls render and the old text placeholders are gone.
6. Audit the remaining unavailable `1482` rows. Their next recovery path is
   parsing WeChat image/video/app-attachment CDN metadata; do not create new
   text fallbacks or directly rewrite signed Matrix event JSON.

### Code completed before pause

- Importer can select exact placeholder IDs from a source ledger, exclude
  completed repair ledgers, shard by stable talker hash, use explicit media
  roots without scanning defaults, resolve `appattach.fileFullPath`, and fetch
  CDN stickers with MD5 validation.
- Upload timeout is `600s`; media compatibility SQLite updates retry locks.
- Finalizer supports concurrent redaction with `--workers`.
- Regression suite: `9 passed` in
  `~/.local/share/wechat-matrix-sync/tests/test_phone_media_prefetch.py`.
