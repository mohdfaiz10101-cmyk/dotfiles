---
name: merge-sub
description: >
  Merge multiple proxy subscription URLs into a single Clash Meta (mihomo) config.
  Accepts URLs in Clash YAML, base64-encoded v2ray links, or raw share link formats.
  Outputs a unified config with regional proxy groups and uploads to file hosting for sharing.
---

# Merge Subscription Skill

Merge multiple proxy subscription sources into one Clash Meta config file.

## When to Use

- User provides multiple subscription URLs and wants them combined
- User says "合并订阅", "merge subscriptions", "合成一个订阅"
- User asks for a unified proxy config from multiple sources

## Input Format

User provides 2+ subscription URLs, separated by spaces or newlines.

## Execution Steps

### 1. Fetch all subscription URLs (parallel)

```bash
# For each URL, try these in order:
# 1. Direct curl (for Clash YAML endpoints)
curl -sL --max-time 15 "<URL>"
# 2. With Clash User-Agent (some endpoints require it)
curl -sL --max-time 15 -A "ClashForAndroid/2.5.12" "<URL>"
```

### 2. Detect and parse each source

**Clash YAML** — directly parseable, extract `proxies` list.

**Base64-encoded** — decode first, then parse share links:
```bash
echo "<content>" | base64 -d
```

**Share link formats supported:**
- `vless://` — VLESS with Reality/TLS/WS
- `hysteria2://` — Hysteria2 protocol
- `trojan://` — Trojan protocol
- `ss://` — Shadowsocks
- `vmess://` — VMess (base64 JSON)

### 3. Parse share links to Clash proxy dicts

Run the merge script:
```bash
python3 ~/.claude/skills/merge-sub/merge_sub.py \
  --url "<url1>" --url "<url2>" --url "<url3>" \
  --output ~/merged_sub.yaml
```

Or use interactively (script fetches + parses + merges):
```bash
python3 ~/.claude/skills/merge-sub/merge_sub.py \
  --url "<url1>" --url "<url2>" \
  --upload
```

### 4. Proxy name prefixing

Each source gets a prefix to avoid name collisions:
- Source 1: `S1-<original_name>`
- Source 2: `S2-<original_name>`
- Source N: `SN-<original_name>`

### 5. Regional proxy groups

Auto-generated groups:
- `🚀 节点选择` — manual select, includes all regional groups
- `♻️ 自动选择` — url-test with all nodes
- `🇭🇰 香港` / `🇯🇵 日本` / `🇺🇸 美国` / `🇸🇬 新加坡` / `🇨🇳 台湾` / `🇰🇷 韩国` / `🇪🇺 欧洲` / `🇦🇺 澳大利亚` — regional url-test groups

### 6. Upload for sharing

Try in order (parallel attempts):
1. `https://tmpfiles.org/api/v1/upload` — POST form `file=@config.yaml`
   - Direct link: `https://tmpfiles.org/dl/<id>/<filename>`
   - TTL: ~1 hour
2. `https://transfer.sh/<filename>` — PUT upload
3. `https://0x0.st` — POST form `file=@config.yaml`
4. `https://catbox.moe/user/api.php` — POST form

**Note:** Some services may be blocked by local network. tmpfiles.org via Cloudflare usually works.

### 7. Output to user

```
[OK] 合并完成: X src1 + Y src2 + Z src3 = Total 节点
订阅地址: https://tmpfiles.org/dl/xxxxx/merged_sub.yaml
```

## Supported Protocols

| Protocol | Clash Type | Notes |
|----------|-----------|-------|
| Shadowsocks | `ss` | All ciphers |
| Trojan | `trojan` | TLS/WS transport |
| VLESS | `vless` | Reality/TLS/WS, needs Mihomo |
| Hysteria2 | `hysteria2` | Needs Mihomo |
| VMess | `vmess` | All transports |

## Important Notes

- Output format is **Clash Meta (Mihomo)** — not compatible with original Clash
- VLESS Reality and Hysteria2 require Mihomo-based clients (Clash Verge Rev, mihomo Party, NekoBox)
- Filter out info nodes (127.0.0.1, traffic remaining, expiry date)
- Verify YAML validity before upload
- Upload links are temporary — tell user TTL

## Files

- `SKILL.md` — This file
- `merge_sub.py` — Standalone Python merge script (no external deps, uses yaml stdlib)
