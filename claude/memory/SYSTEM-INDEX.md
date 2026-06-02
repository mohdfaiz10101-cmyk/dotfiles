# 系统全局索引（AI 冷启动必读）
> 自动生成: 2026-06-02 18:17 | 用途: AI 会话启动时读此文件即可掌握全局架构

## 一、端口地图（实时扫描）

| 端口 | 进程 |
|------|------|
| 22 | 0.0.0.0:* |
| 22 | [::]:* |
| 80 | *:* |
| 443 | 0.0.0.0:* |
| 443 | [::]:* |
| 1053 | *:* |
| 1716 | users:((".kdeconnectd-wr",pid=135204,fd=17)) |
| 2019 | 0.0.0.0:* |
| 2222 | *:* |
| 2223 | *:* |
| 3000 | (v1",pid=130047,fd=21)) |
| 3389 | *:* |
| 4000 | users:(("python3.13",pid=127567,fd=6)) |
| 4001 | users:(("python3.13",pid=128286,fd=6)) |
| 4002 | 0.0.0.0:* |
| 4096 | users:(("opencode",pid=128453,fd=18)) |
| 4533 | users:(("navidrome",pid=128296,fd=9)) |
| 5037 | users:(("adb",pid=127358,fd=12)) |
| 5174 | users:(("MainThread",pid=138764,fd=21)) |
| 5900 | users:(("wayvnc",pid=131484,fd=15)) |
| 5998 | users:((".websockify-wra",pid=131485,fd=8)) |
| 6379 | 0.0.0.0:* |
| 7000 | *:* |
| 7500 | *:* |
| 7681 | users:(("ttyd",pid=2050,fd=13)) |
| 7689 | users:(("ttyd",pid=128677,fd=13)) |
| 7690 | users:(("ttyd",pid=128672,fd=13)) |
| 7691 | users:(("ttyd",pid=128627,fd=13)) |
| 7692 | users:(("ttyd",pid=128651,fd=13)) |
| 7693 | users:(("ttyd",pid=128648,fd=13)) |
| 7694 | users:(("ttyd",pid=128641,fd=13)) |
| 7695 | users:(("ttyd",pid=128676,fd=13)) |
| 7696 | users:(("ttyd",pid=128719,fd=13)) |
| 7697 | users:(("ttyd",pid=128657,fd=13)) |
| 7698 | users:(("ttyd",pid=128818,fd=13)) |
| 7699 | users:(("caddy",pid=128284,fd=7)) |
| 7700 | users:(("ttyd",pid=128652,fd=13)) |
| 7890 | *:* |
| 7891 | *:* |
| 8000 | users:((".uvicorn-wrappe",pid=127344,fd=6)) |
| 8022 | *:* |
| 8080 | users:(("ttyd",pid=128644,fd=13)) |
| 8081 | users:(("opencode",pid=128305,fd=18)) |
| 8082 | users:(("python3.13",pid=128385,fd=3)) |
| 8088 | users:(("python3.13",pid=128316,fd=3)) |
| 8201 | users:(("python3",pid=127470,fd=7)) |
| 8283 | 0.0.0.0:* |
| 8283 | [::]:* |
| 8284 | users:(("python3.13",pid=127562,fd=3)) |
| 8285 | users:(("python3.13",pid=128370,fd=11)) |
| 8286 | users:(("python3.13",pid=128288,fd=3)) |
| 8384 | 0.0.0.0:* |
| 8600 | users:(("python3.13",pid=128299,fd=14)) |
| 8700 | users:(("python3.13",pid=128299,fd=7)) |
| 8701 | users:(("python3.13",pid=127419,fd=13)) |
| 8702 | users:(("python3.13",pid=128229,fd=13)) |
| 8732 | users:(("python3.13",pid=127506,fd=3)) |
| 9090 | *:* |
| 9091 | 0.0.0.0:* |
| 9099 | users:(("python3.13",pid=7782,fd=3)) |
| 9222 | users:(("chrome",pid=129955,fd=60)) |
| 9800 | users:(("python3.13",pid=128291,fd=6)) |
| 9801 | users:(("python3.13",pid=128355,fd=6)) |
| 9810 | users:(("python3.13",pid=128471,fd=6)) |
| 9811 | users:(("python3.13",pid=128290,fd=6)) |
| 9875 | users:(("python3.13",pid=128292,fd=3)) |
| 9876 | users:(("python3.13",pid=128320,fd=3)) |
| 9881 | 0.0.0.0:* |
| 9881 | [::]:* |
| 9890 | users:(("python3",pid=127543,fd=17)) |
| 9900 | users:(("python3.13",pid=128281,fd=6)) |
| 9922 | users:(("MainThread",pid=390665,fd=21)) |
| 9977 | users:(("python3",pid=127386,fd=3)) |
| 9979 | users:(("python3.13",pid=127352,fd=3)) |
| 9980 | users:(("python3.13",pid=127348,fd=3)) |
| 9993 | *:* |
| 9993 | 0.0.0.0:* |
| 11434 | users:((".ollama-wrapped",pid=127649,fd=3)) |
| 15555 | *:* |
| 17698 | *:* |
| 17699 | *:* |
| 17700 | *:* |
| 18000 | 0.0.0.0:* |
| 18090 | *:* |
| 18091 | *:* |
| 18092 | users:(("python3.13",pid=127573,fd=6)) |
| 18093 | *:* |
| 18094 | users:(("python3.13",pid=128189,fd=6)) |
| 18300 | *:* |
| 18700 | *:* |
| 18789 | users:(("openclaw",pid=1057197,fd=25)) |
| 18791 | users:(("openclaw",pid=1057197,fd=26)) |
| 18798 | users:(("python3.13",pid=128201,fd=3)) |
| 19800 | users:(("python3.13",pid=127531,fd=3)) |
| 19876 | *:* |
| 19890 | *:* |
| 19891 | *:* |
| 19892 | *:* |
| 19893 | *:* |
| 19990 | users:(("MainThread",pid=2192708,fd=22)) |
| 19999 | users:(("python3.13",pid=127475,fd=3)) |
| 20241 | users:(("cloudflared",pid=130577,fd=6)) |
| 20242 | users:(("cloudflared",pid=1561894,fd=6)) |
| 20243 | users:(("cloudflared",pid=1604444,fd=6)) |
| 22000 | *:* |
| 24801 | users:(("python3.13",pid=128253,fd=3)) |
| 24802 | users:(("python3.13",pid=127625,fd=3)) |
| 40544 | 0.0.0.0:* |
| 47984 | *:* |
| 47989 | *:* |
| 47990 | *:* |
| 48010 | *:* |
| 50051 | users:(("hqsshd",pid=127535,fd=6)) |
| 60002 | *:* |
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
finance_bot.py
letta-sync.py
mac.py
macg.py
macg_api.py
macg_mcp.py
macg_memory_orchestrator.py
macg_tui_demo.py
marketing_bot.py
mem0_bridge.py
mem0_decay.py
mem0_file_sync.py
mem0_watchdog.py
memory_pulse_monitor.py
notify.py
op_push_service.py
ops_bot.py
proactive.py
report_generator.py
rss_bot.py
self_improve.py
sensor-bridge.py
social_relations.py
telegram-khoj-bridge.py
telegram-userbot.py
telegram_bot.py
telegram_bot_enhanced.py
tg_create_group.py
tg_fix_group.py
tg_forum_watcher.py
tg_group_router.py
tg_healer.py
tg_logger.py
tg_monitor.py
tg_pilot.py
tg_predictor.py
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

### ~/.local/bin/ — 运维脚本（774个，按前缀分组）

**BaiduPCS-*** (1个): `BaiduPCS-Go`
**adb-*** (6个): `adb-autoconnect.sh, adb-device-monitor.py, adb-reverse-haven.sh, adb-tablet-keepalive.sh, adb-whoami, adb-windows.sh`
**agent-*** (4个): `agent-ask.py, agent-danmaku, agent-events-sync.sh, agent-watch`
**aggregate-*** (1个): `aggregate-marketing-research.sh`
**agi-*** (2个): `agi-feedback-bus.sh, agi-persistent-monitor.sh`
**ai-*** (22个): `ai-architecture-audit, ai-brainstorm, ai-cad, ai-config-guard.sh, ai-config-watcher.sh, ai-context-compile, ai-knowledge-sync, ai-manager, ai-patrol-autofix.sh, ai-patrol-daemon.sh... +12更多`
**aider-*** (2个): `aider-post-commit-hook, aider-with-memory`
**anti-*** (1个): `anti-restart-loop.sh`
**apk-*** (1个): `apk-debug`
**architecture-*** (2个): `architecture-cleanup.sh, architecture-health-check`
**asset-*** (1个): `asset-watcher`
**auto-*** (8个): `auto-desktop-rules, auto-discovery.py, auto-fix-services, auto-google-login, auto-login-claude, auto-skill-trigger.sh, auto-update, auto_browser.py`
**backup-*** (2个): `backup-claude-config, backup-ide-configs`
**baseline-*** (1个): `baseline-update.sh`
**bash-*** (1个): `bash-wrapper`
**boot-*** (1个): `boot-recovery.sh`
**browser-*** (1个): `browser-launch-with-cookies`
**cache-*** (1个): `cache-guard.sh`
**cc-*** (26个): `cc-autoagent-hook.sh, cc-autonomous-runner.sh, cc-autoskill-hook.sh, cc-behavior-audit.sh, cc-blocker-resolver.sh, cc-conversation-recorder.sh, cc-decision-engine.py, cc-decision-learner.sh, cc-desktop-image-inject.sh, cc-dialogue-broadcast.sh... +16更多`
**cct-*** (1个): `cct-tmux-wrap`
**cdp-*** (1个): `cdp-inject-cookies`
**cf-*** (2个): `cf-tunnel-7699, cf-tunnel-setup`
**change-*** (2个): `change-recorder.sh, change-watcher`
**charlie-*** (1个): `charlie-ego-record.sh`
**check-*** (3个): `check-idle-simple.sh, check-idle.sh, check-ttyd.sh`
**chroma-*** (3个): `chroma-server.py, chroma-server.sh, chroma_server.py`
**chrome-*** (6个): `chrome-fix.sh, chrome-login-backup.sh, chrome-login-restore.sh, chrome-login-watchdog.sh, chrome-stable-login-setup.sh, chrome-stable-login.sh`
**chromium-*** (1个): `chromium-launch`
**claude-*** (36个): `claude-api-autoheal.sh, claude-api-manager, claude-api-unified, claude-auto-fix, claude-auto-login, claude-cad.py, claude-dual, claude-esp, claude-failover.sh, claude-free-api-auto... +26更多`
**claudep-*** (1个): `claudep-tmux-wrap`
**clear-*** (2个): `clear-notifs, clear-notifs-btn`
**clip-*** (1个): `clip-sync`
**clipboard-*** (2个): `clipboard-sync-tablet, clipboard-sync-windows`
**cliphist-*** (2个): `cliphist-health-check, cliphist-watchdog`
**cloudflared-*** (4个): `cloudflared-bin, cloudflared-happy, cloudflared-launcher, cloudflared-ttyd`
**code-*** (4个): `code-dual, code-indexer, code-search, code-watcher`
**codex-*** (6个): `codex-bypass, codex-doctor.sh, codex-hqssh, codex-op-delegate, codex-tmux-wrap, codex-yolo`
**config-*** (2个): `config-immutable-snapshot, config-lock.sh`
**connectivity-*** (1个): `connectivity-chain-watchdog.sh`
**cookie-*** (1个): `cookie-watcher.py`
**create-*** (1个): `create-skill.py`
**crush-*** (1个): `crush-wrapper.sh`
**cursor-*** (1个): `cursor-setup-check`
**daily-*** (2个): `daily-log-generator.py, daily-security-scan.sh`
**danmaku-*** (1个): `danmaku-send`
**dead-*** (1个): `dead-component-detect.sh`
**deepseek-*** (3个): `deepseek-code, deepseek-mcp-server.py, deepseek-with-context`
**deploy-*** (2个): `deploy-phone-frpc.sh, deploy-tasker-gateway.sh`
**desktop-*** (3个): `desktop-pet.py, desktop-stream.py, desktop-tree-overlay`
**discord-*** (4个): `discord-bot-healthcheck.sh, discord-bot-inspect.sh, discord-intelligent-bot.py, discord-roo-bridge`
**disk-*** (1个): `disk-guard.sh`
**doc-*** (3个): `doc-discover.sh, doc-fetch.sh, doc-search.py`
**docker-*** (3个): `docker-cleanup.sh, docker-health-nurse.sh, docker-recovery-plan`
**dotfiles-*** (2个): `dotfiles-integrity-check.sh, dotfiles-symlink-watch.sh`
**douyin-*** (1个): `douyin-web`
**download-*** (1个): `download-claude-export-from-email.py`
**dpdns-*** (1个): `dpdns-renew`
**event-*** (1个): `event_hooks_trigger.py`
**evolve-*** (1个): `evolve-lessons-sync.py`
**export-*** (1个): `export-claude-conversations.py`
**fcitx5-*** (2个): `fcitx5-adaptive-check, fcitx5-fix`
**finance-*** (1个): `finance-reminder.sh`
**fix-*** (1个): `fix-screenshot-permission`
**floorp-*** (3个): `floorp-clean-start, floorp-popup-fix, floorp-session-cleaner.py`
**foc-*** (1个): `foc-tmux-wrap`
**force-*** (2个): `force-claude-proxy, force-claude-proxy.sh`
**four-*** (1个): `four-tool-dispatch.sh`
**frontend-*** (1个): `frontend-verify.sh`
**frp-*** (2个): `frp-adb-keepalive.sh, frp-watchdog.sh`
**frpc-*** (2个): `frpc-port-guard.py, frpc-port-guard.sh`
**frps-*** (1个): `frps-watchdog.sh`
**fsearch-*** (1个): `fsearch-idle-update.sh`
**gather-*** (1个): `gather-phone-status.sh`
**git-*** (2个): `git-backup.sh, git-codebase-update`
**github-*** (2个): `github-action-trigger, github-ai-weekly`
**google-*** (1个): `google-chrome-proxy`
**gpu-*** (1个): `gpu-mode`
**happy-*** (3个): `happy-daemon-start.sh, happy-login.sh, happy-session-watchdog.sh`
**haven-*** (9个): `haven-create-group.py, haven-detect-tablet.sh, haven-keepalive.sh, haven-mcp-adb-bridge.py, haven-mcp-proxy.py, haven-mcp-telegram-user.py, haven-mcp-telegram.sh, haven-mcp-user-launcher.sh, haven-sync.sh`
**health-*** (1个): `health-scorer`
**hermes-*** (5个): `hermes-attach.sh, hermes-pty-server.py, hermes-telnetd.py, hermes-tty.sh, hermes-wrapper`
**hqssh-*** (3个): `hqssh-hosts-info, hqssh-mcp, hqssh-tmux`
**huggingface-*** (1个): `huggingface-cli`
**hypr-*** (4个): `hypr-kdeconnect-portal, hypr-workspace-apply, hypr-workspace-learn, hypr-workspace-sort.sh`
**ibus-*** (1个): `ibus-toggle.sh`
**idea-*** (2个): `idea-2233, idea-boost.sh`
**iflytek-*** (1个): `iflytek-dict-sync`
**incident-*** (1个): `incident-reporter`
**index-*** (1个): `index-assets`
**input-*** (1个): `input-leap-server`
**install-*** (2个): `install-deepseek-aider.sh, install-roo-extensions.sh`
**integrity-*** (2个): `integrity-check.sh, integrity-init.sh`
**ios-*** (1个): `ios-connect-mcp.py`
**ip-*** (1个): `ip-monitor-telegram`
**jetbrains-*** (1个): `jetbrains-ai-proxy`
**kde-*** (4个): `kde-logout-now, kde-open, kde-open5, kde-tray-auto-hide`
**kill-*** (1个): `kill-ghostty`
**kilo-*** (1个): `kilo-profile`
**lag-*** (1个): `lag-detector.sh`
**latest-*** (1个): `latest-img`
**launch-*** (1个): `launch-via-tablet.sh`
**launcher-*** (1个): `launcher-health-check.sh`
**letta-*** (13个): `letta-deadman-switch.sh, letta-distill, letta-health-check.sh, letta-health-guard, letta-health-monitor, letta-mcp, letta-mcp-health-check, letta-mcp-server, letta-monitor, letta-planning-trigger.sh... +3更多`
**libreoffice-*** (1个): `libreoffice-x11`
**litellm-*** (2个): `litellm-error-guard.sh, litellm-startup.sh`
**llama-*** (1个): `llama-server.sh`
**macg-*** (2个): `macg_context_probe, macg_memory_read`
**marketing-*** (1个): `marketing-web-workflow.sh`
**mcp-*** (1个): `mcp-health-check`
**media-*** (1个): `media-crawler`
**mem-*** (2个): `mem-alert.sh, mem-stats`
**mem0-*** (1个): `mem0-bridge-wrapper`
**memory-*** (13个): `memory-auto-commit, memory-backup, memory-bootstrap.sh, memory-cron.sh, memory-decay-engine.py, memory-dream, memory-engine, memory-episodic.py, memory-evolution-engine, memory-kg-populator.py... +3更多`
**meta-*** (2个): `meta-cognition.py, meta-monitor.sh`
**mihomo-*** (4个): `mihomo-anthropic-check, mihomo-config-sync, mihomo-config-validate, mihomo-guardian`
**mobile-*** (1个): `mobile-entry`
**morning-*** (1个): `morning-brief.sh`
**mutual-*** (1个): `mutual-review`
**network-*** (1个): `network-guard.sh`
**new-*** (1个): `new-api-manager`
**nix-*** (3个): `nix-store-integrity-check.sh, nix-store-nurse, nix_voice_agent.py`
**nixos-*** (15个): `nixos-ai-fix-engine, nixos-auto-commit, nixos-decision-engine, nixos-full-sync, nixos-gui-guardian, nixos-llm-analyzer, nixos-prebuild-audit.sh, nixos-preflight-check.sh, nixos-rebuild-safe, nixos-smoketest.sh... +5更多`
**notif-*** (4个): `notif-btn-daemon.sh, notif-btn.sh, notif-floating-btn.sh, notif-tray-icon.sh`
**notify-*** (3个): `notify-buf-dashboard, notify-screenshot-howto, notify-send`
**ntfs-*** (1个): `ntfs-health-check`
**numlock-*** (1个): `numlock-guard`
**oc-*** (1个): `oc-chat-watch`
**office-*** (1个): `office-agent-runner.sh`
**ollama-*** (1个): `ollama-cuda`
**op-*** (21个): `op-adaptive-gate, op-cc-bridge, op-cc-observer.sh, op-codex-plan, op-dialogue-broadcast.sh, op-dispatch, op-exec-viewer.sh, op-exec.sh, op-feed-viewer.sh, op-force.sh... +11更多`
**open-*** (2个): `open-dashboard-workspace.sh, open-unified-agents-workspace.sh`
**openagents-*** (1个): `openagents-network-wrapper.sh`
**openclaw-*** (3个): `openclaw-restart, openclaw-session-watchdog.sh, openclaw-tmux-wrap`
**opencode-*** (44个): `opencode-19890-proxy.py, opencode-8080-proxy.py, opencode-autoupgrade, opencode-bug-tracker.sh, opencode-config-guard.sh, opencode-continue-safe, opencode-cost-monitor, opencode-deep, opencode-dstate-watchdog, opencode-enforced... +34更多`
**other-*** (85个): `PyGPT.AppImage, agi, ai, aider, baidunetdisk, ccc, ccm, cerebras, claude, claude-tmux-wrap.bak... +75更多`
**otp-*** (1个): `otp-sync`
**overcode-*** (2个): `overcode-loop-watch.sh, overcode-tmux-wrap`
**overtab-*** (3个): `overtab-serve-start, overtab-serve-stop, overtab-tmux-wrap`
**padavan-*** (1个): `padavan-sync.py`
**panel-*** (1个): `panel-nurse`
**paperclip-*** (6个): `paperclip-aider-worker, paperclip-auto-sync, paperclip-dispatcher, paperclip-report-daemon.sh, paperclip-resolve-conflicts, paperclip-restore`
**paste-*** (1个): `paste-image-pinned`
**pattern-*** (1个): `pattern-extract.sh`
**permission-*** (1个): `permission_check.py`
**pet-*** (1个): `pet-feeder`
**petals-*** (1个): `petals-server.sh`
**phone-*** (7个): `phone-ai-bridge.sh, phone-clip-sync, phone-clip-sync-v2, phone-connect-mcp.py, phone-control.sh, phone-network-fix.sh, phone-screenshot`
**plasmashell-*** (1个): `plasmashell-crash-guard.sh`
**playwright-*** (4个): `playwright-chromium-headed, playwright-chromium-nix, playwright-mcp-cleanup, playwright-smart.sh`
**post-*** (4个): `post-edit-verify.sh, post-screenshot.sh, post-task-summary.py, post-task-summary.sh`
**project-*** (2个): `project-context-inject, project-context-save`
**proxy-*** (7个): `proxy-403-monitor, proxy-db-init, proxy-learn, proxy-port-guard.sh, proxy-status-quick, proxy-status-widget, proxy-windows-discover`
**push-*** (2个): `push-apk, push-tunnel-url`
**python-*** (1个): `python-crash-guard.sh`
**query-*** (1个): `query-router.sh`
**quick-*** (2个): `quick-run-cmd, quick-screenshot`
**rebuild-*** (2个): `rebuild-session-notes.sh, rebuild-system-index`
**recovery-*** (1个): `recovery-manager`
**review-*** (2个): `review-op-branch, review-two-model.py`
**rofi-*** (2个): `rofi-drun-pinyin.sh, rofi-pinyin-cache-builder.py`
**roo-*** (12个): `roo-apply-optimizations.sh, roo-backup-config.sh, roo-code-check, roo-digest, roo-enforce-rules, roo-export, roo-index-load.sh, roo-index-save.sh, roo-restore-config.sh, roo-state-backup... +2更多`
**router-*** (2个): `router-config-snapshot.sh, router-port-list.py`
**rta-*** (1个): `rta-scanner`
**runbook-*** (1个): `runbook-engine`
**s-*** (1个): `s-save`
**scrcpy-*** (1个): `scrcpy-panel`
**screenshot-*** (3个): `screenshot-now, screenshot-pin, screenshot-watcher.sh`
**selflearn-*** (1个): `selflearn-health-check.sh`
**sentinel-*** (6个): `sentinel-ack, sentinel-core, sentinel-dispatch, sentinel-inject, sentinel-onfailure, sentinel-watch`
**service-*** (4个): `service-config-guard, service-directory-push.sh, service-panel.sh, service-zombie-cleaner.sh`
**session-*** (7个): `session-archive-cleanup.sh, session-archive.sh, session-archiver.sh, session-embedder-wrapper.sh, session-embedder.py, session-rag-server.py, session-switch`
**setup-*** (2个): `setup-0011, setup-letta-telegram-alert`
**sisy-*** (1个): `sisy-tmux-wrap`
**skill-*** (1个): `skill-auto-extract.py`
**smart-*** (6个): `smart-ip, smart-memory-classifier, smart-redirector.py, smart-redirector.sh, smart-router.py, smart-search`
**smoke-*** (1个): `smoke-test.sh`
**sqlite-*** (2个): `sqlite_web, sqlite_wsgi`
**ssh-*** (1个): `ssh-win`
**start-*** (5个): `start-chromadb, start-desktop-pet.sh, start-hyprland-fixed, start-session-rag-server.sh, start-wechat`
**stepfun-*** (2个): `stepfun-quota-scraper.py, stepfun-quota-update-quiet.sh`
**switch-*** (1个): `switch-claude-provider.sh`
**sync-*** (9个): `sync-all-browser-cookies, sync-bookmarks-to-chromium, sync-claude-export-to-letta, sync-cookies-to-chrome, sync-md-to-letta, sync-memory-to-ntfs, sync-session-to-letta, sync-session-to-letta-v1-backup, sync-to-obsidian`
**sys-*** (1个): `sys-info-mcp.py`
**system-*** (4个): `system-call-check, system-healer, system-health-check, system-sentry-check.sh`
**systemd-*** (1个): `systemd-orphan-guard.sh`
**tablet-*** (1个): `tablet-adb-watch`
**tailscale-*** (1个): `tailscale-interlink-watchdog.sh`
**task-*** (2个): `task-complete, task-step-check.sh`
**terminal-*** (1个): `terminal-pet`
**test-*** (2个): `test-claude-knowledge, test-opencode-modes`
**tg-*** (11个): `tg-auth.py, tg-bot-tasks, tg-canvas, tg-command, tg-copy-listener.py, tg-daily-digest-wrapper.sh, tg-daily-digest.py, tg-finance-setup.sh, tg-push, tg-saved-reader... +1更多`
**tiny-*** (1个): `tiny-agents`
**tmux-*** (3个): `tmux-module, tmux-session-toggle, tmux-voice-bridge.py`
**todo-*** (1个): `todo_sync.py`
**tool-*** (2个): `tool-capture-hook.sh, tool-lookup.sh`
**ttyd-*** (3个): `ttyd-dbus-audit.sh, ttyd-quick-check, ttyd-strace-watcher.sh`
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
**waybar-*** (26个): `waybar-adb.sh, waybar-agent.sh, waybar-api-quota.sh, waybar-chain.sh, waybar-chroma.sh, waybar-clipsync.sh, waybar-disk.sh, waybar-dispatch.sh, waybar-finance.sh, waybar-frp.sh... +16更多`
**wayland-*** (1个): `wayland-screenshot`
**web-*** (2个): `web-ai-proxy, web-ai-proxy-wrapper`
**wechat-*** (16个): `wechat-android-backup.sh, wechat-contact-sync.py, wechat-finance, wechat-kanban-push.sh, wechat-live-monitor.py, wechat-merge.py, wechat-msg-sync-wrapper.sh, wechat-msg-sync.py, wechat-query-mcp, wechat-reply-consumer.py... +6更多`
**weekly-*** (1个): `weekly-error-review`
**whisper-*** (12个): `whisper-bench, whisper-cli, whisper-command, whisper-cpp, whisper-cpp-download-ggml-model, whisper-lsp, whisper-quantize, whisper-server, whisper-stream, whisper-stt-server... +2更多`
**wifi-*** (1个): `wifi-monitor.sh`
**win-*** (6个): `win-8080-relay.sh, win-auto-nogui-push.sh, win-deploy, win-deploy-on-wifi.sh, win-exec, win-tunnel-wrapper.sh`
**wine-*** (1个): `wine-wechat`
**wol-*** (1个): `wol-windows.sh`
**workspace-*** (1个): `workspace-warp-prepare.sh`
**worktree-*** (1个): `worktree-cleanup`
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
almanak
altk-evolve
android-sdk
baidu-download
baidunetdisk
cc-op-graph
comfyui
content-creator
content-router
crewai-venv
crm
embed-server
embed-venv
gelab-zero
gmail-bridge
hub-mobile
image-search
kanban-tui
khoj
latentsync
launcher
lx-music-source-gateway
mcp-shared-memory
mem0
mem0-data
mem0-venv
migration
musetalk
musetalk-models
music-manager
nginx
ollama
onlyoffice
openagents
openclaw-tg-canvas
opencode
pywxdump
rss
sadtalker
stepfun-telegram-bot
video-call-agent
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
共 130 个 skill 目录

### memory/ — 记忆系统
```
SYSTEM-INDEX.md
decision-memory.md
lessons-learned.md
op-tasks.md
opencode-session-log.md
router-infra.md
session-notes.md
user-preferences.md
```

## 三、systemd 用户服务（521个注册，130个运行中）

### 当前运行中
```
adb-device-monitor
agent-orchestrator
agi-brain
agi-frontend
agi-gateway
ai-config-watcher
ai-rules-sync
ai-watchdog
app-org.kde.kdeconnect.daemon@autostart
caddy-launcher
cf-tunnel-7699
change-watcher
chromadb
chrome-cdp
chronos-biofeedback
chronos-sensory
claude-esp
claude-tablet-output
claude-token-tray
clip-sync
clipboard-sync-tablet
clipboard-sync-windows
code-watcher
config-immutable-snapshot
content-router
cookie-sync-server
cookie-watcher
crewai-gateway
crewai-openagents-bridge
dbus
disk-watchdog
dotfiles-symlink-watch
earlyoom
embedding-server
evolve-mcp
fcitx5
file-server
finance-agent
finance-bot
frpc
gcr-ssh-agent
haven-keepalive
haven-mcp-proxy
haven-mcp-telegram
haven-mcp-telegram-user
headless-browser
hermes-tmux
hermes-tty
hqsshd
hub-api
image-search
launcher
letta-mcp
litellm-strip-proxy
macg-mcp
mem0-bridge
memory-auto-commit
memory-evolution
mihomo
mihomo-watch
navidrome
nix-voice-agent
numlock-guard
oa-agi-brain-bridge
oa-codex-bridge
oa-crewai-bridge
oa-opencode-bridge
oa-router
oa-telegram-notify
office-agent
ollama
op-tasks-watcher
op-watchdog
openagents-network
openclaw-gateway
opencode-19890-proxy
opencode-config-guard
opencode-intent-detector
opencode-memwatch
opencode-session-recorder
opencode-stuck-watch
opencode-web
ops-bot
otp-sync
overcode-loop-watch
phone-ai-bridge
phone-clip-sync
pipewire
pipewire-pulse
primary-clip-bridge
proxy-403-monitor
python-crash-guard
rss-bot
screenshot-watcher
smart-redirector
speech-dispatcher
stepfun-tg-bot
sunshine
sys-info-mcp
tablet-control-panel
telegram-userbot
tmux-voice-bridge
ttyd-8080
ttyd-aider
ttyd-audit
ttyd-cct
ttyd-claude
ttyd-claudep
ttyd-codex
ttyd-foc
ttyd-hermes
ttyd-macg
ttyd-opencode
ttyd-overtab
ttyd-ulwh
video-call-agent
voxtype
waybar
waybar-guardian
wayland-session-bindpid@127357
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

## 四、定时任务（115个 timer）
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
api-quota-updater
auto-fix-services
backup-cleanup
cache-guard
cc-autonomous-runner
cc-op-verifier
cc-task-auditor
cf-url-notify
chrome-login-backup
chronos-subconscious
claude-orphan-killer
code-indexer
copywriting-collector
daily-log-generator
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
evolve-sync
finance-reminder
frp-watchdog
frpc-port-guard
github-ai-weekly
happy-session-watchdog
iflytek-dict-sync
image-captioner
incident-reporter
integrity-check
letta-deadman-switch
letta-distill
letta-planning
letta-sync
litellm-error-guard
maintenance-learner
mem-alert
mem0-decay
mem0-file-sync
mem0-watchdog
memory-backup
memory-curator
memory-injector
memory-pulse-monitor
memory-tg-daily
meta-cognition
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
op-lock-watchdog
op-precheck
op-self-upgrade
op-tasks-archive
opencode-bug-tracker
opencode-job-charlie-b445f233ebb8-aider-refactor
opencode-job-charlie-b445f233ebb8-codebase-mapper
opencode-job-charlie-b445f233ebb8-cost-accountant
opencode-job-charlie-b445f233ebb8-heartbeat-system-sentry
opencode-job-charlie-b445f233ebb8-security-watchdog
opencode-session-guard
opencode-web-idle
plocate-update
proxy-port-guard
push-tunnel-url
rebuild-session-notes
rebuild-system-index
router-snapshot
runbook-engine
security-scan
selflearn-check
service-config-guard
session-archive
sync-memory-ntfs
systemd-orphan-guard
systemd-reexec
systemd-tmpfiles-clean
task-review-weekly
tg-daily-digest
tg-healer
tg-predictor
waybar-guardian
waybar-score-finalize
wechat-backup
wechat-backup-reminder
wechat-contact-sync
wechat-live-monitor
wechat-msg-sync
wechat-version-guard
wol-windows
workspace-scheduler
worktree-cleanup
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
