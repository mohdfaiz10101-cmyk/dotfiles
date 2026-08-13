# Design Evolution Backlog

## Active

- 2026-07-19 FlexIME: Android/ColorOS system IME switcher overlaps bottom-row keys.
  - Baseline: reserve bottom safe area; internal `⌨` off by default.
  - Implemented: `bottomSafeInsetDp` default `34`, settings slider `0..64`, docs/runbook update.
  - Next: verify by phone screenshot while editing text; tune default to phone if 34dp is insufficient.

- 2026-07-19 Design reference system: make future UI/product design tasks auto-reference standards.
  - Implemented: `~/.codex/skills/design-reference` with references and subscriptions.
  - Next: add domain references when repeated patterns appear: mobile workbench, WebTTY, dashboards, settings screens.

- 2026-07-19 FlexIME: not enough compared with installed phone IMEs; Chinese input has candidate/commit issues; needs mode switching.
  - Baseline: learn from all enabled/installed IMEs on PKR110: Baidu, iFlytek, Sogou, Gboard, FUTO, CodeBoard, AnySoftKeyboard, Unexpected, Flypy, KDE remote, Dictus, KeePass, Tasker, ToDesk.
  - Implemented: Normal / Programmer / Game modes, Chinese priority candidate map, composing cleanup, IME reference library update.
  - Next: add real RIME/Fcitx5 dictionary bridge or import a larger offline phrase table; add screenshot-based comparison with each IME.

## Rule for adding items

Add an item when a design task reveals a reusable pitfall, device-specific workaround, industry-reference mapping, component pattern, or user preference. Keep entries short and actionable.
