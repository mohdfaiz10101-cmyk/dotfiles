# 系统全局索引（AI 冷启动必读）
> 自动生成: 2026-05-12 12:17 | 用途: AI 会话启动时读此文件即可掌握全局架构

## 一、端口地图（实时扫描）

| 端口 | 进程 |
|------|------|
| 22 | 0.0.0.0:* |
| 22 | [::]:* |
| 443 | 0.0.0.0:* |
| 443 | [::]:* |
| 1053 | users:(("mihomo",pid=1697,fd=9)) |
| 1080 | users:(("ssh",pid=972750,fd=4)) |
| 1080 | users:(("ssh",pid=972750,fd=5)) |
| 3000 | (v1",pid=6822,fd=22)) |
| 4000 | users:(("python3.13",pid=1692,fd=6)) |
| 4001 | users:(("python3.13",pid=1608,fd=6)) |
| 4002 | 0.0.0.0:* |
| 4533 | users:(("navidrome",pid=1708,fd=9)) |
| 5001 | users:(("python3.13",pid=1836,fd=13)) |
| 5037 | users:(("adb",pid=2664,fd=11)) |
| 5900 | users:(("wayvnc",pid=3329,fd=11)) |
| 5998 | users:((".websockify-wra",pid=3330,fd=4)) |
| 6379 | 0.0.0.0:* |
| 7000 | *:* |
| 7500 | *:* |
| 7681 | users:(("ttyd",pid=2083,fd=13)) |
| 7690 | users:(("ttyd",pid=1807,fd=13)) |
| 7691 | users:(("ttyd",pid=1800,fd=13)) |
| 7692 | users:(("ttyd",pid=1829,fd=13)) |
| 7693 | users:(("ttyd",pid=1790,fd=13)) |
| 7694 | users:(("ttyd",pid=1826,fd=13)) |
| 7695 | users:(("ttyd",pid=1811,fd=13)) |
| 7696 | users:(("ttyd",pid=1834,fd=13)) |
| 7697 | users:(("ttyd",pid=1817,fd=13)) |
| 7699 | users:(("caddy",pid=3943,fd=6)) |
| 7700 | users:(("ttyd",pid=1832,fd=13)) |
| 7890 | users:(("mihomo",pid=1697,fd=11)) |
| 7891 | users:(("mihomo",pid=1697,fd=7)) |
| 8080 | users:(("opencode",pid=2347,fd=18)) |
| 8090 | users:(("opencode",pid=197868,fd=19)) |
| 8284 | users:(("python3.13",pid=934301,fd=3)) |
| 8286 | users:(("python3.13",pid=4078,fd=3)) |
| 8384 | 0.0.0.0:* |
| 8787 | users:(("python3.13",pid=3919,fd=3)) |
| 8789 | users:(("python3.13",pid=1669,fd=3)) |
| 9090 | *:* |
| 9091 | users:(("mihomo",pid=1697,fd=3)) |
| 9099 | users:(("python3.13",pid=5612,fd=3)) |
| 9222 | users:(("chrome",pid=2367,fd=62)) |
| 9800 | users:(("python3.13",pid=1676,fd=6)) |
| 9801 | users:(("python3.13",pid=1865,fd=6)) |
| 9810 | users:(("python3.13",pid=1716,fd=6)) |
| 9811 | users:(("python3.13",pid=1656,fd=13)) |
| 9875 | users:(("python3.13",pid=1681,fd=3)) |
| 9876 | users:(("python3.13",pid=3930,fd=3)) |
| 9900 | users:(("python3.13",pid=1570,fd=13)) |
| 9910 | users:(("python3.13",pid=1693,fd=14)) |
| 9922 | users:(("node",pid=1671,fd=21)) |
| 9977 | users:(("python3",pid=1613,fd=3)) |
| 9979 | users:(("python3.13",pid=3909,fd=3)) |
| 9980 | users:(("python3.13",pid=1580,fd=3)) |
| 9993 | *:* |
| 9993 | 0.0.0.0:* |
| 20241 | users:(("cloudflared",pid=42847,fd=6)) |
| 22000 | *:* |
| 24801 | users:(("python3.13",pid=3335,fd=4)) |
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
discord-bot.py
discord_bot_enhanced.py
discord_cc_push.py
doc_knowledge.py
doc_pipeline.py
email_sync.py
embedding_server.py
event_hooks.py
letta-sync.py
mac.py
macg.py
macg_api.py
macg_mcp.py
macg_tui_demo.py
mem0_bridge.py
multi_project_manager.py
op_push_service.py
permission_guard.py
proactive.py
report_generator.py
self_improve.py
sensor-bridge.py
social_relations.py
telegram-api-client.py
telegram-direct-client.py
telegram-login.py
telegram-userbot.py
telegram_bot.py
telegram_bot_enhanced.py
telegram_bridge.py
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
office-agent.py
static
```

### ~/.local/bin/ — 运维脚本（491个，按前缀分组）

**adb-*** (2个): `adb-autoconnect.sh, adb-tablet-keepalive.sh`
**agent-*** (3个): `agent-ask.py, agent-danmaku, agent-watch`
**aggregate-*** (1个): `aggregate-marketing-research.sh`
**agi-*** (2个): `agi-feedback-bus.sh, agi-persistent-monitor.sh`
**ai-*** (19个): `ai-architecture-audit, ai-brainstorm, ai-cad, ai-config-guard.sh, ai-config-watcher.sh, ai-knowledge-sync, ai-manager, ai-patrol-autofix.sh, ai-patrol-daemon.sh, ai-poll... +9更多`
**aider-*** (2个): `aider-post-commit-hook, aider-with-memory`
**apk-*** (1个): `apk-debug`
**architecture-*** (2个): `architecture-cleanup.sh, architecture-health-check`
**asset-*** (1个): `asset-watcher`
**auto-*** (6个): `auto-desktop-rules, auto-fix-services, auto-google-login, auto-login-claude, auto-update, auto_browser.py`
**backup-*** (2个): `backup-claude-config, backup-ide-configs`
**baseline-*** (1个): `baseline-update.sh`
**boot-*** (1个): `boot-recovery.sh`
**browser-*** (1个): `browser-launch-with-cookies`
**cc-*** (25个): `cc-autoagent-hook.sh, cc-autonomous-runner.sh, cc-autoskill-hook.sh, cc-behavior-audit.sh, cc-blocker-resolver.sh, cc-conversation-recorder.sh, cc-decision-learner.sh, cc-desktop-image-inject.sh, cc-dialogue-broadcast.sh, cc-discord-push... +15更多`
**cct-*** (1个): `cct-tmux-wrap`
**cf-*** (1个): `cf-tunnel-7699`
**charlie-*** (1个): `charlie-ego-record.sh`
**check-*** (3个): `check-idle-simple.sh, check-idle.sh, check-ttyd.sh`
**chrome-*** (2个): `chrome-stable-login-setup.sh, chrome-stable-login.sh`
**claude-*** (36个): `claude-api-autoheal.sh, claude-api-manager, claude-api-unified, claude-auto-fix, claude-auto-login, claude-cad.py, claude-dual, claude-esp, claude-failover.sh, claude-free-api-auto... +26更多`
**claudep-*** (1个): `claudep-tmux-wrap`
**clip-*** (1个): `clip-sync`
**clipboard-*** (2个): `clipboard-sync-tablet, clipboard-sync-windows`
**cloudflared-*** (4个): `cloudflared-bin, cloudflared-happy, cloudflared-launcher, cloudflared-ttyd`
**code-*** (4个): `code-dual, code-indexer, code-search, code-watcher`
**cookie-*** (1个): `cookie-watcher.py`
**crush-*** (1个): `crush-wrapper.sh`
**cursor-*** (1个): `cursor-setup-check`
**danmaku-*** (1个): `danmaku-send`
**deepseek-*** (3个): `deepseek-code, deepseek-mcp-server.py, deepseek-with-context`
**desktop-*** (3个): `desktop-pet.py, desktop-stream.py, desktop-tree-overlay`
**discord-*** (4个): `discord-bot-healthcheck.sh, discord-bot-inspect.sh, discord-intelligent-bot.py, discord-roo-bridge`
**disk-*** (1个): `disk-guard.sh`
**docker-*** (3个): `docker-cleanup.sh, docker-health-nurse.sh, docker-recovery-plan`
**dotfiles-*** (2个): `dotfiles-integrity-check.sh, dotfiles-symlink-watch.sh`
**douyin-*** (1个): `douyin-web`
**download-*** (1个): `download-claude-export-from-email.py`
**event-*** (1个): `event_hooks_trigger.py`
**export-*** (1个): `export-claude-conversations.py`
**fcitx5-*** (1个): `fcitx5-adaptive-check`
**finance-*** (1个): `finance-reminder.sh`
**fix-*** (1个): `fix-screenshot-permission`
**floorp-*** (3个): `floorp-clean-start, floorp-popup-fix, floorp-session-cleaner.py`
**foc-*** (1个): `foc-tmux-wrap`
**force-*** (1个): `force-claude-proxy`
**four-*** (1个): `four-tool-dispatch.sh`
**fsearch-*** (1个): `fsearch-idle-update.sh`
**git-*** (2个): `git-backup.sh, git-codebase-update`
**github-*** (2个): `github-action-trigger, github-ai-weekly`
**glm-*** (6个): `glm-enhanced, glm-float, glm-monitor, glm-proxy, glm-task, glm-watch`
**google-*** (1个): `google-chrome-proxy`
**gpu-*** (1个): `gpu-mode`
**happy-*** (3个): `happy-daemon-start.sh, happy-login.sh, happy-session-watchdog.sh`
**hermes-*** (1个): `hermes-wrapper`
**huggingface-*** (1个): `huggingface-cli`
**idea-*** (2个): `idea-2233, idea-boost.sh`
**iflytek-*** (1个): `iflytek-dict-sync`
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
**letta-*** (10个): `letta-distill, letta-health-guard, letta-health-monitor, letta-mcp, letta-mcp-health-check, letta-mcp-server, letta-monitor, letta-planning-trigger.sh, letta-precheck.py, letta-selfheal`
**libreoffice-*** (1个): `libreoffice-x11`
**litellm-*** (2个): `litellm-error-guard.sh, litellm-startup.sh`
**marketing-*** (1个): `marketing-web-workflow.sh`
**mcp-*** (1个): `mcp-health-check`
**media-*** (1个): `media-crawler`
**mem-*** (1个): `mem-stats`
**memory-*** (10个): `memory-backup, memory-bootstrap.sh, memory-decay-engine.py, memory-dream, memory-episodic.py, memory-evolution-engine, memory-kg-populator.py, memory-router, memory-tg-push.sh, memory-working-decay.py`
**meta-*** (2个): `meta-cognition.py, meta-monitor.sh`
**mihomo-*** (4个): `mihomo-anthropic-check, mihomo-config-sync, mihomo-config-validate, mihomo-guardian`
**mobile-*** (1个): `mobile-entry`
**morning-*** (1个): `morning-brief.sh`
**mutual-*** (1个): `mutual-review`
**new-*** (1个): `new-api-manager`
**nix-*** (2个): `nix-store-integrity-check.sh, nix-store-nurse`
**nixos-*** (6个): `nixos-auto-commit, nixos-full-sync, nixos-preflight-check.sh, nixos-rebuild-safe, nixos-smoketest.sh, nixos-stable-watch.sh`
**notify-*** (3个): `notify-buf-dashboard, notify-screenshot-howto, notify-send`
**ntfs-*** (1个): `ntfs-health-check`
**numlock-*** (1个): `numlock-guard`
**oc-*** (1个): `oc-chat-watch`
**office-*** (1个): `office-agent-runner.sh`
**op-*** (19个): `op-adaptive-gate, op-cc-bridge, op-cc-observer.sh, op-dialogue-broadcast.sh, op-exec-viewer.sh, op-exec.sh, op-feed-viewer.sh, op-force.sh, op-graph, op-launch.sh... +9更多`
**opencode-*** (21个): `opencode-autoupgrade, opencode-config-guard.sh, opencode-cost-monitor, opencode-deep, opencode-format-compaction, opencode-integrity-check, opencode-intent-detector, opencode-letta-sync, opencode-memwatch.sh, opencode-normal... +11更多`
**other-*** (55个): `PyGPT.AppImage, ai, aider, ccc, ccm, cerebras, claude-tmux-wrap.bak, cline, code, consensus.sh... +45更多`
**otp-*** (1个): `otp-sync`
**overcode-*** (2个): `overcode-loop-watch.sh, overcode-tmux-wrap`
**overtab-*** (1个): `overtab-tmux-wrap`
**panel-*** (1个): `panel-nurse`
**paperclip-*** (6个): `paperclip-aider-worker, paperclip-auto-sync, paperclip-dispatcher, paperclip-report-daemon.sh, paperclip-resolve-conflicts, paperclip-restore`
**paste-*** (1个): `paste-image-pinned`
**permission-*** (1个): `permission_check.py`
**pet-*** (1个): `pet-feeder`
**petals-*** (1个): `petals-server.sh`
**phone-*** (4个): `phone-ai-bridge.sh, phone-control.sh, phone-screenshot, phone-tailscale-guard`
**plasmashell-*** (1个): `plasmashell-crash-guard.sh`
**post-*** (1个): `post-edit-verify.sh`
**project-*** (2个): `project-context-inject, project-context-save`
**proxy-*** (6个): `proxy-403-monitor, proxy-db-init, proxy-learn, proxy-status-quick, proxy-status-widget, proxy-windows-discover`
**push-*** (2个): `push-apk, push-tunnel-url`
**python-*** (1个): `python-crash-guard.sh`
**query-*** (1个): `query-router.sh`
**quick-*** (2个): `quick-run-cmd, quick-screenshot`
**rebuild-*** (1个): `rebuild-system-index`
**recovery-*** (1个): `recovery-manager`
**review-*** (1个): `review-op-branch`
**roo-*** (12个): `roo-apply-optimizations.sh, roo-backup-config.sh, roo-code-check, roo-digest, roo-enforce-rules, roo-export, roo-index-load.sh, roo-index-save.sh, roo-restore-config.sh, roo-state-backup... +2更多`
**rta-*** (1个): `rta-scanner`
**s-*** (1个): `s-save`
**scrcpy-*** (1个): `scrcpy-panel`
**screenshot-*** (3个): `screenshot-now, screenshot-pin, screenshot-watcher.sh`
**selflearn-*** (1个): `selflearn-health-check.sh`
**service-*** (1个): `service-zombie-cleaner.sh`
**session-*** (4个): `session-embedder-wrapper.sh, session-embedder.py, session-rag-server.py, session-switch`
**setup-*** (2个): `setup-0011, setup-letta-telegram-alert`
**sisy-*** (1个): `sisy-tmux-wrap`
**skill-*** (1个): `skill-auto-extract.py`
**smart-*** (4个): `smart-ip, smart-memory-classifier, smart-router.py, smart-search`
**sqlite-*** (2个): `sqlite_web, sqlite_wsgi`
**start-*** (3个): `start-desktop-pet.sh, start-session-rag-server.sh, start-wechat`
**switch-*** (1个): `switch-claude-provider.sh`
**sync-*** (8个): `sync-all-browser-cookies, sync-claude-export-to-letta, sync-cookies-to-chrome, sync-md-to-letta, sync-memory-to-ntfs, sync-session-to-letta, sync-session-to-letta-v1-backup, sync-to-obsidian`
**system-*** (4个): `system-call-check, system-healer, system-health-check, system-sentry-check.sh`
**tablet-*** (1个): `tablet-adb-watch`
**task-*** (1个): `task-complete`
**terminal-*** (1个): `terminal-pet`
**test-*** (1个): `test-opencode-modes`
**tg-*** (5个): `tg-bot-tasks, tg-command, tg-push, tg-saved-reader, tg-screenshot`
**tiny-*** (1个): `tiny-agents`
**todo-*** (1个): `todo_sync.py`
**ttyd-*** (1个): `ttyd-quick-check`
**ulwh-*** (1个): `ulwh-tmux-wrap`
**unified-*** (1个): `unified-monitor.sh`
**upload-*** (1个): `upload-cookies-to-server`
**vastai-*** (2个): `vastai-auto-list.sh, vastai-setup.sh`
**verify-*** (1个): `verify-chromadb-letta`
**version-*** (1个): `version-check`
**voice-*** (3个): `voice-input, voice-push, voice-test`
**vpn-*** (1个): `vpn-watchdog`
**warp-*** (10个): `warp-auto, warp-auto-fold, warp-claude-attach, warp-claude-auto, warp-claude-launch, warp-dual-view, warp-launch-claude, warp-multi, warp-session, warp-split-now`
**waybar-*** (1个): `waybar-wifi.sh`
**wayland-*** (1个): `wayland-screenshot`
**web-*** (2个): `web-ai-proxy, web-ai-proxy-wrapper`
**wechat-*** (14个): `wechat-android-backup.sh, wechat-contact-sync.py, wechat-finance, wechat-kanban-push.sh, wechat-live-monitor.py, wechat-merge.py, wechat-msg-sync-wrapper.sh, wechat-msg-sync.py, wechat-reply-consumer.py, wechat-send.sh... +4更多`
**weekly-*** (1个): `weekly-error-review`
**whisper-*** (1个): `whisper-stt-server`
**win-*** (2个): `win-deploy, win-exec`
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
cc-op-graph
comfyui
content-creator
content-router
crm
embed-server
embed-venv
hub-mobile
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
共 129 个 skill 目录

### memory/ — 记忆系统
```
MEMORY.md
SYSTEM-INDEX.md
ai-cluster-architecture.md
ai-tools.md
app-dev-journal.md
cc-queue.md
codebase-map.md
command-reference.md
compaction-output-format.md
data-recovery-deployment.md
feedback_phone_operations.md
ideas-roadmap.md
lessons-learned-7699.md
lessons-learned-archive.md
lessons-learned.md
litellm-deployment.md
litellm-startup-diagnosis.md
nixos-config.md
north-star.md
obsidian-sync-guide.md
op-agent-system.md
op-review-report.md
op-tasks-archive-202604.md
op-tasks-archive-20260423.md
op-tasks-archive-202605.md
op-tasks.md
opencode-architecture-audit.md
opencode-cost-optimization.md
opencode-letta-sync.md
opencode-memory-analysis.md
opencode-session-log.md
pending-tasks.md
rules-secondary.md
setup-plan.md
trade-workflow-architecture.md
troubleshooting.md
wechat-merge-plan.md
```

## 三、systemd 用户服务（410个注册，90个运行中）

### 当前运行中
```
agent-orchestrator
agi-brain
agi-frontend
agi-gateway
ai-rules-sync
ai-watchdog
at-spi-dbus-bus
caddy-launcher
cf-tunnel-7699
chrome-cdp
chronos-biofeedback
chronos-sensory
claude-esp
claude-md-sync
claude-tablet-output
claude-token-tray
clip-sync
clipboard-sync-tablet
clipboard-sync-windows
code-watcher
content-router
cookie-sync-server
dbus
dotfiles-symlink-watch
embedding-server
fcitx5
finance-agent
freeze-detector
frpc
gcr-ssh-agent
github-action-trigger
glm-monitor
glm-proxy
headless-browser
hub-api
kunifiedpush-distributor
launcher
letta-mcp
litellm-strip-proxy
macg-api
memory-evolution
mihomo
mihomo-watch
navidrome
numlock-guard
office-agent
op-push
op-tasks-watcher
op-watchdog
opencode-intent-detector
opencode-letta-sync
opencode-memwatch
opencode-stuck-watch
opencode-telegram-processor
opencode-web
opencode-web-sisy
otp-sync
overcode-loop-watch
paperclip-report-daemon
phone-socks-tunnel
pipewire
pipewire-pulse
proxy-403-monitor
python-crash-guard
screenshot-watcher
ssh-winpc-tunnel
sunshine
tablet-control-panel
telegram-userbot
ttyd-aider
ttyd-cct
ttyd-claude
ttyd-claudep
ttyd-foc
ttyd-macg
ttyd-overcode
ttyd-overtab
ttyd-ulwh
voxtype
waybar
web-ai-proxy
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

## 四、定时任务（104个 timer）
```
aggregate-marketing-research
agi-cognitive-engine
agi-daily-report
agi-feedback-bus
agi-self-improve
agi-wechat-learn
ai-architecture-audit
ai-rules-sync-windows
ai-scheduler
auto-fix-services
backup-cleanup
baidu-123-migration
cc-autonomous-runner
cc-op-verifier
cc-task-auditor
cc-task-runner
cf-url-notify
check-ttyd
chronos-subconscious
claude-orphan-killer
code-indexer
copywriting-collector
daily-summary
discord-bot-healthcheck
disk-cleanup
disk-sentinel
disk-space-monitor
docker-cleanup
docker-health-nurse
docker-prune
dotfiles-integrity-check
dotfiles-push
drkonqi-coredump-cleanup
drkonqi-sentry-postman
finance-reminder
git-backup
github-ai-weekly
happy-session-watchdog
health-check
iflytek-dict-sync
image-captioner
lag-detector
letta-health-check
letta-health-guard
letta-health-monitor
letta-mcp-health-check
letta-selfheal
letta-sync
litellm-error-guard
maintenance-learner
memory-backup
memory-curator
memory-decay-engine
memory-kg-populator
memory-tg-daily
memory-working-decay
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
op-task-runner
op-tasks-archive
opencode-autoupgrade
opencode-config-guard
opencode-job-charlie-b445f233ebb8-aider-refactor
opencode-job-charlie-b445f233ebb8-codebase-mapper
opencode-job-charlie-b445f233ebb8-cost-accountant
opencode-job-charlie-b445f233ebb8-discord-butler
opencode-job-charlie-b445f233ebb8-glm-knowledge-writer
opencode-job-charlie-b445f233ebb8-heartbeat-marketing-scan
opencode-job-charlie-b445f233ebb8-heartbeat-memory-maintain
opencode-job-charlie-b445f233ebb8-heartbeat-system-sentry
opencode-job-charlie-b445f233ebb8-letta-selfheal-hourly
opencode-job-charlie-b445f233ebb8-proxy-guardian
opencode-job-charlie-b445f233ebb8-security-watchdog
opencode-sisyphus-guard
push-tunnel-url
rebuild-system-index
recoll-idle-index
selflearn-check
sync-memory-ntfs
sync-obsidian
system-health-monitor
systemd-tmpfiles-clean
task-review-weekly
wechat-backup
wechat-backup-reminder
wechat-contact-sync
wechat-live-monitor
wechat-msg-sync
wechat-version-guard
wol-windows
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
