# FlexIME Android IME

Purpose: local MVP Android input method build/install workflow for the PKR110 phone.

## Source and package

- Source: `~/flexime-mvp`
- Package: `com.yourname.flexime`
- IME service: `com.yourname.flexime/.ime.FlexImeService`
- Settings activity: `com.yourname.flexime/.settings.SettingsActivity`
- Web APK directory: `~/.local/share/phone-agent-web/flexime/`
- Build/install record: `~/.local/state/flexime/builds.jsonl`
- P2P sync/AI service: `flexime-sync-ai.service`
- P2P sync/AI URL: `http://100.87.238.153:19978`
- Desktop sync state: `~/.local/state/flexime-sync/config.json`

## Default operation

When the user asks to use Goose/Step Router for build work, delegate the build
to Goose and do not run Gradle directly from Codex. Goose is already configured
with LiteLLM `step-router-v1` in `~/.config/goose/config.yaml`.

Default delegated build/install command:

```bash
cd ~/flexime-mvp
GOOSE_TELEMETRY_ENABLED=false goose run --no-session --max-turns 8 --text \
  '只调用一次 shell 工具执行：cd /var/home/charlie/flexime-mvp && ./goose-full-build.sh 100.87.37.3:5555。不要 tree，不要 read，等待脚本完成后用中文总结输出。'
```

Inside Goose, use the deterministic installer instead of manual Gradle/ADB steps:

```bash
cd ~/flexime-mvp
./install-to-phone.sh
```

Behavior:

1. Builds debug APK with local JDK/Gradle.
2. Auto-selects connected `model:PKR110` when no serial is provided.
3. Copies a versioned APK plus `FlexIME-latest-debug.apk` to the phone-agent web directory.
4. Appends build/install JSONL records.
5. Installs via root `pm install`, enables and selects FlexIME.
6. Sends a best-effort ntfy `actions` notification with the APK URL.

## Current tracked version

```text
versionName = 9423264
versionCode = 2026071911
```

## Verify

```bash
~/.local/bin/adb-record --tag flexime-verify -- -s 100.87.37.3:5555 shell \
  'printf "default="; settings get secure default_input_method; dumpsys package com.yourname.flexime | grep -E "versionCode|versionName|lastUpdateTime" | head -n 6'
tail -n 4 ~/.local/state/flexime/builds.jsonl
ls -lh ~/.local/share/phone-agent-web/flexime/FlexIME-latest-debug.apk
```

Expected default IME:

```text
com.yourname.flexime/.ime.FlexImeService
```

## Settings

Open settings from the launcher, Android IME settings, the top toolbar
`FlexIME`/`⚙`, or the bottom-row `⚙` key. The internal `⌨` key calls Android's
input method picker, but it is disabled by default because Android/ColorOS may
already show a system input-method switcher near the keyboard bottom edge.

Current default preset is `iflytek_light`: light gray panel, white rounded keys,
blue accent, top mode toolbar, persistent candidate/voice strip, configurable
candidate/key sizing, and a default `34dp` bottom safe-area spacer to avoid the
Android/ColorOS system input-method switcher overlapping the keyboard's bottom
row.

## Baidu / iFlytek reference rule

- Do not compile, decompile, or clone closed-source vendor IMEs.
- Use black-box screenshots and behavior on PKR110 as the reference source.
- Current clean screenshots:
  - `~/.local/state/flexime/ime-clean/baidu.png`
  - `~/.local/state/flexime/ime-clean/iflytek.png`
  - `~/.local/state/flexime/ime-clean/flexime-1910c.png`
- `2026071910` changed normal 9-key toward Baidu/iFlytek:
  - left quick-command strip: `/new`, `/model`, `/status`
  - right action column: delete, `重输`, `0`
  - bottom row: `模式`, `页`, `符`, wide `空格/麦`, `中/英`, blue `确定`
  - toolbar: mode/page/AI/voice/clipboard/cursor/collapse/settings
  - renderer supports per-key styles: `normal`, `command`, `utility`, `side`, `primary`
- `2026071911` completed the first P2P/learning loop:
  - all settings fields are included in config sync, not only mode/theme/bottom-safe
  - `/v1/lexicon` is pulled into `SimplePinyinEngine` before rendering candidates
  - committed candidates push both input history and pinyin/candidate lexicon
  - toolbar adds `史` for P2P history candidates
  - desktop bridge default config now contains every synced UI/behavior field

## P2P sync and Step AI

Desktop bridge:

```bash
systemctl --user status flexime-sync-ai.service
curl --noproxy '*' -fsS http://127.0.0.1:19978/health
curl --noproxy '*' -fsS -X POST http://127.0.0.1:19978/v1/ai/candidates \
  -H 'Content-Type: application/json' \
  --data '{"text":"nihao flexime","modeId":"normal"}'
```

Phone route:

```bash
~/.local/bin/adb-record --tag flexime-sync-verify -- -s 100.87.37.3:5555 shell \
  'toybox wget -q -O - http://100.87.238.153:19978/health 2>/dev/null || curl -sS --max-time 5 http://100.87.238.153:19978/health'
```

Design:

- Phone APK talks to desktop over NetBird P2P: `100.87.238.153:19978`.
- Desktop service calls local LiteLLM `step-3.7-flash`; model secrets stay on desktop, not in the APK.
- If Step returns an empty response, the bridge returns a local fallback so the APK `AI` button never shows an empty candidate list.
- Settings page exposes sync enable, AI enable, sync URL, Step model, upload, and pull.
- Keyboard home toolbar exposes `AI`; it sends composing text or recent text to the desktop bridge and renders returned candidates.
- P2P also covers lexicon, input history, and clipboard:
  - `GET/POST /v1/lexicon`
  - `GET/POST /v1/history`
  - `GET/POST /v1/clipboard`
  - Keyboard home `剪贴` pulls desktop P2P clipboard into candidates.
  - Keyboard home `史` pulls desktop P2P input history into candidates.
  - Chinese candidate generation merges desktop/user lexicon before built-in MVP phrases.

## Latest Goose full-build evidence

On 2026-07-19 Goose with `step-router-v1` ran `/tmp/flexime-goose-build.sh`,
now promoted to project script `~/flexime-mvp/goose-full-build.sh`:

- JDK: `/var/home/charlie/.local/share/jdks/jdk-21`, `javac 21.0.11`
- Full build: `gradle clean assembleDebug`, `34 actionable tasks: 34 executed`
- Install target: `100.87.37.3:5555`
- Installed default IME: `com.yourname.flexime/.ime.FlexImeService`
- Installed version: `versionCode=2026071911`, `versionName=9423264`
- Latest APK SHA256: `8bb8fd730a322013b8abd4ecd6e0dbca0d3c243afbc9cb7fc7ab2c1311d75702`
- Known warning: Gradle 8.14 reports deprecated Gradle features; not blocking now, but fix before Gradle 9.
