# 系统全局索引（AI 冷启动必读）
> 自动生成: 2026-05-23 18:17 | 用途: AI 会话启动时读此文件即可掌握全局架构

## 一、端口地图（实时扫描）

| 端口 | 进程 |
|------|------|
| 22 | 0.0.0.0:* |
| 22 | [::]:* |
| 443 | 0.0.0.0:* |
| 443 | [::]:* |
| 1053 | users:(("mihomo",pid=2608,fd=9)) |
| 1716 | users:((".kdeconnectd-wr",pid=670310,fd=18)) |
| 2019 | users:(("caddy",pid=566681,fd=32)) |
| 2222 | *:* |
| 2223 | *:* |
| 3000 | (v1",pid=3620,fd=21)) |
| 3001 | 0.0.0.0:* |
| 3001 | [::]:* |
| 3010 | 0.0.0.0:* |
| 3389 | *:* |
| 4000 | users:(("python3.13",pid=2585,fd=6)) |
| 4001 | users:(("python3.13",pid=2455,fd=6)) |
| 4002 | 0.0.0.0:* |
| 4533 | users:(("navidrome",pid=2610,fd=11)) |
| 5037 | users:(("adb",pid=720781,fd=13)) |
| 5678 | 0.0.0.0:* |
| 5678 | [::]:* |
| 5900 | users:(("wayvnc",pid=5954,fd=11)) |
| 5998 | users:((".websockify-wra",pid=5955,fd=4)) |
| 6379 | 0.0.0.0:* |
| 7000 | *:* |
| 7500 | *:* |
| 7681 | users:(("ttyd",pid=2131,fd=13)) |
| 7690 | users:(("ttyd",pid=2783,fd=13)) |
| 7691 | users:(("ttyd",pid=2782,fd=13)) |
| 7692 | users:(("ttyd",pid=2832,fd=13)) |
| 7693 | users:(("ttyd",pid=2781,fd=13)) |
| 7694 | users:(("ttyd",pid=2830,fd=13)) |
| 7695 | users:(("ttyd",pid=2786,fd=13)) |
| 7696 | users:(("ttyd",pid=2845,fd=13)) |
| 7697 | users:(("ttyd",pid=2812,fd=13)) |
| 7698 | users:(("ttyd",pid=2998,fd=13)) |
| 7699 | users:(("caddy",pid=5893,fd=6)) |
| 7890 | users:(("mihomo",pid=2608,fd=10)) |
| 7891 | users:(("mihomo",pid=2608,fd=7)) |
| 8000 | 0.0.0.0:* |
| 8000 | [::]:* |
| 8080 | users:(("caddy",pid=566681,fd=11)) |
| 8081 | users:(("opencode",pid=519759,fd=24)) |
| 8090 | users:(("opencode",pid=2749,fd=18)) |
| 8283 | 0.0.0.0:* |
| 8283 | [::]:* |
| 8284 | users:(("python3.13",pid=2574,fd=3)) |
| 8285 | users:(("python3.13",pid=5873,fd=11)) |
| 8286 | users:(("python3.13",pid=2524,fd=3)) |
| 8384 | 0.0.0.0:* |
| 8600 | users:(("python3.13",pid=2726,fd=14)) |
| 8700 | users:(("python3.13",pid=2726,fd=7)) |
| 8701 | users:(("python3.13",pid=2483,fd=13)) |
| 9090 | *:* |
| 9091 | users:(("mihomo",pid=2608,fd=3)) |
| 9099 | users:(("python3.13",pid=4210,fd=3)) |
| 9222 | users:(("chrome",pid=6017,fd=61)) |
| 9800 | users:(("python3.13",pid=2559,fd=6)) |
| 9801 | users:(("python3.13",pid=2907,fd=6)) |
| 9810 | users:(("python3.13",pid=2629,fd=6)) |
| 9811 | users:(("python3.13",pid=2528,fd=6)) |
| 9875 | users:(("python3.13",pid=2566,fd=3)) |
| 9876 | users:(("python3.13",pid=5875,fd=3)) |
| 9890 | users:(("python3",pid=2560,fd=18)) |
| 9900 | users:(("python3.13",pid=2401,fd=6)) |
| 9922 | users:(("MainThread",pid=2557,fd=21)) |
| 9977 | users:(("python3",pid=2467,fd=3)) |
| 9979 | users:(("python3.13",pid=5872,fd=3)) |
| 9980 | users:(("python3.13",pid=2430,fd=3)) |
| 9993 | *:* |
| 9993 | 0.0.0.0:* |
| 11434 | users:((".ollama-wrapped",pid=2632,fd=3)) |
| 15555 | *:* |
| 17698 | *:* |
| 17699 | *:* |
| 17700 | *:* |
| 18090 | *:* |
| 18091 | *:* |
| 18092 | users:(("python3.13",pid=2589,fd=6)) |
| 18093 | *:* |
| 18094 | users:(("python3.13",pid=2765,fd=6)) |
| 18300 | *:* |
| 18700 | *:* |
| 19890 | *:* |
| 19891 | *:* |
| 19892 | *:* |
| 19893 | *:* |
| 20241 | users:(("cloudflared",pid=8375,fd=6)) |
| 22000 | *:* |
| 24801 | users:(("python3.13",pid=2884,fd=3)) |
| 24802 | users:(("python3.13",pid=5653,fd=3)) |
| 40544 | 0.0.0.0:* |
| 47984 | *:* |
| 47989 | *:* |
| 47990 | *:* |
| 48010 | *:* |
| 60100 | [::]:* |

## 二、目录索引（按功能域）

### ~/agi/ — AGI Brain 核心
```
android_sensor.py
audit_log.py
brain.py
browser_sense.py
cognitive_engine.py
context_graph.py
conversation.py
copywriting_collector.py
daily_summary.py
discord_bot_enhanced.py
discord_cc_push.py
doc_knowledge.py
doc_pipeline.py
email_sync.py
embedding_server.py
letta-sync.py
mac.py
macg.py
macg_api.py
macg_mcp.py
macg_tui_demo.py
mem0_bridge.py
memory_pulse_monitor.py
notify.py
op_push_service.py
proactive.py
report_generator.py
self_improve.py
sensor-bridge.py
social_relations.py
telegram-userbot.py
telegram_bot.py
telegram_bot_enhanced.py
tg_logger.py
tg_user_client.py
think.py
video_pipeline.py
wechat-learn.py
wechat_agent.py
```

### ~/hub/ — Hub API
```
Caddyfile
hub-api.py
hub-api.py.bak.202605190009
hub_config.py
office-agent.py
static
```

### ~/.local/bin/ — 运维脚本（590个，按前缀分组）

**BaiduPCS-*** (1个): `BaiduPCS-Go`
**adb-*** (3个): `adb-autoconnect.sh, adb-device-monitor.py, adb-tablet-keepalive.sh`
**agent-*** (3个): `agent-ask.py, agent-danmaku, agent-watch`
**aggregate-*** (1个): `aggregate-marketing-research.sh`
**agi-*** (2个): `agi-feedback-bus.sh, agi-persistent-monitor.sh`
**ai-*** (20个): `ai-architecture-audit, ai-brainstorm, ai-cad, ai-config-guard.sh, ai-config-watcher.sh, ai-knowledge-sync, ai-manager, ai-patrol-autofix.sh, ai-patrol-daemon.sh, ai-poll... +10更多`
**aider-*** (2个): `aider-post-commit-hook, aider-with-memory`
**apk-*** (1个): `apk-debug`
**architecture-*** (2个): `architecture-cleanup.sh, architecture-health-check`
**asset-*** (1个): `asset-watcher`
**auto-*** (6个): `auto-desktop-rules, auto-fix-services, auto-google-login, auto-login-claude, auto-update, auto_browser.py`
**backup-*** (2个): `backup-claude-config, backup-ide-configs`
**baseline-*** (1个): `baseline-update.sh`
**bash-*** (1个): `bash-wrapper`
**boot-*** (1个): `boot-recovery.sh`
**browser-*** (1个): `browser-launch-with-cookies`
**cc-*** (26个): `cc-autoagent-hook.sh, cc-autonomous-runner.sh, cc-autoskill-hook.sh, cc-behavior-audit.sh, cc-blocker-resolver.sh, cc-conversation-recorder.sh, cc-decision-engine.py, cc-decision-learner.sh, cc-desktop-image-inject.sh, cc-dialogue-broadcast.sh... +16更多`
**cct-*** (1个): `cct-tmux-wrap`
**cf-*** (2个): `cf-tunnel-7699, cf-tunnel-setup`
**change-*** (2个): `change-recorder.sh, change-watcher`
**charlie-*** (1个): `charlie-ego-record.sh`
**check-*** (3个): `check-idle-simple.sh, check-idle.sh, check-ttyd.sh`
**chroma-*** (3个): `chroma-server.py, chroma-server.sh, chroma_server.py`
**chrome-*** (6个): `chrome-fix.sh, chrome-login-backup.sh, chrome-login-restore.sh, chrome-login-watchdog.sh, chrome-stable-login-setup.sh, chrome-stable-login.sh`
**claude-*** (36个): `claude-api-autoheal.sh, claude-api-manager, claude-api-unified, claude-auto-fix, claude-auto-login, claude-cad.py, claude-dual, claude-esp, claude-failover.sh, claude-free-api-auto... +26更多`
**claudep-*** (1个): `claudep-tmux-wrap`
**clear-*** (1个): `clear-notifs`
**clip-*** (1个): `clip-sync`
**clipboard-*** (2个): `clipboard-sync-tablet, clipboard-sync-windows`
**cloudflared-*** (4个): `cloudflared-bin, cloudflared-happy, cloudflared-launcher, cloudflared-ttyd`
**code-*** (4个): `code-dual, code-indexer, code-search, code-watcher`
**config-*** (1个): `config-lock.sh`
**connectivity-*** (1个): `connectivity-chain-watchdog.sh`
**cookie-*** (1个): `cookie-watcher.py`
**crush-*** (1个): `crush-wrapper.sh`
**cursor-*** (1个): `cursor-setup-check`
**danmaku-*** (1个): `danmaku-send`
**dead-*** (1个): `dead-component-detect.sh`
**deepseek-*** (3个): `deepseek-code, deepseek-mcp-server.py, deepseek-with-context`
**desktop-*** (3个): `desktop-pet.py, desktop-stream.py, desktop-tree-overlay`
**discord-*** (4个): `discord-bot-healthcheck.sh, discord-bot-inspect.sh, discord-intelligent-bot.py, discord-roo-bridge`
**disk-*** (1个): `disk-guard.sh`
**docker-*** (3个): `docker-cleanup.sh, docker-health-nurse.sh, docker-recovery-plan`
**dotfiles-*** (2个): `dotfiles-integrity-check.sh, dotfiles-symlink-watch.sh`
**douyin-*** (1个): `douyin-web`
**download-*** (1个): `download-claude-export-from-email.py`
**dpdns-*** (1个): `dpdns-renew`
**event-*** (1个): `event_hooks_trigger.py`
**export-*** (1个): `export-claude-conversations.py`
**fcitx5-*** (1个): `fcitx5-adaptive-check`
**finance-*** (1个): `finance-reminder.sh`
**fix-*** (1个): `fix-screenshot-permission`
**floorp-*** (3个): `floorp-clean-start, floorp-popup-fix, floorp-session-cleaner.py`
**foc-*** (1个): `foc-tmux-wrap`
**force-*** (2个): `force-claude-proxy, force-claude-proxy.sh`
**four-*** (1个): `four-tool-dispatch.sh`
**frontend-*** (1个): `frontend-verify.sh`
**frp-*** (1个): `frp-watchdog.sh`
**fsearch-*** (1个): `fsearch-idle-update.sh`
**git-*** (2个): `git-backup.sh, git-codebase-update`
**github-*** (2个): `github-action-trigger, github-ai-weekly`
**google-*** (1个): `google-chrome-proxy`
**gpu-*** (1个): `gpu-mode`
**happy-*** (3个): `happy-daemon-start.sh, happy-login.sh, happy-session-watchdog.sh`
**health-*** (1个): `health-scorer`
**hermes-*** (1个): `hermes-wrapper`
**huggingface-*** (1个): `huggingface-cli`
**ibus-*** (1个): `ibus-toggle.sh`
**idea-*** (2个): `idea-2233, idea-boost.sh`
**iflytek-*** (1个): `iflytek-dict-sync`
**incident-*** (1个): `incident-reporter`
**index-*** (1个): `index-assets`
**input-*** (1个): `input-leap-server`
**install-*** (2个): `install-deepseek-aider.sh, install-roo-extensions.sh`
**ip-*** (1个): `ip-monitor-telegram`
**jetbrains-*** (1个): `jetbrains-ai-proxy`
**kde-*** (4个): `kde-logout-now, kde-open, kde-open5, kde-tray-auto-hide`
**kill-*** (1个): `kill-ghostty`
**kilo-*** (1个): `kilo-profile`
**lag-*** (1个): `lag-detector.sh`
**latest-*** (1个): `latest-img`
**launcher-*** (1个): `launcher-health-check.sh`
**letta-*** (12个): `letta-deadman-switch.sh, letta-distill, letta-health-check.sh, letta-health-guard, letta-health-monitor, letta-mcp, letta-mcp-health-check, letta-mcp-server, letta-monitor, letta-planning-trigger.sh... +2更多`
**libreoffice-*** (1个): `libreoffice-x11`
**litellm-*** (2个): `litellm-error-guard.sh, litellm-startup.sh`
**marketing-*** (1个): `marketing-web-workflow.sh`
**mcp-*** (1个): `mcp-health-check`
**media-*** (1个): `media-crawler`
**mem-*** (1个): `mem-stats`
**mem0-*** (1个): `mem0-bridge-wrapper`
**memory-*** (12个): `memory-backup, memory-bootstrap.sh, memory-cron.sh, memory-decay-engine.py, memory-dream, memory-engine, memory-episodic.py, memory-evolution-engine, memory-kg-populator.py, memory-router... +2更多`
**meta-*** (2个): `meta-cognition.py, meta-monitor.sh`
**mihomo-*** (4个): `mihomo-anthropic-check, mihomo-config-sync, mihomo-config-validate, mihomo-guardian`
**mobile-*** (1个): `mobile-entry`
**morning-*** (1个): `morning-brief.sh`
**mutual-*** (1个): `mutual-review`
**new-*** (1个): `new-api-manager`
**nix-*** (3个): `nix-store-integrity-check.sh, nix-store-nurse, nix_voice_agent.py`
**nixos-*** (14个): `nixos-ai-fix-engine, nixos-auto-commit, nixos-decision-engine, nixos-full-sync, nixos-gui-guardian, nixos-llm-analyzer, nixos-preflight-check.sh, nixos-rebuild-safe, nixos-smoketest.sh, nixos-stable-watch.sh... +4更多`
**notify-*** (3个): `notify-buf-dashboard, notify-screenshot-howto, notify-send`
**ntfs-*** (1个): `ntfs-health-check`
**numlock-*** (1个): `numlock-guard`
**oc-*** (1个): `oc-chat-watch`
**office-*** (1个): `office-agent-runner.sh`
**ollama-*** (1个): `ollama-cuda`
**op-*** (20个): `op-adaptive-gate, op-cc-bridge, op-cc-observer.sh, op-dialogue-broadcast.sh, op-dispatch, op-exec-viewer.sh, op-exec.sh, op-feed-viewer.sh, op-force.sh, op-graph... +10更多`
**opencode-*** (31个): `opencode-autoupgrade, opencode-bug-tracker.sh, opencode-config-guard.sh, opencode-continue-safe, opencode-cost-monitor, opencode-deep, opencode-dstate-watchdog, opencode-export, opencode-format-compaction, opencode-health-check.sh... +21更多`
**other-*** (60个): `PyGPT.AppImage, ai, aider, baidunetdisk, ccc, ccm, cerebras, claude-tmux-wrap.bak, cline, code... +50更多`
**otp-*** (1个): `otp-sync`
**overcode-*** (2个): `overcode-loop-watch.sh, overcode-tmux-wrap`
**overtab-*** (3个): `overtab-serve-start, overtab-serve-stop, overtab-tmux-wrap`
**panel-*** (1个): `panel-nurse`
**paperclip-*** (6个): `paperclip-aider-worker, paperclip-auto-sync, paperclip-dispatcher, paperclip-report-daemon.sh, paperclip-resolve-conflicts, paperclip-restore`
**paste-*** (1个): `paste-image-pinned`
**permission-*** (1个): `permission_check.py`
**pet-*** (1个): `pet-feeder`
**petals-*** (1个): `petals-server.sh`
**phone-*** (5个): `phone-ai-bridge.sh, phone-clip-sync, phone-control.sh, phone-screenshot, phone-tailscale-guard`
**plasmashell-*** (1个): `plasmashell-crash-guard.sh`
**playwright-*** (1个): `playwright-smart.sh`
**post-*** (1个): `post-edit-verify.sh`
**project-*** (2个): `project-context-inject, project-context-save`
**proxy-*** (6个): `proxy-403-monitor, proxy-db-init, proxy-learn, proxy-status-quick, proxy-status-widget, proxy-windows-discover`
**push-*** (2个): `push-apk, push-tunnel-url`
**python-*** (1个): `python-crash-guard.sh`
**query-*** (1个): `query-router.sh`
**quick-*** (2个): `quick-run-cmd, quick-screenshot`
**rebuild-*** (2个): `rebuild-session-notes.sh, rebuild-system-index`
**recovery-*** (1个): `recovery-manager`
**review-*** (1个): `review-op-branch`
**roo-*** (12个): `roo-apply-optimizations.sh, roo-backup-config.sh, roo-code-check, roo-digest, roo-enforce-rules, roo-export, roo-index-load.sh, roo-index-save.sh, roo-restore-config.sh, roo-state-backup... +2更多`
**rta-*** (1个): `rta-scanner`
**runbook-*** (1个): `runbook-engine`
**s-*** (1个): `s-save`
**scrcpy-*** (1个): `scrcpy-panel`
**screenshot-*** (3个): `screenshot-now, screenshot-pin, screenshot-watcher.sh`
**selflearn-*** (1个): `selflearn-health-check.sh`
**service-*** (3个): `service-config-guard, service-panel.sh, service-zombie-cleaner.sh`
**session-*** (6个): `session-archive-cleanup.sh, session-archiver.sh, session-embedder-wrapper.sh, session-embedder.py, session-rag-server.py, session-switch`
**setup-*** (2个): `setup-0011, setup-letta-telegram-alert`
**sisy-*** (1个): `sisy-tmux-wrap`
**skill-*** (1个): `skill-auto-extract.py`
**smart-*** (4个): `smart-ip, smart-memory-classifier, smart-router.py, smart-search`
**smoke-*** (1个): `smoke-test.sh`
**sqlite-*** (2个): `sqlite_web, sqlite_wsgi`
**ssh-*** (1个): `ssh-win`
**start-*** (5个): `start-chromadb, start-desktop-pet.sh, start-hyprland-fixed, start-session-rag-server.sh, start-wechat`
**switch-*** (1个): `switch-claude-provider.sh`
**sync-*** (8个): `sync-all-browser-cookies, sync-claude-export-to-letta, sync-cookies-to-chrome, sync-md-to-letta, sync-memory-to-ntfs, sync-session-to-letta, sync-session-to-letta-v1-backup, sync-to-obsidian`
**sys-*** (1个): `sys-info-mcp.py`
**system-*** (4个): `system-call-check, system-healer, system-health-check, system-sentry-check.sh`
**systemd-*** (1个): `systemd-orphan-guard.sh`
**tablet-*** (1个): `tablet-adb-watch`
**task-*** (1个): `task-complete`
**terminal-*** (1个): `terminal-pet`
**test-*** (2个): `test-claude-knowledge, test-opencode-modes`
**tg-*** (6个): `tg-bot-tasks, tg-command, tg-copy-listener.py, tg-push, tg-saved-reader, tg-screenshot`
**tiny-*** (1个): `tiny-agents`
**todo-*** (1个): `todo_sync.py`
**ttyd-*** (1个): `ttyd-quick-check`
**ui-*** (1个): `ui-verify-chain.sh`
**ulwh-*** (1个): `ulwh-tmux-wrap`
**unified-*** (1个): `unified-monitor.sh`
**update-*** (1个): `update-api-quota.sh`
**upload-*** (1个): `upload-cookies-to-server`
**vastai-*** (2个): `vastai-auto-list.sh, vastai-setup.sh`
**verify-*** (5个): `verify-banner, verify-check, verify-chromadb-letta, verify-pipeline.sh, verify-stats`
**version-*** (1个): `version-check`
**voice-*** (3个): `voice-input, voice-push, voice-test`
**vpn-*** (1个): `vpn-watchdog`
**wan-*** (1个): `wan-ip-monitor.sh`
**warp-*** (10个): `warp-auto, warp-auto-fold, warp-claude-attach, warp-claude-auto, warp-claude-launch, warp-dual-view, warp-launch-claude, warp-multi, warp-session, warp-split-now`
**waybar-*** (21个): `waybar-adb.sh, waybar-agent.sh, waybar-api-quota.sh, waybar-chroma.sh, waybar-clipsync.sh, waybar-disk.sh, waybar-dispatch.sh, waybar-frp.sh, waybar-guardian.py, waybar-health-menu.sh... +11更多`
**wayland-*** (1个): `wayland-screenshot`
**web-*** (2个): `web-ai-proxy, web-ai-proxy-wrapper`
**wechat-*** (14个): `wechat-android-backup.sh, wechat-contact-sync.py, wechat-finance, wechat-kanban-push.sh, wechat-live-monitor.py, wechat-merge.py, wechat-msg-sync-wrapper.sh, wechat-msg-sync.py, wechat-reply-consumer.py, wechat-send.sh... +4更多`
**weekly-*** (1个): `weekly-error-review`
**whisper-*** (1个): `whisper-stt-server`
**wifi-*** (1个): `wifi-monitor.sh`
**win-*** (3个): `win-deploy, win-deploy-on-wifi.sh, win-exec`
**wine-*** (1个): `wine-wechat`
**wol-*** (1个): `wol-windows.sh`
**wx-*** (1个): `wx-memory-extract.py`
**xdg-*** (2个): `xdg-open, xdg-open-guard`
**ydotool-*** (1个): `ydotool-bridge.py`
**yt-*** (1个): `yt-dlp`
**zeditor-*** (1个): `zeditor-nvidia`

### /mnt/ai/apps/ — 应用数据
```
123pan
QtScrcpy-x86_64.AppImage
agi-control-plane
aider-venv
alist
android-sdk
baidunetdisk
cc-op-graph
comfyui
content-creator
content-router
crm
embed-server
embed-venv
gelab-zero
gmail-bridge
hub-mobile
image-search
kanban-tui
latentsync
launcher
mcp-shared-memory
mem0
mem0-data
mem0-venv
migration
musetalk
musetalk-models
nginx
ollama
onlyoffice
openagents
sadtalker
wav2lip
web-ai-proxy
wechat-agent
wechat-backup
yourmemory-venv
```

### ~/.config/opencode/agents/ — Agent 定义
```
agi-mentor
cc-autonomous
charlie-ego
content-creator
cost-accountant
discord-butler
doc-manager
finance
git-backup
marketing-auditor
marketing-coordinator
memory-curator
ops-dispatcher
planner
proxy-guardian
reviewer
security-watchdog
service-nurse
sisyphus
tech-architect
tech-researcher
```

### ~/.claude/skills/ — Skills
共 128 个 skill 目录

### memory/ — 记忆系统
```
MEMORY.md
NIXOS-AI-GUARD.md
SYSTEM-INDEX.md
ai-cluster-architecture.md
ai-tools.md
app-dev-journal.md
cc-decision-engine-setup.md
cc-diagnostic-engine-optimized.md
cc-op-delegate-necessity.md
cc-queue.md
codebase-map.md
command-reference.md
compaction-output-format.md
data-recovery-deployment.md
feedback_ai_tools_search_first.md
feedback_hyprland_configerrors.md
feedback_phone_operations.md
feedback_waybar-management.md
frp-public-access.md
ideas-roadmap.md
infra-reference.md
lessons-learned-7699.md
lessons-learned-archive.md
lessons-learned-backup-20260518.md
lessons-learned.md
litellm-deployment.md
litellm-startup-diagnosis.md
nixos-config.md
north-star.md
obsidian-sync-guide.md
op-agent-system.md
op-review-report.md
op-tasks-archive-2026-05.md
op-tasks-archive-202604.md
op-tasks-archive-20260423.md
op-tasks-archive-202605.md
op-tasks-archive.md
op-tasks.md
opencode-architecture-audit.md
opencode-audit-2026-05-17.md
opencode-cost-optimization.md
opencode-health.md
opencode-letta-sync.md
opencode-memory-analysis.md
opencode-session-log.md
opencode-upgrade-1.15.3.md
package-watchlist.md
pending-tasks.md
router-padavan-backup.md
rules-secondary.md
session-notes.md
setup-plan.md
trade-workflow-architecture.md
troubleshooting.md
wechat-merge-plan.md
```

## 三、systemd 用户服务（446个注册，95个运行中）

### 当前运行中
```
adb-device-monitor
agent-orchestrator
agi-brain
agi-frontend
agi-gateway
agi-telegram-bot
ai-rules-sync
ai-watchdog
caddy-launcher
caddy-opencode-proxy
cf-tunnel-7699
change-watcher
chrome-cdp
chronos-sensory
claude-esp
claude-tablet-output
claude-token-tray
clip-sync
clipboard-sync-tablet
code-watcher
content-router
cookie-sync-server
crewai-gateway
crewai-openagents-bridge
dbus
disk-watchdog
dotfiles-symlink-watch
earlyoom
embedding-server
finance-agent
frpc
gcr-ssh-agent
headless-browser
hub-api
image-search
launcher
letta-mcp
litellm-strip-proxy
macg-mcp
mem0-bridge
memory-evolution
mihomo
mihomo-watch
navidrome
nix-voice-agent
numlock-guard
oa-crewai-bridge
office-agent
ollama
op-tasks-watcher
op-watchdog
openagents
openagents-network
opencode-config-guard
opencode-intent-detector
opencode-memwatch
opencode-stuck-watch
opencode-web
opencode-web-sisy
otp-sync
overcode-loop-watch
phone-clip-sync
pipewire
pipewire-pulse
proxy-403-monitor
python-crash-guard
screenshot-watcher
speech-dispatcher
sunshine
sys-info-mcp
tablet-control-panel
telegram-userbot
ttyd-aider
ttyd-cct
ttyd-claude
ttyd-claudep
ttyd-foc
ttyd-macg
ttyd-opencode
ttyd-overtab
ttyd-ulwh
voxtype
waybar
waybar-guardian
wayland-session-bindpid@3309
wayland-wm@hyprland\x2duwsm.desktop
wechat-agent
wechat-crm-archiver
wechat-reply-consumer
wireplumber
xdg-desktop-portal
xdg-document-portal
xdg-permission-store
ydotool-bridge
ydotoold
```

## 四、定时任务（119个 timer）
```
agi-cognitive-engine
agi-daily-report
agi-evolve
agi-feedback-bus
agi-self-improve
agi-wechat-learn
ai-architecture-audit
ai-config-sync-pull
ai-rules-sync-windows
ai-scheduler
auto-fix-services
backup-cleanup
cc-autonomous-runner
cc-op-verifier
cc-task-auditor
cf-url-notify
check-ttyd
chrome-login-backup
chrome-login-watchdog
chronos-subconscious
claude-orphan-killer
code-indexer
connectivity-chain-watchdog
copywriting-collector
daily-summary
discord-bot-healthcheck
disk-cleanup
disk-guard
disk-sentinel
disk-space-monitor
docker-cleanup
docker-health-nurse
docker-prune
dotfiles-integrity-check
dotfiles-push
dpdns-renew
duckdns
finance-reminder
frp-watchdog
git-backup
github-ai-weekly
gmail-reply-monitor
gmail-watch
happy-session-watchdog
health-check
health-scorer
iflytek-dict-sync
image-captioner
incident-reporter
integrity-check
letta-deadman-switch
letta-health-check
letta-health-guard
letta-health-monitor
letta-planning
letta-sync
litellm-error-guard
maintenance-learner
memory-backup
memory-curator
memory-decay-engine
memory-engine-sync
memory-engine-ttl
memory-injector
memory-kg-populator
memory-pulse-monitor
memory-tg-daily
meta-cognition
mihomo-backup
mihomo-guardian
mihomo-health
mihomo-sync
morning-brief
nix-store-check
nixos-auto-commit
nixos-full-sync
nixos-stable-watch
nixos-test-notify
ntfs-health-check
ocr-indexer
op-lock-watchdog
op-precheck
op-self-upgrade
op-tasks-archive
opencode-autoupgrade
opencode-bug-tracker
opencode-dstate-watchdog
opencode-health-monitor
opencode-job-charlie-b445f233ebb8-aider-refactor
opencode-job-charlie-b445f233ebb8-codebase-mapper
opencode-job-charlie-b445f233ebb8-cost-accountant
opencode-job-charlie-b445f233ebb8-security-watchdog
opencode-session-guard
plocate-update
push-tunnel-url
rebuild-session-notes
rebuild-system-index
runbook-engine
selflearn-check
service-config-guard
sync-images
sync-memory-ntfs
sync-obsidian
system-health-monitor
systemd-orphan-guard
systemd-reexec
systemd-tmpfiles-clean
task-review-weekly
wan-ip-monitor
waybar-guardian
wechat-backup
wechat-backup-reminder
wechat-contact-sync
wechat-live-monitor
wechat-msg-sync
wechat-version-guard
win-deploy
wol-windows
workspace-scheduler
```

## 五、故障快速定位

| 症状 | 先检查 | 常见原因 |
|------|--------|---------|
| Telegram 不通知 | `curl --proxy 7890 api.telegram.org` | mihomo 节点挂了 |
| AI 调用失败 | `curl localhost:4000/health` | LiteLLM 挂/Key 过期 |
| 记忆丢失 | `curl localhost:8283/v1/agents` | Letta DB 超时 |
| 微信断连 | `ssh G@192.168.2.36` | Windows bridge 挂了 |
| 代理不通 | `curl localhost:9091/proxies` | mihomo 坏节点 |
| ADB 断连 | `adb devices` | WiFi ADB 需重连 |
| 磁盘满 | `df -h / /mnt/ai` | Nix store / Docker |
| 服务挂 | `systemctl --user status <svc>` | 查 Result 字段 |
