# 系统全局索引（AI 冷启动必读）
> 自动生成: 2026-05-03 21:57 | 用途: AI 会话启动时读此文件即可掌握全局架构

## 一、端口地图（实时扫描）

| 端口 | 进程 |
|------|------|
| 22 | 0.0.0.0:* |
| 22 | [::]:* |
| 443 | 0.0.0.0:* |
| 443 | [::]:* |
| 1053 | *:* |
| 3000 | (v1",pid=38536,fd=22)) |
| 3001 | 0.0.0.0:* |
| 3001 | [::]:* |
| 4000 | 0.0.0.0:* |
| 4533 | users:(("navidrome",pid=1751,fd=9)) |
| 5037 | users:(("adb",pid=688933,fd=11)) |
| 5244 | 0.0.0.0:* |
| 5244 | [::]:* |
| 5678 | 0.0.0.0:* |
| 5678 | [::]:* |
| 5900 | users:(("wayvnc",pid=1241373,fd=10)) |
| 5997 | users:(("python3.13",pid=1097419,fd=3)) |
| 5998 | users:((".websockify-wra",pid=1240113,fd=3)) |
| 6379 | 0.0.0.0:* |
| 7681 | users:(("ttyd",pid=1486,fd=13)) |
| 7690 | users:(("ttyd",pid=1848,fd=13)) |
| 7691 | users:(("ttyd",pid=1844,fd=13)) |
| 7693 | users:(("ttyd",pid=1843,fd=13)) |
| 7694 | users:(("ttyd",pid=1852,fd=13)) |
| 7699 | users:(("caddy",pid=1136090,fd=4)) |
| 7890 | *:* |
| 7891 | *:* |
| 8000 | 0.0.0.0:* |
| 8000 | [::]:* |
| 8001 | 0.0.0.0:* |
| 8001 | [::]:* |
| 8080 | users:(("opencode",pid=3730,fd=19)) |
| 8283 | 0.0.0.0:* |
| 8283 | [::]:* |
| 8284 | 0.0.0.0:* |
| 8284 | [::]:* |
| 8384 | 0.0.0.0:* |
| 8788 | users:(("python3.13",pid=1743,fd=3)) |
| 8789 | users:(("python3.13",pid=1723,fd=3)) |
| 9090 | *:* |
| 9091 | 0.0.0.0:* |
| 9099 | users:(("python3.13",pid=11348,fd=3)) |
| 9222 | users:(("chrome",pid=636883,fd=76)) |
| 9800 | users:(("python3.13",pid=1729,fd=6)) |
| 9801 | users:(("python3.13",pid=10038,fd=6)) |
| 9810 | users:(("python3.13",pid=1759,fd=6)) |
| 9875 | users:(("python3.13",pid=1739,fd=3)) |
| 9876 | users:(("python3.13",pid=17327,fd=3)) |
| 9880 | 0.0.0.0:* |
| 9880 | [::]:* |
| 9900 | users:(("python3.13",pid=22521,fd=13)) |
| 9922 | users:(("node",pid=1491406,fd=21)) |
| 9977 | users:(("python3",pid=1663,fd=3)) |
| 9980 | users:(("python3.13",pid=1640,fd=3)) |
| 22000 | *:* |
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
letta-sync.py
mac.py
macg.py
macg_api.py
macg_mcp.py
macg_tui_demo.py
op_push_service.py
proactive.py
report_generator.py
self_improve.py
sensor-bridge.py
social_relations.py
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
office-agent.py
static
```

### ~/.local/bin/ — 运维脚本（418个，按前缀分组）

**adb-*** (2个): `adb-autoconnect.sh, adb-tablet-keepalive.sh`
**agent-*** (3个): `agent-ask.py, agent-danmaku, agent-watch`
**agi-*** (2个): `agi-feedback-bus.sh, agi-persistent-monitor.sh`
**ai-*** (13个): `ai-architecture-audit, ai-cad, ai-config-guard.sh, ai-config-watcher.sh, ai-knowledge-sync, ai-manager, ai-patrol-autofix.sh, ai-patrol-daemon.sh, ai-rules-sync.sh, ai-rules-watch.sh... +3更多`
**aider-*** (2个): `aider-post-commit-hook, aider-with-memory`
**apk-*** (1个): `apk-debug`
**architecture-*** (2个): `architecture-cleanup.sh, architecture-health-check`
**asset-*** (1个): `asset-watcher`
**auto-*** (6个): `auto-desktop-rules, auto-fix-services, auto-google-login, auto-login-claude, auto-update, auto_browser.py`
**backup-*** (2个): `backup-claude-config, backup-ide-configs`
**baseline-*** (1个): `baseline-update.sh`
**boot-*** (1个): `boot-recovery.sh`
**browser-*** (1个): `browser-launch-with-cookies`
**cc-*** (23个): `cc-autoagent-hook.sh, cc-autonomous-runner.sh, cc-autoskill-hook.sh, cc-behavior-audit.sh, cc-blocker-resolver.sh, cc-conversation-recorder.sh, cc-decision-learner.sh, cc-desktop-image-inject.sh, cc-dialogue-broadcast.sh, cc-discord-push... +13更多`
**cct-*** (1个): `cct-tmux-wrap`
**charlie-*** (1个): `charlie-ego-record.sh`
**check-*** (2个): `check-idle-simple.sh, check-idle.sh`
**claude-*** (36个): `claude-api-autoheal.sh, claude-api-manager, claude-api-unified, claude-auto-fix, claude-auto-login, claude-cad.py, claude-dual, claude-esp, claude-failover.sh, claude-free-api-auto... +26更多`
**clip-*** (1个): `clip-sync`
**clipboard-*** (1个): `clipboard-sync-tablet`
**cloudflared-*** (3个): `cloudflared-bin, cloudflared-happy, cloudflared-ttyd`
**code-*** (1个): `code-dual`
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
**export-*** (1个): `export-claude-conversations.py`
**fcitx5-*** (1个): `fcitx5-adaptive-check`
**finance-*** (1个): `finance-reminder.sh`
**fix-*** (1个): `fix-screenshot-permission`
**floorp-*** (3个): `floorp-clean-start, floorp-popup-fix, floorp-session-cleaner.py`
**four-*** (1个): `four-tool-dispatch.sh`
**fsearch-*** (1个): `fsearch-idle-update.sh`
**git-*** (1个): `git-backup.sh`
**github-*** (1个): `github-ai-weekly`
**glm-*** (6个): `glm-enhanced, glm-float, glm-monitor, glm-proxy, glm-task, glm-watch`
**gpu-*** (1个): `gpu-mode`
**happy-*** (3个): `happy-daemon-start.sh, happy-login.sh, happy-session-watchdog.sh`
**hermes-*** (1个): `hermes-wrapper`
**huggingface-*** (1个): `huggingface-cli`
**idea-*** (2个): `idea-2233, idea-boost.sh`
**iflytek-*** (1个): `iflytek-dict-sync`
**index-*** (1个): `index-assets`
**input-*** (1个): `input-leap-server`
**install-*** (2个): `install-deepseek-aider.sh, install-roo-extensions.sh`
**jetbrains-*** (1个): `jetbrains-ai-proxy`
**kde-*** (4个): `kde-logout-now, kde-open, kde-open5, kde-tray-auto-hide`
**kill-*** (1个): `kill-ghostty`
**lag-*** (1个): `lag-detector.sh`
**latest-*** (1个): `latest-img`
**letta-*** (6个): `letta-distill, letta-health-guard, letta-health-monitor, letta-mcp, letta-monitor, letta-planning-trigger.sh`
**libreoffice-*** (1个): `libreoffice-x11`
**litellm-*** (2个): `litellm-error-guard.sh, litellm-startup.sh`
**marketing-*** (1个): `marketing-web-workflow.sh`
**mcp-*** (1个): `mcp-health-check`
**media-*** (1个): `media-crawler`
**mem-*** (1个): `mem-stats`
**memory-*** (4个): `memory-backup, memory-decay-engine.py, memory-dream, memory-evolution-engine`
**meta-*** (1个): `meta-monitor.sh`
**mihomo-*** (2个): `mihomo-config-validate, mihomo-guardian`
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
**op-*** (18个): `op-adaptive-gate, op-cc-bridge, op-cc-observer.sh, op-dialogue-broadcast.sh, op-exec-viewer.sh, op-exec.sh, op-feed-viewer.sh, op-force.sh, op-graph, op-launch.sh... +8更多`
**opencode-*** (7个): `opencode-autoupgrade, opencode-config-guard.sh, opencode-memwatch.sh, opencode-run-agent.sh, opencode-session, opencode-stuck-watch.sh, opencode-tmux-wrap`
**other-*** (50个): `PyGPT.AppImage, ai, aider, ccc, ccm, cerebras, claude-tmux-wrap.bak, cline, code, consensus.sh... +40更多`
**otp-*** (1个): `otp-sync`
**panel-*** (1个): `panel-nurse`
**paperclip-*** (6个): `paperclip-aider-worker, paperclip-auto-sync, paperclip-dispatcher, paperclip-report-daemon.sh, paperclip-resolve-conflicts, paperclip-restore`
**paste-*** (1个): `paste-image-pinned`
**pet-*** (1个): `pet-feeder`
**petals-*** (1个): `petals-server.sh`
**phone-*** (4个): `phone-ai-bridge.sh, phone-control.sh, phone-screenshot, phone-tailscale-guard`
**plasmashell-*** (1个): `plasmashell-crash-guard.sh`
**post-*** (1个): `post-edit-verify.sh`
**proxy-*** (6个): `proxy-403-monitor, proxy-db-init, proxy-learn, proxy-status-quick, proxy-status-widget, proxy-windows-discover`
**push-*** (2个): `push-apk, push-tunnel-url`
**python-*** (1个): `python-crash-guard.sh`
**quick-*** (2个): `quick-run-cmd, quick-screenshot`
**rebuild-*** (1个): `rebuild-system-index`
**review-*** (1个): `review-op-branch`
**roo-*** (12个): `roo-apply-optimizations.sh, roo-backup-config.sh, roo-code-check, roo-digest, roo-enforce-rules, roo-export, roo-index-load.sh, roo-index-save.sh, roo-restore-config.sh, roo-state-backup... +2更多`
**rta-*** (1个): `rta-scanner`
**s-*** (1个): `s-save`
**scrcpy-*** (1个): `scrcpy-panel`
**screenshot-*** (3个): `screenshot-now, screenshot-pin, screenshot-watcher.sh`
**selflearn-*** (1个): `selflearn-health-check.sh`
**service-*** (1个): `service-zombie-cleaner.sh`
**setup-*** (2个): `setup-0011, setup-letta-telegram-alert`
**smart-*** (4个): `smart-ip, smart-memory-classifier, smart-router.py, smart-search`
**sqlite-*** (2个): `sqlite_web, sqlite_wsgi`
**start-*** (2个): `start-desktop-pet.sh, start-wechat`
**switch-*** (1个): `switch-claude-provider.sh`
**sync-*** (8个): `sync-all-browser-cookies, sync-claude-export-to-letta, sync-cookies-to-chrome, sync-md-to-letta, sync-memory-to-ntfs, sync-session-to-letta, sync-session-to-letta-v1-backup, sync-to-obsidian`
**system-*** (4个): `system-call-check, system-healer, system-health-check, system-sentry-check.sh`
**tablet-*** (1个): `tablet-adb-watch`
**task-*** (1个): `task-complete`
**terminal-*** (1个): `terminal-pet`
**test-*** (5个): `test-ai-models.sh, test-letta-memory-system, test-windsurf-knowledge-mcp, test-windsurf-router, test-windsurf-smart-router`
**tg-*** (5个): `tg-bot-tasks, tg-command, tg-push, tg-saved-reader, tg-screenshot`
**tiny-*** (1个): `tiny-agents`
**todo-*** (1个): `todo_sync.py`
**unified-*** (1个): `unified-monitor.sh`
**upload-*** (1个): `upload-cookies-to-server`
**vastai-*** (2个): `vastai-auto-list.sh, vastai-setup.sh`
**verify-*** (1个): `verify-chromadb-letta`
**version-*** (1个): `version-check`
**voice-*** (3个): `voice-input, voice-push, voice-test`
**vpn-*** (1个): `vpn-watchdog`
**warp-*** (10个): `warp-auto, warp-auto-fold, warp-claude-attach, warp-claude-auto, warp-claude-launch, warp-dual-view, warp-launch-claude, warp-multi, warp-session, warp-split-now`
**wayland-*** (1个): `wayland-screenshot`
**wechat-*** (14个): `wechat-android-backup.sh, wechat-contact-sync.py, wechat-finance, wechat-kanban-push.sh, wechat-live-monitor.py, wechat-merge.py, wechat-msg-sync-wrapper.sh, wechat-msg-sync.py, wechat-reply-consumer.py, wechat-send.sh... +4更多`
**weekly-*** (1个): `weekly-error-review`
**whisper-*** (1个): `whisper-stt-server`
**win-*** (2个): `win-deploy, win-exec`
**windsurf-*** (5个): `windsurf-konsole-sidebar, windsurf-mcp-summary, windsurf-realtime-summary, windsurf-sidebar, windsurf-with-sidebar`
**wine-*** (1个): `wine-wechat`
**wol-*** (1个): `wol-windows.sh`
**wx-*** (1个): `wx-memory-extract.py`
**xdg-*** (2个): `xdg-open, xdg-open-guard`
**yt-*** (1个): `yt-dlp`
**zeditor-*** (1个): `zeditor-nvidia`

### /mnt/ai/apps/ — 应用数据
```
QtScrcpy-x86_64.AppImage
agi-control-plane
android-sdk
cc-op-graph
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
musetalk
musetalk-models
nginx
ollama
onlyoffice
sadtalker
wav2lip
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
共 147 个 skill 目录

### memory/ — 记忆系统
```
MEMORY.md
SYSTEM-INDEX.md
ai-cluster-architecture.md
ai-tools.md
app-dev-journal.md
cc-queue.md
cline-api-integration-analysis.md
codebase-map.md
command-reference.md
feedback_architecture_continuity.md
feedback_entry_point.md
feedback_phone_operations.md
ideas-roadmap.md
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
op-tasks.md
pending-tasks.md
setup-plan.md
trade-workflow-architecture.md
troubleshooting.md
wechat-merge-plan.md
weekly-error-review-2026-W14.md
weekly-error-review-2026-W15.md
```

## 三、systemd 用户服务（350个注册，64个运行中）

### 当前运行中
```
agent-orchestrator
agi-brain
agi-frontend
agi-gateway
agi-telegram-bot
ai-rules-sync
at-spi-dbus-bus
caddy-launcher
chrome-cdp
chronos-biofeedback
chronos-sensory
claude-esp
claude-md-sync
claude-token-tray
cloudflared-happy
cookie-sync-server
dbus
dotfiles-symlink-watch
fcitx5
freeze-detector
gcr-ssh-agent
glm-monitor
headless-browser
hub-api
kunifiedpush-distributor
launcher
letta-mcp
memory-evolution
mihomo-watch
navidrome
numlock-guard
office-agent
op-push
op-tasks-watcher
op-watchdog
opencode-memwatch
opencode-stuck-watch
opencode-web
otp-sync
paperclip-report-daemon
phone-ai-bridge
pipewire
pipewire-pulse
proxy-403-monitor
python-crash-guard
screenshot-watcher
sunshine
swayidle
tablet-adb-watch
tablet-control-panel
ttyd-aider
ttyd-cct
ttyd-claude
ttyd-macg
voxtype
vpn-watchdog
wechat-agent
wechat-crm-archiver
wechat-reply-consumer
wireplumber
xdg-desktop-portal
xdg-document-portal
xdg-permission-store
ydotoold
```

## 四、定时任务（94个 timer）
```
adb-tablet-keepalive
agi-cognitive-engine
agi-daily-report
agi-feedback-bus
agi-self-improve
agi-wechat-learn
ai-architecture-audit
ai-config-guard
ai-scheduler
auto-fix-services
backup-cleanup
cc-autonomous-runner
cc-op-verifier
cc-task-auditor
cc-task-runner
chronos-subconscious
claude-orphan-killer
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
fcitx5-adaptive-check
finance-reminder
git-backup
github-ai-weekly
happy-session-watchdog
health-check
iflytek-dict-sync
image-captioner
lag-detector
letta-distill
letta-health-check
letta-health-guard
letta-health-monitor
letta-planning
letta-sync
litellm-error-guard
maintenance-learner
memory-backup
memory-curator
mihomo-backup
mihomo-guardian
morning-brief
nix-store-check
nixos-auto-commit
nixos-full-sync
nixos-stable-watch
nixos-test-notify
ntfs-health-check
ocr-indexer
op-connection-guard
op-lock-watchdog
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
opencode-job-charlie-b445f233ebb8-marketing-scan
opencode-job-charlie-b445f233ebb8-memory-maintain
opencode-job-charlie-b445f233ebb8-proxy-guardian
opencode-job-charlie-b445f233ebb8-security-watchdog
phone-tailscale-guard
push-tunnel-url
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
