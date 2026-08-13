# Mobile IME / Keyboard Design Reference

## Required checks

- System IME switcher: Android normally provides a system button for switching IMEs. Do not assume it can be removed. If a custom switcher is used, make it opt-in or follow platform callback behavior.
- Bottom safe area: reserve bottom padding/spacer for navigation bar, gesture handle, ColorOS/OEM keyboard switcher, and floating affordances. Make this user-configurable.
- Candidate bar: keep it above keys; avoid causing app resize churn by repeatedly changing height unless necessary.
- Settings access: provide a launcher/settings Activity and an IME settings entry; in-keyboard settings key should be optional.
- Avoid duplicate controls: if the OS already shows an IME switcher, hide internal `⌨` by default.
- Touch targets: bottom-row utility keys are high-risk; keep adequate size and avoid placing near system gesture edges.
- Device verification: verify on the real phone path with ADB screenshot/focus/package checks.

## FlexIME local decisions

- Package: `com.yourname.flexime`
- IME: `com.yourname.flexime/.ime.FlexImeService`
- Settings: `com.yourname.flexime/.settings.SettingsActivity`
- Default style: `iflytek_light`
- Default bottom safe-area spacer: `34dp`
- Internal `⌨` key default: off, because ColorOS/Android can show its own switcher near the bottom edge.
- Modes:
  - Normal: Chinese-first daily input, iFlytek/Baidu/Sogou-style defaults.
  - Programmer: CodeBoard/Unexpected Keyboard-inspired symbols, cursor, copy/paste, compact dark theme.
  - Game: low-height, low-obstruction, no toolbar by default, larger bottom safe area.

## Local installed IME strengths to reuse

- Baidu OPPO / Sogou / iFlytek: Chinese candidate quality, 9-key/full-key, discoverable settings.
- Gboard / FUTO Keyboard: privacy-conscious local behavior, multilingual/ascii-capable layouts, inline suggestions where supported.
- FUTO Voice Input / Dictus: voice-first and dictation mode should be a future plug-in, not mixed into core typing.
- CodeBoard / Unexpected Keyboard / AnySoftKeyboard: programmer symbols, cursor/navigation, compact configurable layouts.
- KDE Connect remote keyboard / ToDesk: remote-control text path; future mode should avoid interfering with remote sessions.
- KeePass Magikeyboard / Tasker keyboard / OPlus security keyboard: special-purpose secure/automation keyboards should stay narrow and explicit.

## Common pitfalls

- Placing `⌫`, Enter, space, language switch, or settings keys at the bottom-right without reserving system switcher/navigation space.
- Relying on desktop/emulator screenshots; OEM Android IME chrome often differs.
- Hiding candidate bar by changing total IME height aggressively; it can feel jumpy.
- Adding settings but not exposing the exact constants that vary by phone.
- Treating a vendor keyboard's visual style as enough; behavior, safety zones, and settings discoverability matter more.
