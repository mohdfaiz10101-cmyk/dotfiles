# Core Design Standards

## Default checklist

- Reference first: official platform docs, design-system docs, then observed local device behavior.
- Safe areas: layout must account for system bars, navigation bars, gesture areas, display cutouts, floating system controls, desktop captions, and vendor overlays.
- Touch: primary controls should keep at least 48dp target size; if visual size is smaller, hit target must remain large.
- Density: prefer 4dp/8dp spacing rhythm; keep compact settings user-adjustable.
- Accessibility: labels, contrast, text size, reachable controls, no gesture-only critical action.
- Settings: expose volatile device-specific layout constants, such as bottom inset, keyboard height, spacing, haptics, and toolbar toggles.
- Verification: check the real target device/surface, not only emulator/desktop screenshots.

## Source priority

1. Official platform docs: Android Developers, Material Design, Apple HIG.
2. Product-specific references: user-provided screenshots, installed app behavior, local runbooks.
3. Industry examples: common production apps, only as visual inspiration, not as API truth.
4. Local evolution backlog: known device bugs and user preferences.
