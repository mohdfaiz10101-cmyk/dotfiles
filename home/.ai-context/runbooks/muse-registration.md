# Meta Muse registration verification

## Observed 2026-10-23

- Registration entry: https://muse.ai/ ; official product page: https://ai.meta.com/muse/ .
- Existing mihomo HTTP proxy: 127.0.0.1:7890.
- Email verification succeeded; authenticated page redirects to `/access`, showing `You’re on the waitlist` and country/region unavailability. This is not successful product activation.
- A temporary loopback mihomo listener on 17890 selected the existing US Trojan node. Browser Cloudflare trace reported `loc=US`; the same authenticated account still showed the waitlist. A US exit alone did not activate this account. Do not generalize this into a claim about Meta’s unpublished eligibility criteria.
- Temporary listener was removed and configuration hot-reloaded after testing; original proxy selection preserved.
- Never promise permanent regional eligibility or unlimited quota.
- Filling the six-digit verification input can submit automatically; inspect current UI before clicking Confirm. Expired login sessions require a new code.
- Evidence: ~/.local/state/muse-registration/us-result.png and waitlist.png. Persistent isolated browser profile: ~/.local/state/muse-registration/browser (private, contains authentication state). Do not print or share its cookies/tokens.

## Search follow-up 2026-10-23

- First-person report updated 2026-10-18: https://lazy-cv.com/blog/zh-TW/notes/how-to-use-muse . Author reports an existing waitlisted email still failed on VPN, existing Meta account failed, and a fresh email succeeded. This is anecdotal, not proof that waitlist state is permanent.
- First-person walkthrough dated 2026-10-01, updated 10-02: https://www.kocpc.com.tw/archives/670693 . Reports US VPN + incognito + fresh email, followed by birth date and age verification. Article includes referral/affiliate incentives.
- Direct community post: https://www.reddit.com/r/MetaAI/comments/1x1o1bv/still_cant_sign_up_for_meta_muse_even_with_a_vpn/ . Also recommends fresh email and US VPN; not official or independently reproduced here.
- Referral bonus tokens must not be conflated with waitlist access or unlimited usage.
- Before any NEW registration attempt, verify the intended egress first and preserve it through email verification. In this session the first email submission used the default proxy, and US egress was only tested later; do not claim a clean first-registration US test was performed.

## Fresh signup follow-up

- Used a separate durable browser profile `~/.local/state/muse-registration/browser-us`, CDP loopback `127.0.0.1:9227`, and a dedicated mihomo mixed listener `127.0.0.1:17890` named `muse-registration-us`, targeting existing node `美国-US-3-流量倍率:1`. This second attempt leaves that listener in place to preserve the authenticated browser path; it does not change global proxy selectors.
- Browser Cloudflare trace confirmed `loc=US` BEFORE initial email submission and AGAIN AFTER the result.
- Fresh email verification passed, user supplied required identity fields, and the account creation form was submitted. Muse then redirected to `/access` with `Join the waitlist for Muse` and country/region unavailability. The `Join waitlist` button was deliberately not clicked. Product activation did not succeed.
- Thus the fresh-email + isolated-browser + US-egress tutorial was attempted here and did NOT bypass this restriction. Do not keep teaching it as a confirmed fix or imply a different outcome without new evidence. Actual provider eligibility logic remains unknown.
- Evidence: `~/.local/state/muse-registration/fresh-us-region-blocked.png`. Do not copy identity information, OTPs, or cookies into runbooks.

## Shared skill

- Canonical reusable instructions: `~/.shared-agent/skills/devops/muse-account-access/SKILL.md`. No identity details, OTPs or authentication exports are stored there.
- Hermes reads the shared source; Codex lean, Claude, OpenCode and standard `.agents/skills` use targeted symlinks. Codex lean selection is persisted in `~/.local/bin/codex-skills-mode`.
- OpenHands uses its generated `~/.openhands/skills/muse-account-access.md`; semantic content checked against shared source and actual `load_user_skills()` confirmed discovery.
- Loader verification exposed invalid YAML `name: [MAIN] memory-curator` in the existing memory-curator skill. Corrected name to `memory-curator` and moved legacy tags under metadata in the shared source and OpenHands generated file; both changed skills pass quick_validate.

## Existing-account login recovery (2026-10-24)

- User-provided Hermes session links can point to unfinished work: read `/api/session?session_id=<id>&messages=1&resolve_model=0` and identify the actual task before diagnosing WebUI.
- Existing requested account now authenticated in Meta and Muse. Muse chat rendered previous history and answered a minimal verification with `连接正常`. This is separate from the earlier fresh-account waitlist tests.
- Native headed Chromium started independently under user systemd and controlled with Playwright CDP; no protocol incompatibility was observed on this route. `navigator.webdriver=false`; US proxy trace `loc=US`, `colo=SJC`.
- Current unit `meta-account-browser.service`, CDP loopback `9231`, private profile `~/.local/state/muse-registration/meta-headed`, dedicated US proxy `17890`. Never copy authentication state into this runbook.
- Reopen after reboot, first verify no existing instance/port conflict and that 17890 is still the intended US route:
  `systemd-run --user --unit=meta-account-browser --collect --setenv=DISPLAY=:0 --setenv=WAYLAND_DISPLAY=wayland-1 --setenv=XDG_RUNTIME_DIR=/run/user/1000 /usr/bin/chromium-browser --user-data-dir=/var/home/charlie/.local/state/muse-registration/meta-headed --remote-debugging-address=127.0.0.1 --remote-debugging-port=9231 --proxy-server=http://127.0.0.1:17890 --no-first-run --no-default-browser-check https://muse.ai/`
- Email route verified: accountscenter.meta.com → Login and security → Contact info → Add new contact info → Add email. New email input is available. Await user target email, confirm ownership before removing any old contact. No email/phone was removed or changed.
- dev.meta.ai developer OIDC still reports `Token exchange failed. Please try again.` even in the same working headed browser. Cause remains unproven; do not generalize to Muse login or promise manual login fixes it. API key retrieval was an earlier agent-added detour, not required for the original Muse login/email task.
- Private account record: `~/workspace/muse-account.json`, mode 0600. Evidence screenshot: `~/.local/state/muse-registration/meta-evidence/muse-chat-verified.png` (may contain account conversation; keep local).

## 手机 Muse (com.facebook.aura) 一直"正在重新连接" — 根因与永久修复（2026-10-24）

### 真实 app 身份（先搞错过一次，别再查 stella）
- 手机上跑 Muse 的是 **`com.facebook.aura`**（Meta AI app，版本 13.0.0.0.144），
  通知栏"Muse正在后台运行"由它发出。
- `com.facebook.stella`（295.0.0.37.164）是**另一个** app（可穿戴/眼镜伴侣），
  不是手机 Muse。别用 `pm list packages | grep stella` 找手机 Muse。
- aura 入口：`com.facebook.aura/.main.AuraMainActivity`
  （用 `cmd package resolve-activity -c android.intent.category.LAUNCHER com.facebook.aura` 核实）。
- 手机侧 PKR110 有守护进程抢前台，`am start` 后可能被 Brave 抢回，
  `uiautomator dump` 会抓到浏览器内容；以 `topResumedActivity` 和 screencap 为准。

### 根因：DNS 污染 → GeoIP 判 CN → 走 DIRECT
mihomo 的 `dns` 段**没有 `enhanced-mode: fake-ip`**（默认 redir-host），
国内 resolver（223.5.5.5 / 119.29.29.29 / alidns / doh.360）对
`muse.ai` / `meta.ai` / `hatch-api.meta.ai` / `graph.meta.ai` 返回被污染的 A 记录，
GeoIP 命中 `cn`，于是 `MATCH,PROXY` 之前的 GeoIP CN 规则把它判成 DIRECT，
MUSE-US 规则根本没机会生效。app 侧表现为无限"正在重新连接"。

电脑侧同样缺 `respect-rules`，`nameserver` 是国内 DNS，日志可见
`dial DIRECT (match GeoIP/cn)`。

### 修复（电脑侧 /etc/mihomo/config.yaml + 手机侧 /data/adb/mihomo_netbird/config.yaml）
1. `dns.enhanced-mode: fake-ip`（手机补 `fake-ip-range: 198.18.0.1/16`）
2. `dns.respect-rules: true` —— 让 nameserver-policy 优先于主 nameserver
3. 电脑侧 `nameserver` 把 114 换成 119.29.29.29，`fallback` 改 DoH
   （https://1.1.1.1/dns-query、https://8.8.8.8/dns-query）
4. 手机侧 `fallback-filter.domain` 追加 `+.muse.ai` / `+.meta.ai` / `+.meta.com`

改后用**手机侧 mihomo controller** 验收，这是唯一可信证据：
```
adb -s 192.168.5.211:5555 shell 'su -c "curl -s http://127.0.0.1:9000/connections"'
```
必须看到 `hatch-api.meta.ai` / `graph.meta.ai` / `graph.facebook.com`
的 chains 都是 `['美国-US-3-流量倍率:1', 'MUSE-US']`。

### 手机侧链路（已存在，别重建）
`/data/adb/muse-us-ensure.sh` 把 aura 的 UID 流量全部导入 `MUSE_US` iptables 链：
- TCP → REDIRECT 127.0.0.1:17890（listener `muse-us-app`, proxy MUSE-US）
- 目的 7890/7891 → REDIRECT 17891（保留 CONNECT/SOCKS 语义）
- UDP 非 53 → REJECT；ip6tables 全 REJECT（堵 QUIC/IPv6 泄漏）
- `/data/adb/service.d/98-muse-us.sh` 每 30s 跑一次 ensure；`97-mihomo.sh:151` 也调它。
所以**不需要**给 aura 单独设 http_proxy，也不该动 VPN 槽位。

### 备份位置
- 电脑：`/etc/mihomo/config.yaml.before-dns-fix-<ts>`，另存 `config.yaml.last-good`
- 手机：`/data/adb/muse-us-backup/config.before-<ts>.yaml`

### 验证 Muse 出口的正确方法（重要）
- `curl -x http://127.0.0.1:17890 https://www.cloudflare.com/cdn-cgi/trace` 会显示
  `loc=CN`，因为该域名不在 MUSE-US 规则内，走默认直连。**不能据此说没修好**。
- https 目标 + `-x proxy` 时 curl 会**自己解析 DNS 后直连**，得到 000 超时，
  这是测试假象，不是链路故障。用 `http://` 目标测（得 301），
  或直接看 mihomo controller 的 connections/chains。

## PKR + Firefox fixed US access (2026-10-24, final configuration)

User preference: keep the existing email, sign into Firefox and the native PKR app, keep a stable US exit, and work on 5G after unplugging USB. No email was changed.

- Firefox uses the existing default profile `~/.config/mozilla/firefox/22e0ld4w.default-release`. Cookies/storage are retained, startup restores tabs. Actual refresh and full Firefox restart preserved Muse login. `firefox.service` remains enabled; temporary Marionette/geckodriver control was removed/stopped.
- Official package identity checked against Google Play: `com.facebook.aura`. Installed Meta-signed Muse `13.0.0.0.144` from Uptodown after Play/Aurora rejected the store region. APK and certificate metadata: `~/.local/state/muse-registration/apk/verified.json`. ADB installation required the ColorOS bottom Install button, which UI XML omitted; use a screenshot.
- Final path: PKR Muse UID 10043 → phone root Mihomo MUSE-US (single member MUSE-US-PINNED) → existing home WireGuard → authenticated Fedora `192.168.5.144:17892` mixed listener → Fedora fixed US Trojan → Internet. Other apps retain existing phone proxy rules. USB is only an optional management path.
- Dependencies: home `charlie-home` WireGuard remains active and Fedora remains online. No alternate-region or DIRECT fallback is configured. Same node labels or even the same relay IP do NOT prove the same public exit: the subscription assigned different IPv4/IPv6 exits to direct phone vs PC connections. Routing only Muse through Fedora made both exits match.
- Fedora fixed relay is a separate proxy alias `MUSE-US-PINNED`, endpoint IPv4 pinned with original TLS SNI retained; existing subscription nodes stay unchanged. Local dedicated `17890` and domain rules use it. Phone-facing listener `17892` has a separate random credential, stays LAN-only, and firewalld accepts only router SNAT `192.168.5.1/32` and local PKR `192.168.5.211/32`. No WAN mapping was added.
- Phone private relay fragment `/data/adb/muse-us-node.yaml` is mode 600; the host copy and authentication material are under `~/.local/state/muse-registration/persistent-us/` (private). Never print those files or copy credentials into skills/logs.
- Phone loopback listeners: Mihomo redir `17890`, mixed `17891`, and Muse-only TLS/SNI bridge `17893`. MUSE_US handles the app UID's local HTTP/SOCKS proxy connections as well as direct TCP. Non-DNS UDP and IPv6 are rejected only for that app to prevent unproxied paths.
- Root cause of native reconnecting: TLS ClientHello captured SNI `hatch.metaaivm.com`, while a direct connection dialed a stale/bad resolved address and received zero response bytes. Clean proxy-side DNS alone did not repair that native socket path. `/data/adb/muse-tls-sni.py` recovers SNI and forwards unchanged TLS bytes via local SOCKS; it does not decrypt TLS. The parser was tested against the captured real ClientHello.
- Bridge uses explicit `/data/data/com.termux/files/usr/bin/python3`. `/data/adb/service.d/98-muse-us.sh` supervises it and reapplies UID rules every 30 seconds; lock/PID files prevent duplicate guard/bridge instances. Repeated ensures did not grow iptables rules.
- `/data/adb/muse-config-apply.sh` injects the pinned private node, group/listeners, Meta/Muse rules and encrypted DNS policy during `/data/adb/mihomo-sync-netbird.sh`. It includes `metaaivm.com`. Overlay YAML validation and applying it twice produced identical hashes. `/data/adb/service.d/97-mihomo.sh` retains the Muse UID hook when rebuilding normal rules.
- Default reapply command: `~/.local/bin/muse-us-lock --serial <working-PKR-serial>`. It first reads the current phone config and modifies only Muse sections, validates on-device, backs up, hot-reloads the existing single Mihomo, and deploys helpers. Sources: `~/.local/libexec/muse/`. Do not restore an old whole-phone snapshot over newer unrelated edits.
- Verified on real cellular `rmnet_data5`, no USB device in adb inventory, control via independent FRP `127.0.0.1:15555`: app UID requests and Fedora requests both returned IPv4 `23.142.224.238`, IPv6 `2604:a840:3:1e0::3017`, Cloudflare `loc=US`, `colo=SJC`. These are observed exits, not ownership or lifetime guarantees from the provider.
- Actual screenshots are required: the Android UI tree omitted visible “正在重新连接” text. Final screenshot after the SNI fix showed the chat without that status. Preserve this boundary; don't declare UI health from XML absence alone.
- Scope: native Muse login/connection and Firefox are handled separately from dev.meta.ai's historical OIDC error. No developer API key is needed for this web/native task.
