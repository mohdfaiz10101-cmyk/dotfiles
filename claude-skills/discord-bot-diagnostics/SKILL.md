---
name: discord-bot-diagnostics
description: Discord bot 状态诊断，API quota、429 错误、Gemini 错误排查
---

# discord-bot-diagnostics

**Version:** 1.0.0
**Author:** Claude MPM
**Triggers:** discord bot, bot status, api quota, 429 error, gemini error, bot diagnostics

## Introduction

Diagnose and auto-repair Discord Bot issues, including systemd service status, API quota exhaustion (429 errors), environment variable misconfiguration, and connectivity problems.

## When to use

- Discord Bot not responding in channels
- User reports 429 / RESOURCE_EXHAUSTED errors
- Bot service crashed or restarted unexpectedly
- Need to verify API keys or environment variables
- API quota monitoring and fallback suggestions
- Post-deployment health check

## Prerequisites

- **Service:** `discord-bot.service` (systemd user service)
- **Files:**
  - `~/hub/discord-bot.py` (Bot code)
  - `~/.config/api-keys/systemd.env` (Environment variables)
  - `~/.config/systemd/user/discord-bot.service` (Service definition)
- **APIs:** Discord, Gemini, OpenCode (GLM), Claude, DeepSeek

## Diagnostic Workflow

### 1. Check Bot Status

```bash
# Check if Bot is running
systemctl --user status discord-bot.service --no-pager | head -20

# Check recent restarts
journalctl --user -u discord-bot.service --since "1 hour ago" | grep -E "Started|Stopped|FAILED"
```

**Expected:** `Active: active (running)`
**If Failed:** Proceed to restart procedure.

### 2. Verify Environment Variables

```bash
# Check systemd.env content
cat ~/.config/api-keys/systemd.env | grep -E "DISCORD_BOT_TOKEN|GEMINI_API_KEY|DEEPSEEK_API_KEY"

# Verify service loads environment file
systemctl --user cat discord-bot.service | grep EnvironmentFile
```

**Required Keys:**
- `DISCORD_BOT_TOKEN` — Discord Bot authentication
- `GEMINI_API_KEY` — Google Gemini API (optional if using fallback)
- `DEEPSEEK_API_KEY` — DeepSeek API (optional)

### 3. Analyze Recent Logs

```bash
# Last 50 lines with error filtering
journalctl --user -u discord-bot.service -n 50 --no-pager | grep -E "ERROR|FAILED|429|RESOURCE_EXHAUSTED|DEBUG.*Received"

# Real-time monitoring
journalctl --user -u discord-bot.service -f
```

**Key Patterns:**
- `[DEBUG] Received message in channel: cc` — Message received
- `[OK] Discord Bot online` — Bot connected
- `429` / `RESOURCE_EXHAUSTED` — API quota exhausted
- `DISCORD_BOT_TOKEN not set` — Missing token

### 4. Test API Connectivity

```bash
# Discord API
curl -I https://discord.com/api/v10

# Test Gemini CLI (if configured)
source ~/.config/api-keys/env && echo "test" | timeout 5 gemini 2>&1 | head -10

# Test OpenCode (local)
echo "test" | timeout 5 opencode 2>&1 | head -5
```

### 5. Detect API Quota Errors

```bash
# Search for quota exhaustion in logs
journalctl --user -u discord-bot.service --since "1 hour ago" | grep -c "429"

# Check last occurrence
journalctl --user -u discord-bot.service | grep "429" | tail -3
```

## Auto-repair Procedures

### Restart Bot Service

```bash
# Restart and verify
systemctl --user restart discord-bot.service
sleep 5
systemctl --user status discord-bot.service --no-pager
```

### Reload Environment Variables

```bash
# If systemd.env was updated
systemctl --user daemon-reload
systemctl --user restart discord-bot.service
```

### Handle Quota Exhaustion

**When Gemini API quota exhausted:**

1. **Automatic fallback** (already implemented in Bot code)
   - Bot detects 429 error → switches to OpenCode (local GLM)
   - User notification: "⚠️ Gemini 配额耗尽，自动切换到 OpenCode"

2. **Manual intervention**
   ```bash
   # Wait for quota reset (Google resets daily at 00:00 UTC)
   # Or use other agents explicitly:
   # In Discord: @claude <your message>
   # In Discord: @opencode <your message>
   ```

3. **Monitor quota usage**
   - Visit: https://ai.dev/rate-limit
   - Check daily limits: 1500 requests/day (free tier)

## Example Session

**User reports:** "Discord Bot in #cc channel not responding"

```bash
# Step 1: Check status
systemctl --user status discord-bot.service --no-pager
# → Active: active (running) ✓

# Step 2: Check recent logs
journalctl --user -u discord-bot.service -n 30 | grep -E "Received|429"
# → [DEBUG] Received message in channel: cc
# → Attempt 1 failed with status 429

# Step 3: Diagnose quota issue
journalctl --user -u discord-bot.service | grep "429" | tail -1
# → "You exceeded your current quota" (RESOURCE_EXHAUSTED)

# Step 4: Verify fallback logic
cat ~/hub/discord-bot.py | grep -A5 "quota_exceeded"
# → Fallback to OpenCode is configured ✓

# Step 5: Test manually
source ~/.config/api-keys/env && echo "test" | opencode
# → OpenCode works ✓

# Conclusion: Bot auto-fallback should handle this. If not, restart:
systemctl --user restart discord-bot.service
```

## Troubleshooting

### Bot shows "Active" but not responding

**Cause:** Stuck in event loop or Discord connection lost

**Fix:**
```bash
# Force restart
systemctl --user restart discord-bot.service

# Check connection logs
journalctl --user -u discord-bot.service -n 20 | grep "connected to Gateway"
```

### "DISCORD_BOT_TOKEN not set" error

**Cause:** Environment variable not loaded

**Fix:**
```bash
# Verify token in systemd.env
cat ~/.config/api-keys/systemd.env | grep DISCORD_BOT_TOKEN

# Reload and restart
systemctl --user daemon-reload
systemctl --user restart discord-bot.service
```

### Gemini CLI always returns 429

**Cause:** Daily quota exhausted (1500 requests/day)

**Fix:**
1. Wait for reset (00:00 UTC daily)
2. Use manual agent selection: `@claude` or `@opencode`
3. Bot auto-fallback should handle this (check code in discord-bot.py:180-200)

### Bot created only some channels

**Cause:** Permission issue or guild limit

**Fix:**
```bash
# Check bot permissions in Discord Developer Portal
# Required: Manage Channels, Send Messages, Embed Links

# Manually verify channels in Discord:
# Should exist: #cc, #claude, #gemini, #opencode, #billy, #alerts, #daily
```


### Issue (Auto-detected @ 2026-04-08 01:32:41)

**User Report:** Discord bot encountered 429 error - RESOURCE_EXHAUSTED when processing messages

**Symptoms:**
- Discord bot encountered 429 error - RESOURCE_EXHAU
- Issue occurred during skill execution

**Resolution:**
- [TODO] Add specific resolution steps
- Check related logs and error messages
- See related skills for context (if available)



### Issue (Auto-detected @ 2026-04-08 01:36:29)

**User Report:** discord bot 502 bad gateway error

**Symptoms:**
- discord bot 502 bad gateway error
- Issue occurred during skill execution

**Resolution:**
- [TODO] Add specific resolution steps
- Check related logs and error messages
- See related skills for context (if available)


## Files and Paths

| File | Purpose |
|------|---------|
| `~/hub/discord-bot.py` | Bot source code |
| `~/.config/api-keys/systemd.env` | Environment variables (systemd format) |
| `~/.config/api-keys/env` | Environment variables (shell format) |
| `~/.config/systemd/user/discord-bot.service` | Systemd service definition |
| `~/.claude/projects/-home-charlie/memory/lessons-learned.md` | Historical issues log |
| `~/.claude/projects/-home-charlie/memory/command-reference.md` | Command quick reference |

## Version History

- **1.0.0** (2026-04-08) — Initial release
  - Diagnostic procedures for Bot status, API quota, environment variables
  - Auto-repair for service restart and quota exhaustion
  - Integration with Bot's auto-fallback logic

## Related Skills

- `mpm-config` — MPM configuration management
- `hermetic-ledger` — Customer heartbeat system (if using HyperChat)
- `paperclip` — Task coordination (if using Paperclip agents)

<!-- Test commit at 2026年 04月 08日 星期三 01:32:19 CST -->
