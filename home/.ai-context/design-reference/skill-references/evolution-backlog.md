# Design Evolution Backlog

## Active

- 2026-07-19 FlexIME: Android/ColorOS system IME switcher overlaps bottom-row keys.
  - Baseline: reserve bottom safe area; internal `⌨` off by default.
  - Implemented: `bottomSafeInsetDp` default `34`, settings slider `0..64`, docs/runbook update.
  - Next: verify by phone screenshot while editing text; tune default to phone if 34dp is insufficient.

- 2026-07-19 Design reference system: make future UI/product design tasks auto-reference standards.
  - Implemented: `~/.codex/skills/design-reference` with references and subscriptions.
  - Next: add domain references when repeated patterns appear: mobile workbench, WebTTY, dashboards, settings screens.

## Rule for adding items

Add an item when a design task reveals a reusable pitfall, device-specific workaround, industry-reference mapping, component pattern, or user preference. Keep entries short and actionable.
