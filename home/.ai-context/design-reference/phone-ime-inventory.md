# PKR110 Phone IME Inventory and Reuse Notes

Snapshot: 2026-07-19. Source: `ime list -s`, `cmd input_method dump`, and package dumps via `adb-record`.

## Enabled / relevant IMEs

- `com.baidu.input_oppo/.ImeService` — Baidu OPPO custom IME, v8.5.302.578.
  - Reuse: strong Chinese daily input, 9-key/full-key, handwriting-ready, OEM-safe settings.
- `com.iflytek.inputmethod.oem/com.iflytek.inputmethod.FlyIME` — iFlytek clean/OEM IME, v8.1.8448.
  - Reuse: clean light visual style, simple Chinese-first layout, large rounded keys.
- `com.sohu.inputmethod.sogouoem/.SogouIME` — Sogou OEM, v10.32.
  - Reuse: Chinese phrase/candidate depth, handwriting support, settings discoverability.
- `com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME` — Gboard, v17.7.
  - Reuse: multilingual/ascii-capable layout, inline suggestion support, strong system integration.
- `org.futo.inputmethod.latin.playstore/org.futo.inputmethod.latin.LatinIME` — FUTO Keyboard, v0.1.29.1.
  - Reuse: privacy/local-first product stance, configurable modern keyboard baseline.
- `org.futo.voiceinput/.VoiceInputMethodService` — FUTO Voice Input, v1.3.7-1.
  - Reuse: future voice/dictation plug-in; keep separate from core typing.
- `com.gazlaws.codeboard/.CodeBoardIME` — CodeBoard, v6.0.3.
  - Reuse: programmer mode, symbols, brackets, cursor/navigation, copy/paste shortcuts.
- `com.menny.android.anysoftkeyboard/.SoftKeyboard` — AnySoftKeyboard, v1.13.547.
  - Reuse: open/configurable keyboard patterns, language packs and compact layouts.
- `juloo.keyboard2/.Keyboard2` — Unexpected Keyboard / Keyboard2, v2.0.4.
  - Reuse: programmer/terminal-friendly compact symbol access.
- `cc.flypy.input/PangIME.Android.InputService` — 小鹤/飞扬类输入法, v3.26.1.2601.
  - Reuse: future double-pinyin / flypy mode.
- `org.kde.kdeconnect_tp/...RemoteKeyboardService` — KDE Connect Remote Keyboard.
  - Reuse: remote-control text path; avoid breaking remote session use.
- `dev.pivisolutions.dictus/.ime.DictusImeService` — Dictus.
  - Reuse: dictation mode ideas.
- `com.kunzisoft.keepass.libre/...MagikeyboardService` — KeePass secure keyboard.
  - Reuse: explicit secure mode; narrow scoped secret entry.
- `net.dinglisch.android.taskerm/...InputMethodServiceTasker` — Tasker keyboard.
  - Reuse: automation/action keyboard ideas.
- `youqu.android.todesk/...PinyinIME` — ToDesk remote IME.
  - Reuse: remote desktop text entry compatibility.

## FlexIME product modes

- Normal: learn from Baidu/iFlytek/Sogou. Chinese-first, clean light style, 9-key default, candidate priority, easy settings.
- Programmer: learn from CodeBoard/Unexpected/AnySoftKeyboard. Code layout, symbols, cursor, copy/paste, compact dark theme.
- Game: low obstruction. Compact height, no toolbar by default, larger bottom safe area, minimal vibration/sound.
- Future: Voice, Secure, Remote, Double Pinyin/Flypy modes.
