# Runbook: Codex Multi-Account Routing

Codex 三账号并行、互补和省钱路由规划。

## Current State

- Account 1: `CODEX_HOME=~/.codex`, tmux socket `/run/user/1000/tmux/codex.sock`, session `haven-codex`, Haven/WebTTY entry `2225` / `19899`. Public `19899` is a direct local socket proxy (`codex-public-19899-proxy.socket` -> `127.0.0.1:19000`); do not route C1 public WebTTY through same-host FRPS -> FRPC loopback again.
- Account 2: `CODEX_HOME=~/.codex-2`, tmux socket `/run/user/1000/tmux/codex2.sock`, session `haven-codex2`, local WebTTY gate `19001`, public WebTTY entry `19900`, Sub2API key `codex2-sub2api` bound to group `openai-codex-2` / `group_id=11`. As of 2026-07-17, it is bound to upstream account `15` named `Franciscastillo47795`, status `active`, `proxy_id=2`, no fallback. It is not unbound/dead, but Sub2API marked the upstream rate-limited at `2026-07-17T10:10:28Z` with reset `2026-07-23T04:54:51Z`; `/v1/models` returns 200 while `/v1/responses` returns 503 because account selection reports `no available accounts`. Do not clear this rate-limit flag manually unless a fresh real response proves recovery; rotate/rebind C2 if immediate use is needed.
- Account 3: `CODEX_HOME=~/.codex-3`, tmux socket `/run/user/1000/tmux/codex3.sock`, session `haven-codex3`, Haven/WebTTY entry `2229` / `19902`.
- Account 4: `CODEX_HOME=~/.codex-4`, tmux socket `/run/user/1000/tmux/codex4.sock`, session `haven-codex4`, WebTTY entry `19903`, Sub2API key `codex4-sub2api` bound to group `openai-codex-4` / `group_id=14`. As of 2026-07-14, group 14 is bound only to upstream account `16` named `k2 team`; it uses `proxy_id=1` and no fallback.
- Account 5: `CODEX_HOME=~/.codex-5`, tmux socket `/run/user/1000/tmux/codex5.sock`, session `haven-codex5`, local WebTTY gate `19004`, backend `19889`, Workbench short link `/go/c5`, public WebTTY entry `19904`, Sub2API key `codex5-sub2api` bound to group `openai-codex-5` / `group_id=16`. As of 2026-07-15, group 16 is bound only to OAuth upstream account `18` named `C5 OAuth`; it uses `proxy_id=1` and no fallback. Public path is router `19904/TCP -> 192.168.123.71:19904`, FRP `fedora-codex-tty-19004` `remotePort=19904` -> local `19004`.
- Account 6: `CODEX_HOME=~/.codex-6`, tmux socket `/run/user/1000/tmux/codex6.sock`, session `haven-codex6`, local WebTTY gate `19005`, backend `20020`, Workbench link `/go/c6`, public WebTTY entry `19905`, Sub2API key `codex6-sub2api` bound to group `openai-codex-6` / `group_id=17`. Public path is router `19905/TCP -> 192.168.123.71:19905`, FRP `fedora-codex-tty-19005` `remotePort=19905` -> local `19005`. As of 2026-07-20, C6 account identity is upstream `19` (`GPT Team JSON · 20260715`), but that workspace is deactivated. C6 may use lower-priority upstream `15` only for task continuation; do not present `15` as the C6 account identity. Slot smoke through C6 returned HTTP 200 via task fallback `15`.

- Account 7: `CODEX_HOME=~/.codex-7`, tmux socket `/run/user/1000/tmux/codex7.sock`, session `haven-codex7`, local WebTTY gate `19006`, backend `20021`, Workbench link `/go/c7`, public WebTTY entry `19906`, Sub2API key `codex7-sub2api` bound to group `openai-codex-7` / `group_id=18`. Local services are `ttyd-codex7.service`, `ttyd-codex7-backend.service`, and `haven-codex7.service`; FRP proxy is `fedora-codex-tty-19006` `remotePort=19906` -> local `19006`; router NAT is `19906/TCP -> 192.168.123.71:19906`; Fedora firewalld allows `19906/tcp`. As of 2026-07-17, the delivered日抛 Plus account is phone-bound and imported as upstream account `20` named `C7 day Plus`; it uses `proxy_id=1`, status `active`, no fallback. The chongpt SMS CDK state file is `~/.local/state/codex-sms/c7-chongpt-20260716.json` (`0600`, preview `SMS8...9MWLN`, status `used`).
- Account 8: `CODEX_HOME=~/.codex-8`, tmux socket `/run/user/1000/tmux/codex8.sock`, session `haven-codex8`, local WebTTY gate `19007`, backend `20022`, Workbench link `/go/c8`, public WebTTY entry `19907`, Sub2API key `codex8-sub2api` bound to group `openai-codex-8` / `group_id=19`. Local services are `ttyd-codex8.service`, `ttyd-codex8-backend.service`, and `haven-codex8.service`; FRP proxy is `fedora-codex-tty-19007` `remotePort=19907` -> local `19007`; router NAT is `19907/TCP -> 192.168.123.71:19907`; Fedora firewalld allows `19907/tcp`. As of 2026-07-17, the delivered 日抛 Plus account is phone-bound and imported as upstream account `21` named `C8 day Plus`; group `openai-codex-8` is bound only to upstream `21`, status `active`, `proxy_id=1`, no fallback. The same chongpt SMS CDK state file used for C7 remains at `~/.local/state/codex-sms/c7-chongpt-20260716.json` (`0600`, preview `SMS8...9MWLN`) and recorded the additional C8 binding without exposing the full CDK. C8 is now an API/Sub2API slot, so `/quota.json` must show `ok=true`, `sub2api.bound_account_count=1`, `sub2api.account.id=21`, `usage_source=sub2api-postgres`, and `official_possible=false` rather than `sub2api.unbound=true`. If C8 ever returns to zero `account_groups` rows, `ttyd-codex8-entry` / `haven-codex8-ensure` should run `~/.local/bin/codex8-prepare-login-mode` so the pane shows the Codex ChatGPT/API login selector instead of a 503 loop.
- Account 9: `CODEX_HOME=~/.codex-9`, slot created on 2026-07-20. The real AF63 card was retrieved from `https://gpt.jinpai.lat/api/redeem` as `sub2_json`, imported through Sub2API admin `/api/v1/admin/accounts/batch`, and bound to upstream account `25` (`HalbertTaladay0446@outlook.com`) with `proxy_id=1`; C9 slot smoke returned HTTP 200. Earlier local raw exports mapped to upstream accounts `23/24`, both `402 deactivated_workspace`; they were removed from task pools and must not be reused. C9 has no fallback by default.
- Account 10: `CODEX_HOME=~/.codex-10`, API/Sub2API-only slot as of 2026-07-20; no WebTTY/Haven services are installed yet. Delivered iCloud Plus credentials are stored only in `~/.local/state/codex-account-import/c10-icloud-plus-20260720.secret` (`0600`) and must not be printed. Codex device-auth succeeded and `~/.codex-10/auth.json` was imported with `codex-sub2api-json-bind` as upstream account `22` named `C10 iCloud Plus`, `status=active`, `schedulable=true`, `plan_type=plus`, `proxy_id=1`. Slot group/key/env: `openai-codex-10` / `group_id=27`, API key name `codex10-sub2api`, env `~/.config/codex10-sub2api.env`. Primary upstream `22` is currently rate-limited until `2026-07-25T05:56:07.723074Z`, so `codex-fallback-pool-repair --apply` keeps upstream `22` at priority `100` and adds rescue upstream `10` at priority `10`. Verification on 2026-07-20: `/v1/models` returned HTTP 200; a tiny `/v1/responses` smoke returned HTTP 200 and usage logged under upstream `10`, proving fallback works while C10's own primary remains independently visible as limited.
- 2026-07-20 C10 doubt/verification: do not assume a freshly added seller account is the intended identity merely because `codex login --device-auth` succeeded. Sub2API admin direct test against upstream account `22` returned SSE error `API returned 429` with upstream body fields `type=usage_limit_reached`, `plan_type=plus`, `resets_at=1784958966` (`2026-07-25T05:56:06Z`), so the limit is real upstream feedback, not an AI guess. More importantly, redacted identity correlation showed upstream accounts `21` and `22` share the same OpenAI `sub_hash` and extra email hash while their token hashes differ, meaning C10 likely authorized the existing C8 browser/OpenAI account again instead of the delivered iCloud account. To fix, redo C10 device auth in a clean/isolated browser profile or logged-out real Chrome session, verify the visible OpenAI/ChatGPT email before approving Codex, then re-import with `codex-sub2api-json-bind`. Never print the email or token; compare only hashes.
- Codex account management is now script-owned by `~/.local/bin/codex-account-manager`. Default `summary` is read-only and writes `~/.local/state/codex-account-manager/latest.json` plus `.md`; it classifies each slot as primary/fallback/rate-limited, records reset times, last actual usage account, last Sub2API error evidence, and duplicate identity hashes. `direct-test --account-id <upstream>` calls Sub2API admin `POST /api/v1/admin/accounts/:id/test` to probe one upstream directly, bypassing fallback, and stores only redacted evidence. `codex-account-manager.timer` refreshes the DB-only snapshot every 5 minutes; direct tests remain manual so the monitor does not burn quota.
- 2026-07-20 account identity vs fallback rule: account info must show only the slot's independent primary upstream. Fallback is task-continuation/rescue capacity only and must not be counted as that slot's identity. Use `~/.local/bin/codex-account-registry` and read `~/.local/state/codex-account-audit/registry.md` for the non-confusing table. Current examples: C6 identity is upstream `19` (workspace deactivated) while fallback `15` can continue tasks; C9 identity is upstream `25` and is independently usable.
- 2026-07-20 config sync guard: secondary `~/.codex-[2-8,10]/config.toml` files briefly contained duplicate `model_provider` / `[model_providers.sub2api]` entries after shared sync. `~/.local/bin/codex-shared-sync` now treats an existing `[model_providers.sub2api]` as already present, and all `~/.codex*/config.toml` files validate with Python `tomllib`. Keep this validation after future account/MCP syncs.
- Language and expert reply behavior: all account configs `~/.codex*/config.toml` carry
  `instructions` and `developer_instructions` rules requiring conversational
  replies in Simplified Chinese regardless of the user's input language, while
  preserving required original language for code, commands, paths, identifiers,
  logs, quotes, and explicitly requested foreign-language artifacts. As of
  2026-07-18 they also enforce expert-fast concise replies: direct answer first,
  short bullets/checklists, minimal caveats, one blocking clarification at most,
  targeted inspection, safe changes, and verification. The same rule is also in
  `/var/home/charlie/AGENTS.md` and `~/.codex/AGENTS.md`; secondary slots
  `~/.codex-2` through `~/.codex-8` plus `~/.codex-10` link `AGENTS.md` to `~/.codex/AGENTS.md`.
  `~/.local/bin/codex-account-provision` and `~/.local/bin/codex-shared-sync`
  must keep this behavior in generated or synced account configs.
- Local desktop console: `~/.local/bin/codex-foot-tabs all` opens every
  discovered Codex Foot tab, each attaching to the same per-account tmux
  session as WebTTY. Discovery is based on `ttyd-codex*-entry` and
  `haven-codex*.service`, with account 1 represented by the base
  `ttyd-codex-entry` / `haven-codex.service` names.
  `codex0` is the shell command alias for this combined local console.
  `Super+F1` through `Super+F8` open or focus one account when keybindings are
  present; `Super+Shift+C` opens or focuses all discovered accounts. This
  launcher must use plain tmux attachment via the existing
  `ttyd-codex*-entry` programs, never `attach-session -d`, and must unset
  `TMUX` / `TMUX_PANE` before launching Foot clients so a tmux-originated
  environment cannot make local Foot attach clients exit immediately.
- Desktop health sorting: `codex-foot-tab-sort.timer` runs every 2 minutes,
  using the same loopback WebTTY `quota.json` fields that drive account-button
  availability: active upstream rate limit, workspace availability, and
  Sub2API account `status`/`schedulable`. It restores any missing discovered
  local Foot account view, then orders tabs with the same group/score policy as
  the WebTTY/Workbench account buttons: `有额度`, `额度少`, `限额/不可用`,
  then `未知`; within a group it sorts by quota score descending and then
  account number. `Super+Ctrl+S` runs the sort immediately.
  It does not stop or rotate accounts. Automatic maintenance never focuses a
  tab and defers sorting whenever a Codex Foot tab is focused, so it cannot
  interrupt typing.
- 2026-07-17 local Foot seven-account stabilization: the old short-lived
  5-second maintainer loop caused the local tab panel to flicker between partial
  and complete account sets. Keep only `codex-foot-tab-sort.timer` at
  `OnUnitActiveSec=2min`; the service must call `codex-foot-console-maintain`,
  which repairs all discovered `ttyd-codex*-entry` / `haven-codex*.service`
  slots before sorting. Sway must include `Super+F7` for C7, route
  `foot-codex[0-9]+` dynamically to workspace 1, and use `no_focus` for new
  timer-created Codex Foot windows while explicit hotkeys still focus the
  requested tab.
- Sway routing for the local Codex console must use dynamic regexes such as
  `foot-codex[0-9]+`, not fixed `1-7` ranges. Generic title-based AI rules
  must explicitly exclude `foot(-codex[0-9]+)?` so Codex Foot terminals always
  remain tiled on workspace `1`, including future C8+ slots.
- Mobile action preference (2026-07-20): when a Codex/account purchase/login/payment/confirmation page needs user action, default to a phone direct browser open of the target page; use Workbench manual-action cards only as fallback. Do not only reply with a URL unless pushing is unavailable.
- Merchant checkout flow (2026-07-20): when the user supplies contact/safety code for a specific purchase, the agent may auto-submit the merchant order form up to the payment page, using the shop's own payment channel (for this shop the fast path is `支付宝电脑收款`). The handoff point is the merchant payment URL such as `/shopApi/Pay/payment?trade_no=...`; at that point stop and let the user finish payment manually. For repeatability, use the same pattern: item page -> auto fill contact/query code -> create order -> open payment URL in phone popup.
- Purchase execution flow (2026-07-20): for a specific shop item such as `f19y5u`, open the item page in a phone manual-action popup, keep the merchant checkout on the merchant side, and use the merchant channel named `支付宝电脑收款` when available. Do not try to perform payment inside Workbench; the agent may prepare the page, confirm the item, and present the channel choice, but final payment and checkout fields remain user-handled. If the user wants a repeated pattern, keep the popup title as `购买 <goods_key>` and the message as `20元内优先 / ChatGPT/OpenAI / 免接码优先 / Cursor可用加分`.
- Post-payment fetch rule (2026-07-20): after payment succeeds, the merchant often requires `/order` plus the buyer's reserved contact/order number and a human verification ticket before `/shopApi/Order/list` or `/shopApi/Order/info` will return cards. If the bot wall blocks direct HTTP, do not keep hammering curl; push a phone manual-action popup for the order query page and wait for the user to complete the verification, then continue with extraction/import.
- Purchase preference update (2026-07-20): procurement defaults now prefer ChatGPT/OpenAI accounts over any non-ChatGPT product. Within ChatGPT items, `免接码优先` comes first, `Cursor可能` is a positive tag, and `需接码` stays a fallback only when no免接码 option is available.
- Codex purchase planner page (2026-07-20): Mobile AI Workbench `/codex-purchase?device=<code>` is now the default user-facing procurement page. It dynamically fetches `https://pay.ldxp.cn/shop/G09AC5SS`, filters GPT/OpenAI/Codex products, scores them against current C1-C10 health from `~/.local/state/codex-account-manager/latest.json`, and presents user-facing slot labels (`C1`...`C10`) plus product buckets (`首选`, `可买`, `只作配件/测试`, `不建议`). The current recommendation is: least problems = official direct recharge to a clean personal account; for quick new slot such as C9, buy an independent Plus account only with explicit Codex support plus long-lived US Codex SMS if phone binding is needed. Avoid Team/K12/workspace, short first-login warranty JSON, one-time SMS, and products saying `未绑定手机`/`自行接码` unless explicitly doing a low-cost test. Verification: `curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/api/codex-purchase/products | jq '.ok,.products[:5]'` and `/codex-purchase?device=w19900422` returns a visible page.
- Account status presentation preference (2026-07-20): when explaining account health or purchase strategy to the user, translate Sub2API upstream ids into Codex slot labels such as `C6 / Codex账号6` and include plain attributes (`独立`, `共享`, `限额`, `失效`, `备用`, `可用`, `慢风险`). Avoid presenting many bare numeric upstream ids unless needed for commands or verification.
- Account purchase strategy (2026-07-20): for future buys, prefer a clean personal OAuth/Plus account with a unique email/sub identity, verified on a logged-out/isolated browser, then imported once into one slot only. Avoid shared seller pools, duplicate identities, reused browser logins, and workspace/team accounts that can return `deactivated_workspace` or cross-slot rate-limit coupling. The least-problem pattern in current stats is a slot whose primary is `usable`, `runtime_schedulable_now=true`, `active_rate_limit=false`, and whose `sub_hash`/`email_hash` does not match older slots. Temporary fallback may be used for emergency continuity, but it should not define the purchase target.
- C6 repeatable update sequence: run `codex-sub2api-json-bind --account 6 ... --restart --health-check --json`; ensure `ttyd-codex6.service` and `ttyd-codex6-backend.service` are active; retain C6 in Workbench's `accounts` list and proxy `allAccountStatus()`/quota snapshots. The main account-status group uses the single injected `codex_account6_stable_card`, which refreshes C6's `运行中`/`有结果`/`异常` badge from `/sessions.json` without a DOM-observer feedback loop. Verify C6 with `curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19000/sessions.json | jq '.accounts[] | select(.account=="6")'`.
- C6 switch regression (2026-07-16): C5/C6 services can be healthy while the account card does nothing if injected UI helpers still validate only `^[12345]$` or map ports only through C5. In `~/.local/bin/ttyd-device-gate-proxy`, every account validation, port array, and top-level pinned-port map must include C6 (`1-6`, `19005`, `19905`). Account cards now use a normal top-level page navigation for C6; do not restore the old `codex_top_level_frame_host`, `codex_c6_click_fix`, or `codex_c6_pin` iframe behavior. It caused iOS/WebKit to show ttyd `Try again` and left competing click/timer handlers. Restart all six `ttyd-codex{,2,3,4,5,6}.service` gates after shared UI changes, then verify C6 `/token`, a WebSocket `101` upgrade, and `/status` with the device code.
- C6 public `Try again` repair (2026-07-16): `19905 -> 19005` can be fully healthy on Fedora and FRP yet remain unreachable on the phone when Fedora firewalld lacks `19905/tcp`. The router must have `vts_port_x39=19905`, `vts_lport_x39=19905`, `vts_ipaddr_x39=192.168.123.71`, and `vts_proto_x39=TCP`; after NVRAM commit, run `/sbin/restart_firewall`. On Fedora run `sudo firewall-cmd --permanent --add-port=19905/tcp` and `sudo firewall-cmd --reload`. Verify router-to-host with `wget http://192.168.123.71:19905/?device=<code>&view=frame`, then use `curl --noproxy '*' http://charlie1990.duckdns.org:19905/?device=<code>&view=frame` and require HTTP 200.
- Mobile iframe authentication rule: in `ttyd-device-gate-proxy`, `?device=<code>&view=frame` must set the account cookie but must not 302 away the `device` query. iOS/WebKit can otherwise load an unauthenticated terminal WebSocket and render ttyd's “Try again”. Verify a frame URL returns `200` plus `set-cookie`, not `302`.
- C6 `异常` recovery: if `/sessions.json` reports `codex6.sock (No such file or directory)` while both C6 WebTTY services are active, restore only the missing tmux session with `systemctl --user start --no-block haven-codex6.service`. This is a successful oneshot service and returns to `inactive (dead)` after creating the detached tmux server; verify `curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19005/status | jq '{ok,account,error}'` and then refresh `/sessions.json`. Do not rotate the upstream account or restart Sub2API for this local-session condition.
- Fixed account egress: Codex OpenAI traffic must never use Mihomo `AUTO`. The stable mapping is C1/C3/C6/C7/C8 -> `美国-US-3`, C2 -> `荷兰-NL-4`, C4 -> `德国-DE-2`, C5 -> `德国-DE-3`. Mihomo owns loopback-only mixed listeners `7892` through `7897`, groups `OPENAI-C1` through `OPENAI-C6`, and default `OPENAI-STABLE` is C1's US node. Until dedicated C7/C8 listeners are created, C7 and C8 entry scripts reuse C6's stable `7897` path. Sub2API upstreams are bound to proxies `codex-c2-nl:7893`, `codex-c3-us:7894`, `codex-c4-de:7895`, `codex-c5-de:7896`, and `codex-c6-us:7897`; restart `sub2api.service` after any change. C1 is native and its terminal entry uses `7892` directly. The WebTTY `更多` account cards inject `codex_account_egress_labels` and must visibly show `节点 <name>`; Workbench `/api/status` exposes the same `node` value. Verify group selection with Mihomo's loopback controller, Sub2API bindings using only proxy names/ports, and `curl ... http://127.0.0.1:19090/v1/models` with each slot-local API key. Do not print keys or proxy credentials.
- C5 auth-state rule: the terminal deliberately uses its local Sub2API API key
  as the front door, while upstream account `18` is the real OpenAI OAuth
  session. Therefore `codex login status` reporting API-key mode is expected;
  verify OAuth with `/quota.json` (`C5 OAuth`, id `18`) and a successful
  `/v1/responses` health check. Label Workbench and WebTTY `OAuth`, not
  `未 OAuth`.
- C5 response-stall repair: if `/v1/models` returns 200 but a simple prompt
  remains `Working`, verify upstream account `18` has `proxy_id=1`, restart
  `sub2api.service`, then run `codex-account-provision --account 5
  --primary-account-id 18 --restart --health-check --json`. This recreates the
  stale tmux session only after a real response returns 200.
- C5 account entry: individual Codex WebTTY has a main-bar `账号` link and a
  second `账号` link inside the expanded `更多` panel; both open Workbench
  `/buttons` for the five-account panel. Do not put this low-frequency entry
  in the Workbench homepage header or taskbar.
- C5/C6/C7 quota display repair: `ttyd-device-gate-proxy` must treat every
  Sub2API slot `2-7` as eligible for `sub2apiQuotaFor`, including when no
  Codex `token_count` event exists. Otherwise aggregate `/quota.json` from a
  different account gate can show C6/C7 as empty or incorrectly reuse the
  current gate's Sub2API key. Restart only gate services, not backend/tmux,
  then verify `http://127.0.0.1:19000/quota.json` shows
  `codex6-sub2api`/upstream `19` for C6 and `codex7-sub2api`/upstream `20`
  for C7.
- C5 page-stuck/narrow-pane repair (2026-07-17): if `19004/status` is healthy
  and `/quota.json` shows `codex5-sub2api` bound to active upstream `C5 OAuth`,
  but the phone page is blank, stuck, or not showing, check tmux clients first:
  `tmux -S /run/user/1000/tmux/codex5.sock list-clients -F '#{client_tty}
  #{client_width}x#{client_height}'`. A stale `2x1` or very narrow WebTTY
  client can shrink the visible pane. Detach only the narrow clients, set
  `window-size manual`, resize `haven-codex5` to `100x30`, and recheck
  `/status`. If a narrow client immediately reappears, restart only
  `ttyd-codex5.service` to reset WebTTY browser connections, then resize again.
  Do not rotate C5, restart Sub2API, or restart the backend/tmux session for
  this UI-layer condition.
- C5 dock-visible/terminal-blank repair (2026-07-17): if the phone shows the
  C5 right-side account dock but the terminal body is blank while tmux
  `capture-pane` has Codex text, verify the real phone with ADB screenshot
  before trusting headless Chromium. Headless Chromium can falsely show only
  the resize badge. The durable C5 fix is: keep `ttyd-codex5-entry` aligned
  with `haven-codex5-ensure` by exporting and passing `CODEX_FORCE_NEW=1`,
  restart/recreate only C5, and keep `ttyd-codex5-backend.service` on the
  C5-local renderer that works on the phone. After the fix, verify
  `19004/status` and public `19904/status` show `pane[1]=node`, `error=""`,
  and a phone screenshot shows the Codex terminal text behind the C5 dock.
  Do not rotate `C5 OAuth`, rebind Sub2API, or touch other accounts for this
  front-end/entry condition.
- C5 OAuth browser isolation: use the user-managed Chromium profile on CDP
  port `9226` for C5 OAuth/device-code recovery. It keeps C5's authorization
  cookies separate from the daily browser session; real mouse events must
  target a button after `scrollIntoView({block:'center'})`, otherwise an
  off-screen button can appear to do nothing. Do not store credentials or
  device codes in this runbook.
- C5 phone-code order: before spending a `sms.sightx.top` CDK to request a
  number, verify the existing OpenAI browser tab has a live phone-add session.
  An `invalid_state` page cannot send SMS. If no code arrives after two minutes,
  cancel the activation, wait for `cdkStatus=retry_available`, then restore the
  OpenAI login session before requesting the one permitted replacement number.
- Use `codex-c5-phone-login` to restore that session: it opens ChatGPT login in
  the Fedora Chromium control tab and pushes the Mobile AI Workbench browser
  panel directly to the phone. It uses `phone-run` and then the maintained LAN
  ADB link as a direct-open fallback. Do this before any replacement-number
  request; it contains no CDK or OAuth material.
- C7/C8 phone-code order: the 2026-07-17 C7 rotation and C8 binding completed.
  A chongpt.xyz ChatGPT/Codex SMS CDK is stored in
  `~/.local/state/codex-sms/c7-chongpt-20260716.json` (`0600`, preview
  `SMS8...9MWLN`, status `used`; full CDK stays only in that state file). Do
  not redeem or request a number until the browser is on a live OpenAI
  `/add-phone` page, because the seller describes the number as time-limited
  and binding-limited. Successful sequence:
  1. Start a fresh slot device login: `CODEX_HOME=~/.codex-N codex login
     --device-auth`; for C8 the active WebTTY pane can show the device code.
  2. Complete email/password/TOTP until OpenAI shows `/add-phone`. If Fedora
     headless/Playwright auth hits Cloudflare/MFA 403, use the real Android
     Chrome path over ADB instead; it worked for C8.
  3. Open or API-query `https://chongpt.xyz/`, use the stored CDK only after
     `/add-phone` is visible, and copy the issued number into OpenAI. If the
     CDK already has a received code from an earlier binding, request a fresh
     SMS session after OpenAI sends the new SMS so the newest code is returned.
  4. Wait for the SMS code; if no SMS arrives after about two minutes, use the
     platform cancel/retry path before requesting a replacement number.
  5. If Codex consent says device code authorization is disabled, log into
     ChatGPT, open `#settings/Security`, enable `为 Codex 启用设备代码授权`,
     then rerun the device-login flow. The old device code may not complete.
  6. After Codex writes native `~/.codex-N/auth.json`, run
     `~/.local/bin/codex-sub2api-json-bind --account N --file
     /var/home/charlie/.codex-N/auth.json --label '<label>' --restart
     --health-check --json`. If `/v1/models` returns 200 but
     `/v1/responses` times out, set upstream `accounts.proxy_id=1`, restart
     system `sub2api.service`, then rerun
     `codex-account-provision --account N --primary-account-id <id> --restart
     --health-check --json`.
  7. Verify `/quota.json`, `/status`, Workbench `/api/status`, a real
     `/v1/responses` call, and the public WebTTY port (`:19906` for C7,
     `:19907` for C8).
  Seller note: number validity was advertised as 25-29 days, theoretically one
  registration or three bindings, not guaranteed; reported successful tests
  used three different IP regions with about five minutes between bindings.
- C7 page-stuck repair (2026-07-17): if `19006/status` and `19906/status` are
  healthy, the page has `codex_mobile_ime_stability`,
  `codex_mobile_viewport_lock`, and no `codex_ttyd_reconnect_autofix`, but the
  visible pane is stuck on `Conversation interrupted` or a stale prompt, treat
  it as a local TUI/session state issue. Snapshot first, detach stale WebTTY
  clients, then use the account-local restart path:
  `curl -X POST -H 'X-Device-Code: w19900422'
  http://127.0.0.1:19006/restart?reason=c7-page-stuck`. Verify the pane PID
  changed, the capture shows a fresh Codex prompt, both `19006/status` and
  `19906/status` return `ok=true`, then restore the tmux window to `100x30`.
  Do not rotate the upstream account, restart Sub2API, or edit auth files for
  this condition.
- C7 unable-to-input repair (2026-07-17): if C7 `19006/status` /
  `19906/status` are healthy and the page includes `codex-input-panel` with no
  `codex-ios-safe-input`, but typing or the mobile `输入` panel appears to do
  nothing, check whether the pane is stuck in tmux copy-mode:
  `tmux -S /run/user/1000/tmux/codex7.sock list-panes -t haven-codex7 -F
  'pane_in_mode=#{pane_in_mode} mode=#{pane_mode}'`. If `pane_in_mode=1`, exit
  copy-mode with `tmux -S /run/user/1000/tmux/codex7.sock send-keys -t
  haven-codex7 -X cancel`, then restore `window-size manual` and resize to
  `100x30`. `~/.local/bin/ttyd-device-gate-proxy` now also cancels copy-mode
  before `/tmux-send` paste/Enter and supports `account=7/8` targeting, so a
  C1/top-level input panel can clear and send to C7. Restart only gate services
  after this script change; do not restart C7 backend, tmux, Sub2API, or rotate
  the upstream account for this UI/session-state failure.
  If `pane_in_mode=0` and both status endpoints remain healthy but the real
  phone screenshot still shows ttyd's `Press Enter to Reconnect` overlay or a
  bottom `连接待恢复` notice, treat it as a stale Chrome/WebSocket tab. First
  restart only `ttyd-codex7.service`, then force the phone to open a fresh C7
  URL with a cache-busting query:
  `adb -s <serial> shell "am start -a android.intent.action.VIEW -d
  'http://charlie1990.duckdns.org:19906/?device=<device-code>&r=$(date +%s)'
  com.android.chrome"`. Verify with an ADB screenshot that the overlay is gone
  and with `19006/status` still `ok=true`. Do not restart
  `ttyd-codex7-backend.service` or kill the `haven-codex7` tmux pane for this
  browser-tab condition.
  2026-07-17 follow-up: Workbench/hidden iframe clients can create very narrow
  tmux clients such as `2x47` or `2x1`, making C7/C8 look stuck or unable to
  input. C7 inherits C5 scripts, so the durable fix was added to
  `~/.local/bin/ttyd-codex5-entry` and
  `~/.local/bin/haven-codex5-ensure`; C8 has the same fix directly in
  `~/.local/bin/ttyd-codex8-entry` and
  `~/.local/bin/haven-codex8-ensure`. Each now applies
  `tmux set-window-option window-size manual` and `resize-window -x 100 -y 30`
  during create/ensure/attach. Validate with `bash -n` on those four scripts
  and `19006/status` / `19007/status` showing pane `100x30`.
- 2026-07-17 C8 unbound 503 repair: if C8 shows `503 Service Unavailable` while `19007/status` is healthy, first check whether `openai-codex-8` has any `account_groups` rows. A newly created slot with only `codex8-sub2api` and no upstream binding will pass `/v1/models` but fail `/v1/responses`. Do not restart global Sub2API or borrow C7 as a fallback for an independent account. Keep C8 in login-mode until a real C8 OAuth source is imported; then run `codex-sub2api-json-bind --account 8 --file ~/.codex-8/auth.json --label 'C8 day Plus' --restart --health-check --json`, verify `/v1/responses` returns 200, and ensure `/quota.json` no longer has `sub2api.unbound=true`.
- 2026-07-17 WebTTY button/account-label repair: C6/C7 must not reuse
  `index-codex5.html`. Each backend needs its own index file:
  `index-codex6.html` / `index-codex7.html`, with matching title, badge, and
  `const account="<slot>"`. Also keep C4/C5 index `const account` aligned with
  their slots. `ttyd-codex6.service` must include C7 in
  `CODEX_ACCOUNT_EXTERNAL_PORTS` and `CODEX_ACCOUNT_LOCAL_PORTS`, otherwise C6
  cannot expose the C7 account button. `mobile-ai-workbench` short-link auth
  allowlists and Super actions must include `c6` and `c7`, not only `c1-c5`.
  Verification:
  `curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19005/status` and
  `19006/status` return `ok=true`; C4-C7 frame HTML contains the matching
  `Codex N WebTTY`, `Codex N | ~/.codex-N`, `const account="N"`,
  `codex-input-panel`, and `codex_mobile_ime_stability`; Workbench
  `/ports`, `/super`, `/go/c6`, and `/go/c7` resolve with the device cookie.
- 2026-07-17 complex info button restore: individual Codex WebTTY pages and
  `?view=frame` use the right-side `codex-stable-dock` info rail by default,
  created by `codex_simple_account_surface` in
  `~/.local/bin/ttyd-device-gate-proxy`. This is the user-preferred "凌晨复杂按钮"
  surface, not the plain simple TTY rail. It has a sticky `收/展 C<N>` collapse
  button, account cards `1-7`, and each card shows `C<N> · name`, account type,
  fixed node, task state, and quota/limit data from `/quota.json`. Keep `输入`,
  `输入↵`, `打断`, `任务`, `多窗`, and `更多` inside this rail; `更多` exposes
  quota, scroll, local sessions, terminal progress `/history`, copyable
  per-account input history `/input-history`, and the external tool jumps
  `Workbench`, `OP`, `Crush`, `Aider`, and `Goose`. `Aider` must use
  same-origin `/tool/aider/`; visible `Goose` must use same-origin
  `/tool/guise/`; `OP` and `Crush` use public DuckDNS ports `18910` and
  `17766`; `Workbench` uses port `19888`. Do not replace this with the plain
  six-button TTY rail unless the user explicitly asks for that simpler mode.
- 2026-07-17 C7 mobile jump/flicker repair: if C7 is healthy but the phone
  view visibly scrolls, refreshes, or jumps, first inspect the C7 frame source
  before touching account credentials:
  `curl -H 'X-Device-Code: w19900422'
  'http://127.0.0.1:19006/?device=w19900422&view=frame'`. C7 should use the
  same account surface as the other Codex pages so the account buttons stay the
  same full-card shape. C7 must skip the visual `codex_account_smart_sort`
  compression because its 2-column/narrow-card layout makes account text
  unreadable on phone. Inject `codex_c7_stable_behavior` before the account
  surface scripts so C7 suppresses decorative 2/3/5/15-second timers and broad
  decoration observers at runtime.
  `codex_mobile_viewport_lock` must not execute C7 `visualViewport` behavior
  that repeatedly recalculates height or calls `scrollTo(0,0)`.
  Restart only `ttyd-codex7.service`, then verify the frame source has
  `codex_c7_stable_behavior`, `codex_simple_account_surface`,
  `codex_external_tools`, `cet-workbench`, and `cet-goose`, while
  `codex_account_smart_sort`, `codex_ttyd_reconnect_autofix`, and
  `visualViewport.addEventListener('scroll'` are absent. Do not rotate C7,
  restart Sub2API, or restart the backend for this front-end jump symptom.
- 2026-07-17 account button smart sort: `ttyd-device-gate-proxy` injects
  `codex_account_smart_sort` on top-level, `?view=frame`, and iOS fallback
  Codex pages. It sorts account cards by quota usability and groups them as
  `有额度`, `额度少`, `限额/不可用`, then `未知`. Accounts with active
  `upstream_rate_limit` or `availability` state `monitoring`/`stopped` are
  pushed down by group/color, but account cards must remain visually the same
  size across every page: 74px normally and 70px on narrow mobile screens. Low
  official quota stays above blocked accounts; Sub2API/API accounts with no
  official percentage are treated as available only when `sub2api.ok` is not
  false and `upstream_rate_limit.active` is false. Do not require
  `sub2api.account` to be present: C6/C7-style Sub2API slots may report
  `sub2api.ok=true` with `sub2api.account=null`, and those are still `有额度`
  unless `sub2api.ok:false`, an active upstream rate limit, or disabled
  availability says otherwise. If `ok:false`,
  `sub2api.ok:false`, or an active upstream rate limit appears, classify the
  account as `限额/不可用`; C3 with `rate_limit_reset_at=2026-07-20T03:44:54Z`
  is one such blocked case even though its API key balance remains positive.
  Do not treat `null` quota fields as `0%` because JavaScript `Number(null)`
  returns `0`. Workbench homepage account tabs and Workbench `/buttons` use the
  same sorting policy. Homepage tabs should render each availability group as a
  separate horizontally scrollable `tab-section`; do not place group labels and
  buttons as flat siblings in one flex row on mobile, because they visually pile
  together. `/buttons` should keep account cards a fixed visual height instead
  of shrinking low/blocked cards. On phone, homepage account buttons must keep
  names readable: use wide tabs around `128px`, allow `C<N> · name` to wrap to
  two lines, and keep horizontal scrolling for the account strip. Workbench
  `/buttons` should use a single-column account card grid on narrow screens,
  with account-card text allowed to wrap; do not return to 82px single-line
  tabs or two-column narrow cards because long account names are truncated.
  After changing this UI layer, restart only
  `ttyd-codex{,2,3,4,5,6,7}.service` and `mobile-ai-workbench.service`, not
  backend ttyd or tmux. Verification:
  `curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19000/?view=frame | rg 'codex_account_smart_sort'`
  and headless `/buttons` DOM should show available accounts before low quota
  and limited/unavailable accounts.
- 2026-07-17 C2 rate-limit 503 classification: C2 `19001/status` can be healthy and `codex2-sub2api` can be active/bound while `/v1/responses` returns `503 Service temporarily unavailable`. This is not the C8 unbound case if `bound_account_count=1`; check `/quota.json` `upstream_rate_limit.active`. For upstream account `15`, reset is `2026-07-23T04:54:51Z`. `ttyd-device-gate-proxy` now forces top-level quota `ok=false` and Workbench `quota_ok=false` when `upstream_rate_limit.active=true`, while keeping `sub2api.ok=true` to mean the DB/key binding itself is healthy.
- 2026-07-17 official usage/quota visibility: `/quota.json` exposes
  `official_possible`, `official_source`, and `usage_source`. C1 is native
  ChatGPT/Codex auth, so official Codex `rate_limits` and token totals can come
  from Codex `token_count` / `rate_limits` events in session JSONL. C2-C7 run
  slot-local Codex in `auth_mode=apikey` through Sub2API, so official Codex
  5h/7d data is not available from the slot-local CLI; show Sub2API
  `usage_logs` token totals and upstream rate-limit/reset state instead. Do
  not label Sub2API usage as official ChatGPT/Codex quota. If a future slot is
  converted back to native ChatGPT/Codex auth, a fresh Codex turn is required
  to emit a usable `token_count` event before official data appears.
- 2026-07-17 dynamic account sort follow-up: WebTTY account buttons derive the
  rendered account ids from `CODEX_ACCOUNT_LOCAL_PORTS` /
  `CODEX_ACCOUNT_EXTERNAL_PORTS` in `ttyd-device-gate-proxy`, and local Foot
  tab sorting discovers accounts from `ttyd-codex*-entry` plus
  `haven-codex*.service`. When adding C8+, update the service/env port arrays
  first; the visible button list, `/quota.json` snapshots, `/sessions` actions,
  and smart sort should then include the new slot without hard-coded
  `1-7` edits. If a quota row is temporarily absent, Foot sorter places that
  account in `未知` instead of producing an empty sort item.
- 2026-07-19 phone WebTTY reconnect route repair: if Haven/SSH is stable but
  browser WebTTY shows reconnect/blank/unstable, do not trust DuckDNS or
  Fedora-local checks alone. Run `~/.local/bin/phone-webtty-route-probe auto`; it must auto-pick a reachable ADB serial such as `100.87.37.3:5555` before testing phone-side LAN/NetBird/DuckDNS status, frame
  page, and WebSocket `101` for C1-C8 and writes
  `~/.local/state/phone-webtty-route-probe/latest.json`. Workbench smart
  `/go/cN` and homepage iframes now prefer this phone-measured route when the
  Workbench itself was opened through DuckDNS. This avoids unstable DuckDNS
  hairpin while keeping DuckDNS as fallback.
- 2026-07-19 C7 not-visible Workbench repair: if C7 is healthy in
  `19006/status`, `19906/status`, Workbench `/api/status`, and
  `/api/route-best`, but the phone homepage does not show C7, inspect the
  Workbench homepage JavaScript/layout before changing accounts. A generated
  JS line in `~/.local/bin/mobile-ai-workbench` had an unescaped newline in
  `b.title`, which broke `renderTabs()` and hid the account strip. After
  fixing the JS, the mobile layout was changed from a hidden horizontal strip
  to a fixed `4 x 2` account grid so C1-C8 are all visible on a 390px-wide
  phone screen. `hostForAccount()` now uses `phoneRouteBest["c"+id]` for every
  account first, regardless of whether Workbench was opened via DuckDNS,
  NetBird, LAN, or USB; only then does it fall back to the current host plus
  the external public port. Verify with a 390x844 Chromium screenshot of
  `http://127.0.0.1:19888/?device=w19900422` and phone-side
  `curl -L http://charlie1990.duckdns.org:19888/go/c7?device=w19900422`,
  expecting C7 visible in the second row and HTTP 200 from the selected
  `19906` route.
- 2026-07-19 C2/C3/C4 narrow-pane repair: phone probes/browser clients can
  leave tmux panes at `2x1`, making WebTTY look like reconnect/blank while
  Haven remains stable. Detach only narrow clients, cancel copy-mode, set
  `window-size manual`, resize to `100x30`, and do not rotate accounts.
  `ttyd-codex{2,3,4}-entry` and `haven-codex{2,3,4}-ensure` now normalize
  existing and newly created sessions to `100x30`. Verify with
  `tmux -S /run/user/1000/tmux/codexN.sock list-panes -t haven-codexN -F
  '#{pane_width}x#{pane_height} mode=#{pane_in_mode}'`.
- 2026-07-20 C2/C4/C5/C6/C7/C8 503 emergency repair: if `/v1/models` is 200
  but `/v1/responses` is 503 because the slot's current upstream is
  rate-limited or workspace-deactivated, first test whether an unbound/reset
  upstream can return a real `/v1/responses`. In this incident upstream
  account `10` passed health and was used as a temporary shared fallback/source:
  C2 `15 + fallback 10`, C3 `13 + fallback 10`, C4 `10`,
  C5 `18 + fallback 10`, C6 `10`, C7 `20 + fallback 10`,
  C8 `21 + fallback 10`. This restores work quickly but
  shares one Plus quota, so import fresh independent OAuth sources when
  sustained parallel work is needed. After rebinding, clear
  `/run/user/1000/codex-webtty-sub2api-quota.json.*`, restart only the eight
  WebTTY gate services plus `mobile-ai-workbench.service`, and verify every
  slot's `/v1/responses` returns HTTP 200. `ttyd-device-gate-proxy`
  `sub2apiQuotaFor()` must select a currently usable bound upstream
  (`active`, schedulable, no future `rate_limit_reset_at` /
  `temp_unschedulable_until`) before falling back to priority order; otherwise
  UI cards can stay red while Sub2API correctly schedules the fallback.
  Initially C1 (`~/.codex`) was native ChatGPT-token mode, so "fallback to
  account 1" meant the working shared upstream account `10`. Later on
  2026-07-20 C1 was intentionally converted to Sub2API API-key mode with
  group `openai-codex-1`, key `codex1-sub2api`, and primary upstream
  account `10`. After this conversion, `ttyd-device-gate-proxy` must treat C1
  as Sub2API whenever `~/.codex/auth.json` has `auth_mode=apikey`; otherwise
  `/quota.json` and Workbench `:19888` can keep showing stale official
  ChatGPT/Codex 5h/7d limits even though the terminal data plane is already
  using Sub2API. When repairing C3 with `codex-account-provision`, do not let
  `--template-group-id` default to `3`; either pass another template group such
  as `11` or use the fixed provisioner that skips template unbind when the
  template group is the target group. Otherwise the script can delete C3's
  newly-created binding after health repair.
- 2026-07-21 account independence policy: every `openai-codex-N` group keeps
  only its independently purchased primary upstream. The sole in-group exception
  is C6 `19 -> 15`, an explicitly documented task-continuation path; it must
  never be displayed as C6 identity. Do not automatically inject a rescue
  upstream, build a C1 pool, or re-enable `codex-fallback-pool-repair.timer`.
  The helper is now a manual cleanup/audit tool only. Before any new account
  bind, verify the final group has exactly one primary row (or the C6 exception)
  and confirm with `codex-account-registry`.
- 2026-07-20 third-party desktop binding: the Kasm-installed
  `thirdparty-codex-desktop-linux` default instance is the total-pool client,
  not an independent C5 client. `custom_startup.sh` launches
  `bin/ilysenko-codex-desktop 1`, which uses C1 / `openai-codex-1`; its
  priority-100 primary and priority-10 usable account routes provide automatic
  Sub2API fallback. The explicit desktop entry is
  `Thirdparty-Codex-Desktop-Pool.desktop`. After changing any local account
  config or pool membership, run `~/.local/bin/kasm-codex-home-sync` and
  restart only `kasm-cursor-webtop`; do not edit the container copy by hand.
- 2026-07-20 pending C10 iCloud Plus credential: a user-supplied credential was
  stored only in `~/.local/state/codex-account-import/c10-icloud-plus-20260720.secret`
  with mode `0600`; do not copy it into runbooks, shell commands, logs, or final
  replies. The seller says Codex requires separate SMS/phone receiving, so this
  account cannot become a Sub2API upstream until `CODEX_HOME=~/.codex-10 codex
  login --device-auth` completes and `~/.codex-10/auth.json` is created. After
  phone binding/device authorization, import with
  `codex-sub2api-json-bind --account 10 --file ~/.codex-10/auth.json --label
  '<non-secret label>' --restart --health-check --json`, then run the
  fallback-pool repair.
- 2026-07-18 auto-sort misjudgement repair: do not let transient Sub2API
  `sudo podman exec`/Postgres timeouts flip available accounts to
  `限额/不可用`. `ttyd-device-gate-proxy` now returns the last successful
  per-slot Sub2API quota cache for a bounded stale window when the live query
  times out, and WebTTY smart sort uses an explicit group rank
  `有额度` → `额度少` → `限额/不可用` → `未知` instead of relying only on
  numeric score. `mobile-ai-workbench` `/api/status` reads the canonical C1
  `/quota.json` snapshot once per refresh and treats missing quota rows as
  `未知`, not unavailable. After this UI-layer change, restart only
  `ttyd-codex{,2,3,4,5,6,7,8}.service` and `mobile-ai-workbench.service`.
  Verification: concurrent curls to `19000-19007/quota.json` should show zero
  `ETIMEDOUT` rows; C5/C7/C8 real `/v1/responses` should return 200, while
  C4/C6 remain correctly `限额/不可用` with top-level `ok=false` if their
  Sub2API upstream account status is `error`/unschedulable and real
  `/v1/responses` returns 503. Keep `sub2api.ok=true` in that case to mean
  the DB/key binding itself is readable; the top-level `ok` is route
  availability.
  For workspace deactivation such as current C4 upstream `16` and C6 upstream
  `19`, include non-secret `accounts.error_message`, set
  `upstream_availability.deactivated=true`, and show
  `不会自动恢复；工作区已停用，需导入/绑定新的有效上游账号。` in
  WebTTY `/quota.json`, Workbench `/api/status`, homepage tabs, and
  `/buttons` cards. Do not invent a reset time when Sub2API has none.
- Account provisioning is script-owned. Use `~/.local/bin/codex-account-provision` or the WebTTY `生成4` button; do not repeat the old manual sequence of editing Sub2API groups, API keys, Codex auth/config/env files, and restarting ttyd by hand. With `--restart`, the script also detects stale tmux pane process API keys and recreates the session before service restart.
- 2026-07-14 claim-code rotation rule: for slot `1/2/3`, if the user provides a delivered claim code and wants to replace the current independent upstream account, prefer `~/.local/bin/codex-sub2api-claim-bind <slot> <code>`. It will redeem or lookup the code, download `download.json`, import through local Sub2API `POST /api/v1/admin/accounts/batch`, rebind `openai-codex-N` and `codexN-sub2api`, update the slot-local env/auth, and restart the slot. If the code page says “额度已用完” but `lookup` still returns `download.json`, treat that as a valid historical rotation path instead of a failure.
- 2026-07-14 raw JSON rotation rule: if the user provides an exported phone/local raw Codex JSON/TXT file instead of a claim code, prefer `~/.local/bin/codex-sub2api-json-bind --account <slot> --file <path> --label '<name>' --restart --health-check --json`. This extracts and validates the raw OAuth JSON, imports/updates a Sub2API upstream account, then delegates slot binding to `codex-account-provision`. Do not paste tokens into converter sites or print them. If health times out while `/v1/models` works, check and set the upstream `proxy_id=1`, restart `sub2api.service`, then rerun the provision health check.
- 2026-07-14 page-level acceptance rule: after any Codex account import/rebind, verify both backend and visible WebTTY UI. For slot 4, run a headless Chromium mobile screenshot against `http://127.0.0.1:19003/?device=w19900422`, dump DOM and assert markers such as `Codex 4 WebTTY`, `codex_account_ui_final`, `OP`, `Crush`, `codex-quota`, `codex-session`, and `codex-send`. Then check `/quota.json` shows the intended upstream account name/id and active `codex4-sub2api` key, and `/status` returns `ok=true`. Headless Chromium may leave a narrow tmux client; detach it and restore `haven-codex4` to `100x30` before finishing.
- Authentication, installation id, history, SQLite state, logs, cache, and shell snapshots must remain account-local.
- Shared config, skills, AGENTS.md, `~/.ai-context`, `~/memory`, and MCP definitions may be shared through the existing sync path.
- 2026-07-17 C8 shared-knowledge repair: C8 originally had an account-local
  empty `~/.codex-8/skills` directory containing only the system marker, while
  `~/.local/bin/codex-shared-sync` defaulted to C2/C3 only. This meant C8 could
  miss local operational skills and appear not to know prior local actions such
  as NetBird installation. Durable fix: `~/.codex-{4,5,6,7,8}/skills` are
  symlinks to `~/.codex/skills`, and `codex-shared-sync` default
  `CODEX_SECONDARY_HOMES`, `slot_for_home`, and Sub2API slot detection now
  include C2-C8. Validate with:
  `find -L ~/.codex-8/skills -maxdepth 2 -name SKILL.md` and
  `~/.local/bin/codex-shared-sync --check`.
- Account 2 has already added the token-safety baseline:
  - `~/.config/codex-shell-env/env.sh`
  - `~/.local/bin/codex-token-safe-run`
  - `~/.local/bin/codex-resume-or-new`
  - Haven/WebTTY Codex entries exporting `BASH_ENV`, `ENV`, and `ZDOTDIR`
  - default model lowered to `gpt-5.5` with `model_reasoning_effort="low"`
- 2026-07-14 WebTTY model-switch rule: `~/.local/bin/ttyd-device-gate-proxy`
  now exposes `POST /interrupt` and uses it before slot-local model restart.
  For quick model buttons, always interrupt the current tmux/Codex stream
  first, then rewrite `config.toml`, restart the slot, wait for `/status`,
  and only then reload the visible account surface. Do not hot-restart a live
  streaming Codex pane without the pre-interrupt step; it commonly surfaces in
  UI as `Conversation interrupted`.
- 2026-07-14 follow-up: the right-dock quick model buttons are now disabled in
  the visible WebTTY UI because users repeatedly triggered
  `Conversation interrupted` while switching models mid-session. Current policy:
  change slot-local default model through backend/admin paths only, and let the
  new model apply on the next fresh session unless an explicit forced restart is
  requested during maintenance.
- 2026-07-14 top-bar merge: network/connectivity status is no longer a separate
  floating widget. `ttyd-device-gate-proxy` now writes connection score and
  daily/weekly failure summary into the same top quota strip as `5h/7d`,
  `已用 N 天`, current quota, and model. The top strip also exposes a direct
  `输入` button for iOS fallback input, so do not reintroduce a standalone
  right-top connectivity box that overlaps page text.
- 2026-07-14 iOS WebKit input follow-up: for Codex WebTTY pages, keep the
  native auto-context wrapper disabled on iOS/WebKit, but still re-apply
  `.xterm-helper-textarea` attributes (`autocomplete=off`, `autocorrect=off`,
  `autocapitalize=none`, `spellcheck=false`) and allow a single guarded
  terminal-tap focus to the helper textarea. Avoid older multi-event forced
  focus loops on `pointerdown/click/touchend`, which caused repeated input and
  composition instability.
- 2026-07-15 iOS panel activation: `ttyd-device-gate-proxy` injects
  `codex_ios_panel_activation`. It directly activates controls in Codex docks
  and panels from a single `touchend`, then synchronously focuses the real
  `#codex-input-text` textarea while the Safari user gesture is still active.
  Do not restore readonly/inputmode restrictions or delayed-only focus for
  this fallback input.
- 2026-07-15 external-tool isolation: the Codex UI injection applies only to
  Codex account pages. Never inject `codex_*` docks, touch handlers, or input
  panels into `/tool/aider/` or `/tool/guise/`; those are independent native
  ttyd/xterm surfaces. Injection there causes taps to reach the terminal and
  can display xterm capability responses such as `0;276;0c`.
- 2026-07-15 iOS home fallback: the Codex account homepage must not load the
  desktop's stacked multi-account/iframe/dock scripts on iPhone or iPad.
  `ttyd-device-gate-proxy` selects `codex_ios_home_fallback`, which leaves the
  native ttyd terminal active and supplies a right-side collapsed rail. Its
  default controls are `输入` and `更多`; expanding it reveals
  `历史`/`Aider`/`Goose`/`刷新`, so there is only one mobile control surface.
  This is the stable iOS surface; do not add Router, quota polling, account
  frames, or global touch handlers to it.
- 2026-07-14 force-refresh rule: WebTTY UI version changes must auto-reload the
  current visible page by default. Do not leave old pages on a passive
  “界面有新版本，不会自动刷新” prompt. Only delay reload while an
  input/textarea/select is actively focused; once focus clears, refresh the
  visible page. Likewise, WebSocket reconnect logic should auto-reload after
  `/status` recovers instead of waiting for the user to press a manual button.
- 2026-07-14 ttyd reconnect prompt rule: Codex WebTTY pages must inject
  `codex_ttyd_reconnect_autofix` from `~/.local/bin/ttyd-device-gate-proxy`.
  This watches iframe terminal text for ttyd's `Press Enter ... reconnect`
  prompt and WebSocket close/error, polls same-account `/status`, then reloads
  the visible frame automatically. When users report “按 enter reconnect”, first
  verify `curl -H 'X-Device-Code: w19900422'
  http://127.0.0.1:1900N/?view=frame | rg
  'codex_ttyd_reconnect_autofix|codex_no_leave_confirm_reconnect'`, then
  restart only `ttyd-codex{,2,3,4}.service` if the marker is missing. Do not
  restart backend ttyd or kill tmux/Codex just to clear this prompt.
- 2026-07-14 hang interrupt rule: if a Codex account page shows
  `Working (Nm Ns)` for several minutes with no pane text change and near-zero
  Codex CPU, treat it as a stuck request before blaming the WebTTY page.
  `ttyd-device-gate-proxy` injects `codex_interrupt_watch` plus `打断` buttons
  into the existing right dock/rescue bar. Pressing it calls `POST /interrupt`
  for the current account and sends Escape, Ctrl-C, Escape to that tmux pane.
  It does not kill the tmux session or clear history. After a successful
  interrupt, the page reloads so stale WebSocket state is cleared.
- 2026-07-15 Mobile AI Workbench home taskbar rule:
  `mobile-ai-workbench.service` on `:19888` uses `/` as the primary phone task
  management entry. Keep the account tabs and Codex WebTTY iframes visible, but
  also keep the top home taskbar visible with `任务中心`, `多 CLI 窗口`,
  `新建当前账号`, `刷新状态`, and the compact task-state summary. The homepage
  may fetch `/api/status` asynchronously after terminal frames are rendered, but
  status failures must not block opening or switching terminals. Do not hide
  multi-window management only inside `/buttons` or a secondary drawer.
- 2026-07-14 Mobile AI Workbench tool dock rule: the `工具` control must be an
  independent floating dock, not part of the account tab bar. When collapsed it
  shows `展 C<N> · <任务状态>` for the current account; when expanded, `/buttons`
  shows every Codex account grouped by account type/name (`个人`, `团队`, `API`)
  with visible task-state labels such as `运行中`, `有结果`, `未知`, or `异常`.
  The task state is sourced from existing WebTTY `/sessions.json` data through
  Workbench `/api/status`; it remains lazy-loaded through `/buttons`, not a
  clean-page dependency.
- 2026-07-14 Mobile AI Workbench task-center rule: the `任务` button opens the
  Workbench-owned `/tasks`集散中心, not an iframe of one selected account's
  `/sessions`. `/tasks` consumes `/api/tasks`, groups all accounts by task
  state (`全部`, `运行中`, `有结果`, `异常`, `待查看`), shows per-account cards,
  a selected-account progress panel, recent screen lines, recent archives, and
  management actions (`快照`, `归档当前`, `恢复`, `归档重启`). Actions go through
  `POST /api/tasks/action`, which proxies the existing WebTTY session action
  path. Keep `/tasks` as the main task management surface; individual account
  `/sessions`, `/history`, `/timeline`, and `/archives` are detail pages.
- 2026-07-17 C1 black-screen repair: if Workbench/C1 shows a black terminal
  while the old tmux pane still has content, check for a preserved session such
  as `haven-codex-stuck-*`. Plain tmux targets like `haven-codex` prefix-match
  `haven-codex-stuck-*`, so `haven-codex-ensure` can falsely report healthy and
  `ttyd-codex-entry` can attach the stuck session. For C1, both
  `~/.local/bin/haven-codex-ensure` and `~/.local/bin/ttyd-codex-entry` must use
  exact tmux target `=haven-codex:` for `has-session`, `list-panes`, options,
  kill, and attach. Then run `systemctl --user start haven-codex.service` and
  restart only `ttyd-codex-backend.service ttyd-codex.service`. Do not delete
  the preserved `haven-codex-stuck-*` session unless the user asks.
- 2026-07-17 C2 black-screen repair: C2 can fail the same way as C1, so
  `~/.local/bin/haven-codex2-ensure` and `~/.local/bin/ttyd-codex2-entry` must
  use exact tmux target `=haven-codex2:` for `has-session`, `list-panes`,
  options, kill, and attach. If `/status` is healthy and xterm connects but the
  visible tmux capture is all blank, treat it as a corrupt Codex TUI screen
  rather than account/API failure: first snapshot/archive, then call the
  account-local restart endpoint, e.g. `curl -X POST -H 'X-Device-Code:
  w19900422' http://127.0.0.1:19001/restart?reason=c2-black-screen`. Verify
  `http://127.0.0.1:19001/status` and `http://127.0.0.1:19900/status`, confirm
  the page contains `codex_mobile_ime_stability`, `codexSafeReload`,
  `MIN_RELOAD_MS=10000`, `OK_REQUIRED=3`, and does not contain
  `codex_ttyd_reconnect_autofix`. Do not rotate the upstream account or restart
  Sub2API for this local screen-state condition.
- 2026-07-17 C2 visible `502 Bad Gateway` in the Codex pane can be an upstream
  `/v1/responses` failure while the WebTTY page itself is healthy. First check
  local and public-local page health:
  `curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19001/status` and
  `http://127.0.0.1:19900/status`. If both return `ok=true`, verify the C2
  Sub2API data plane with the slot-local key: `/v1/models` and a tiny
  `/v1/responses` request against `http://127.0.0.1:19090`. On 2026-07-17 C2
  key `codex2-sub2api` was active, upstream account `15`
  (`Franciscastillo47795`) was active/schedulable with `proxy_id=2`, no rate
  limit, and a follow-up `/v1/responses` returned HTTP 200. In this condition,
  do not rotate C2 or restart tmux/Sub2API just because an old 502 remains on
  screen; treat it as stale pane text unless a fresh minimal response check
  still fails.
- `codex-webtty-guard.timer` runs `~/.local/bin/codex-webtty-guard` every two
  minutes as the server-side account-page monitor. It now checks C1-C7 gate,
  backend, public-local status, exact tmux session, and pane text for
  disconnect/5xx markers. It performs only light repairs: start inactive
  gate/backend units, start the matching `haven-codexN.service` when the exact
  tmux session is missing or `/status` is unhealthy, and restart only the
  affected gate/backend on HTTP `000`/5xx. It writes the latest non-secret
  status to `/run/user/1000/codex-webtty-guard/latest.json` and events to
  `/run/user/1000/codex-webtty-guard/events.log`. It must not rotate accounts,
  clear Sub2API scheduler state, kill Codex tmux sessions, or restart global
  `sub2api.service` for stale pane text alone.
- If browser-side connection scoring disappears, check
  `~/.local/bin/ttyd-device-gate-proxy` for duplicate function definitions.
  On 2026-07-17 a later empty `connectivityScoreScript() { return "" }`
  overrode the real `codex_connectivity_score` injector. Remove the empty
  override, run `node --check`, restart only the seven gate services
  `ttyd-codex{,2,3,4,5,6,7}.service`, and verify every top-level account page
  contains `codex_connectivity_score`. Do not restart backend ttyd or tmux for
  this UI-only repair.
- 2026-07-15 Multi-window rule: Mobile AI Workbench owns `/windows` as the
  account/window manager. It lets each Codex account create multiple independent
  CLI windows. Each window is a separate tmux session on that account's existing
  socket plus a local-only dynamic ttyd port in the `20040-20140` range. Public
  access stays behind Workbench `:19888` through `/window/<id>/`; do not add
  router forwards for individual windows. State lives in
  `~/.local/state/codex-windows/windows.json`. API:
  `GET /api/windows`, `POST /api/windows/action` with `create|start|kill`.
  Short link: `/go/wins`. The homepage taskbar must also link to `/windows`
  and provide `新建当前账号` so task/window management starts from `/`. The
  individual Codex TTY pages must also expose a visible `多窗` button in the
  right-side simplified dock, injected by `~/.local/bin/ttyd-device-gate-proxy`
  as `#codex-windows-center`, so users can reach multi-window management from
  `19899/19900/19902/19903/19904` without first opening Workbench.
- 2026-07-15 Multi-window repair notes: `~/.local/bin/mobile-ai-workbench`
  must not trust only the saved PID in `windows.json`. A stale ttyd may still
  be listening on the dynamic port, or a shell/curl command may contain
  `/window/<id>` and be falsely matched. Identify live window ttyd processes
  from `ps -eo pid=,comm=,args=` where `comm=="ttyd"` and args contain
  `-b /window/<id>`. `start` must recreate the tmux session when
  `tmux_alive=false`, then start/reuse ttyd; `kill` must remove both the tmux
  session and all matching ttyd processes. In Node, use `SIGTERM`/`SIGKILL`
  signal names, not `TERM`/`KILL`. Dynamic windows must not share the account's
  main `CODEX_HOME`, because the local `~/.local/bin/codex` wrapper checks
  `state_5.sqlite` and may kill the existing Codex PID using that account home.
  Each window should use a window-local home under
  `~/.local/state/codex-windows/homes/<window-id>` and copy only non-runtime
  account resources such as `auth.json`, `config.toml`, `installation_id`,
  `skills`, and `plugins`. Dynamic windows should force a new interactive Codex
  TUI with `CODEX_FORCE_NEW=1`; otherwise `codex-resume-or-new` can complete
  `codex resume --last --include-non-interactive` and exit immediately, leaving
  ttyd attached to a dead tmux session. Verify with: create a smoke window, wait
  at least 15 seconds, confirm `/api/windows` shows
  `alive=true, tmux_alive=true`, confirm the pane environment has
  `CODEX_HOME=~/.local/state/codex-windows/homes/<window-id>`, confirm
  `curl -I -H 'X-Device-Code: w19900422'
  http://127.0.0.1:19888/window/<id>/` returns ttyd `200 OK`, then `kill` and
  confirm both state count and matching ttyd process count are `0`.
- 2026-07-14 Codex account page simplification rule:
  `~/.local/bin/ttyd-device-gate-proxy` injects
  `codex_simple_account_surface` after the older WebTTY UI scripts. The
  persistent account page surface should stay small but readable: top
  quota/status strip, and a compact right dock with account `1/2/3/4/5`, `输入`,
  `打断`, `任务`, and `更多` visible by default. The `任务` button must open the
  Workbench `/tasks`集散中心, so the account page and Workbench do not expose
  two different task-management surfaces. Because account buttons include
  name/type/task state, do not shrink the dock below a phone-readable width.
  Router, quota, management, project, archive, scroll, and external tools remain
  available only after `更多` is opened. Do not add new always-visible floating
  buttons to individual account pages; add low-frequency tools to Workbench
  `:19888` or behind `更多`.
- 2026-07-15 C6 placement: show `C6 · GPT Team` as a peer card in the
  account-status/active-account group, alongside the other account cards.
  It opens C6 directly through `19005` locally or `19905` remotely; do not put
  it in the standalone `更多` menu.
- 2026-07-17 Codex WebTTY external-tool buttons: `Workbench`, `OP`, `Crush`,
  `Aider`, and `Goose` belong in the complex Codex WebTTY `更多` area injected
  by `~/.local/bin/ttyd-device-gate-proxy` (`codex_external_tools` augmenting
  `#csd-extra`). They must use the intended independent tools, not Crush
  redirects: `Workbench` -> `:19888/`, `OP` ->
  `http://charlie1990.duckdns.org:18910/`, `Crush` ->
  `http://charlie1990.duckdns.org:17766/`, same-origin `/tool/aider/` proxies
  to `aider-ttyd.service` on `127.0.0.1:7693`, and visible `Goose` uses
  same-origin `/tool/guise/` proxied to `guise-ttyd.service` on
  `127.0.0.1:7694`. The internal `guise` path is a compatibility alias; all
  user-visible labels use `Goose`. After edits, restart all seven
  `ttyd-codex{,2,3,4,5,6,7}.service` gates and verify local gates
  `19000-19006`, public-local gates `19899 19900 19902 19903 19904 19905
  19906`, and a Chromium DOM dump where `#csd-extra` contains
  `cet-workbench`, `cet-op`, `cet-crush`, `cet-aider`, and `cet-goose`.
- 2026-07-14 Codex main-bar task status rule: the same account/task-state
  display must apply to the Codex WebTTY main page itself, not only the Mobile
  AI Workbench drawer. `ttyd-device-gate-proxy` injects
  `codex_main_bar_task_status`, which rewrites main account buttons as
  `C<N> · <name> / <type> / <任务状态>`. Keep `更多` short; do not rewrite it as
  `展 C<N> · <任务状态>`. `/sessions.json` must include all five
  accounts and a `task_state` field. UI auto-reload must treat the top-level
  shell page as visible so already-open Codex pages receive these bar changes
  after a service restart.
- 2026-07-14 Codex main-bar mobile layout rule: when the main `更多` dock is
  expanded, the `收 C<N> · <任务状态>` button must remain the first child of the
  dock and use sticky top positioning. The dock must be bounded to the phone
  viewport with internal vertical scrolling, so users never need to scroll to
  the bottom of an over-tall dock just to collapse it.
- 2026-07-14 follow-up: do not hard-code the Codex WebTTY dock top offset
  against the quota/status bar. `ttyd-device-gate-proxy` should compute
  `--codex-dock-top` from `#codex-quota-strip.getBoundingClientRect().bottom`
  plus a small gap, and use that variable for both collapsed and expanded dock
  `top` and `max-height`. This prevents the `展/收` control from overlapping
  the top quota bar when the quota/status strip wraps on mobile.
- 2026-07-14 WebTTY injection guard: when adding injected scripts in
  `ttyd-device-gate-proxy`, detect existing scripts by a real
  `<script id="...">` tag, not by raw substring. Terminal output can contain
  script ids such as `codex_simple_account_surface`, and a substring check will
  falsely skip injection.

## Operating Model

Use the accounts as a dynamic resource pool. Do not permanently bind account
identity to roles such as coordinator, implementer, or reviewer, because quota,
rate limits, provider health, account risk, and active context differ over time.

Each task receives a temporary lease:

- `owner`: the account currently responsible for user-facing progress.
- `worker`: any available account assigned a bounded implementation or research subtask.
- `reviewer`: any available account assigned read-only validation.
- `fallback`: the next account allowed to continue if the owner hits quota, errors, or becomes risky.

Lease selection must be recalculated at task start and at phase boundaries. Any
of the three accounts can be owner, worker, reviewer, or fallback if its current
health and quota are suitable.

Selection inputs:

- 5-hour remaining quota, if available.
- 7-day remaining quota, if available.
- API/sub2api trusted usage state, if applicable.
- active task state in tmux/WebTTY.
- whether the account already carries useful context for the current task.
- recent usage-limit or provider-error messages.
- account-risk cooldown, described below.

2026-07-12 example from `/quota.json`:

- Account 1 Plus: 5h used 100%, 7d used 67%; not a good owner until 5h reset, but can resume after reset because it has native Plus context.
- Account 2 Team: 5h used 100%, 7d used 16%; better long-window reserve than Account 1, but currently also blocked by 5h quota.
- Account 3 API: official 5h/7d fields unavailable; use sub2api trusted usage and provider health instead of guessing official quota.

When a window is exhausted, do not keep prompting that account. Move the lease
or wait for reset.

## Conflict Rules

- Never let two accounts edit the same file class at the same time.
- Shared config must have a temporary lease owner, not a permanent account owner:
  - `~/.codex/config.toml`, `~/.codex-*/config.toml`: one active lease owner only.
  - `~/.local/bin/codex-*`, `~/.config/codex-shell-env/*`: one active lease owner only.
  - `~/.local/share/ttyd-codex/*` and WebTTY UI: one active lease owner only.
  - `~/.ai-context/runbooks/*`: one active lease owner only.
- Repo code changes should use worktree or file-level ownership:
  - owner account: main workspace and final merge.
  - worker account: one bounded module or one dedicated worktree.
  - reviewer account: read-only unless explicitly assigned a separate worktree.
- If two accounts need the same repository, create separate worktrees under `/var/mnt/ai/cache/codex-worktrees/`.
- Before editing shared files, an account must inspect current file contents and recent tmux state for the other accounts.

Lease handoff rule:

- The old owner records current state, touched files, verification status, and
  next command in `~/memory/codex-routing-ledger.jsonl`.
- The new owner reads that ledger entry and the latest pane capture before
  continuing.
- Do not hand off by copying account-local `auth.json`, session database, cache,
  or logs into another `CODEX_HOME`.

## Cost Routing Policy

Do not do frequent hot model switching inside one long coding session. It tends to lose prompt-cache benefits and repeats large context. Route at task start, then escalate only at phase boundaries.

Default route chooses both a route class and an account lease.

- `fast`: reading, grep/search, small explanations, status checks, runbook lookups.
  - Model target: cheap/low effort.
  - Account target: healthiest available account; prefer one with low active context cost and enough quota.
- `standard`: normal code edits, single-module fixes, focused tests.
  - Model target: `gpt-5.5`, low or medium effort.
  - Account target: account with enough 5h quota and no active conflicting file lease.
- `deep`: cross-module refactor, persistent test failures, architecture decisions, security-sensitive changes, unclear root cause after one failed pass.
  - Model target: strongest available model or higher reasoning effort.
  - Account target: account with best quota/risk balance; add a separate reviewer lease if possible.

Account selection score:

- Hard block if current pane shows usage-limit, auth error, provider error, or
  repeated request failure.
- Hard block if account has an active lease on a different high-risk task.
- Prefer higher 5h remaining for interactive coding.
- Prefer higher 7d remaining for large multi-hour work.
- Prefer API/sub2api for batch, tests, and retry-heavy tasks when trusted usage
  data is available.
- Prefer native Plus/Team accounts for tasks that benefit from official Codex
  TUI behavior and prompt cache, if their quota is healthy.
- Prefer continuing on the same account when it already has useful context and
  quota is not constrained.

Account-risk cooldown:

- If an account hits usage limit, mark it unavailable until the reported reset.
- If an account shows auth/provider errors, mark it degraded until one clean
  health check passes.
- If an account has many failed or repeated prompts, reduce priority for new
  deep tasks.
- Do not route around limits by hammering all accounts with the same prompt.

Escalation triggers:

- Same failure repeats twice.
- More than three files need behavioral changes.
- Tests fail after one targeted fix.
- The task touches auth, secrets, routing, phone/Haven, systemd, SSH, router, or shared Codex config.
- The model starts broad-searching or producing large unbounded output.

De-escalation triggers:

- Task is pure lookup, summarization, command output compression, or one-line config verification.
- The next step is mechanical validation already specified by a runbook.
- A stronger account/model produced a plan and only execution remains.

## Router Shape

Current SSH entry:

- Use `codex-smart "task"` as the no-button command-line router.
- Use `codex-smart --status` to inspect account health.
- Use `codex-smart --dry-run "task"` to preview route/account/model without spending model tokens.
- Use `codex-smart --send "task"` only when deliberately sending into the selected interactive tmux pane. This uses that pane's currently running model; it does not hot-switch an already running TUI model.
- `codex-smart` is now a thin compatibility wrapper around `codex-router`; router owns task classification, account selection, explicit model parsing, model choice, and reasoning effort. Default `codex-smart "task"` submits through `codex-router` with `wait=true`.
- Explicit model names in task text (`gpt-5.6-sol`, `gpt-5.5`, `gpt-5.4`) override the route default in both `codex-router` and `codex-smart`. Explicit effort words (`high`/`medium`/`low`, `高`/`中`/`低`) override effort; `gpt-5.6-sol` defaults to high effort when no effort is specified.
- Tested 2026-07-12: with Account 1/2 5h quota exhausted, `codex-smart --exec --route fast '只回复 OK，不要运行命令，不要解释。'` selected Account 3, launched `gpt-5.5` with `reasoning effort: low` via `sub2api`, and returned `OK`.
- 2026-07-14 账号 13（Codex 3）503/502 复盘：先不要把 `503 no available accounts` 或长时间 `502 context canceled` 直接判断成额度问题。正确顺序是：
  1. 查 `accounts` 表里 `schedulable/rate_limited_at/rate_limit_reset_at/temp_unschedulable_reason/error_message`。
  2. 查 `account_groups` 是否仍绑定到目标 group。
  3. 必要时重启 `sub2api` 清理 scheduler cache，避免内存快照陈旧。
  4. 对目标账号执行管理员动作：`DELETE /api/v1/admin/accounts/<id>/temp-unschedulable`、`POST /clear-error`、`POST /refresh`。
  5. 如果请求仍卡住，再核对 `proxy_id`。本次 13 号与 10 号同源账号，10 挂了 `mihomo-local`(`proxy_id=1`)，13 没挂；补上代理后，故障从超时/502 变成上游明确 `429 usage_limit_reached`，才算定位到真实限额。
  6. 因此结论是：`502/503 -> 先排调度和代理；429 -> 才是上游真实限额`。WebTTY 顶栏应显示 `限额至 <时间>`，不要继续把它显示成泛化的“官方未知”。
- 2026-07-15 Codex 3/4/5 限额页标注：如果 `curl -H 'X-Device-Code: w19900422' http://127.0.0.1:1900N/quota.json` 里 `upstream_rate_limit.active=true`，恢复时间以 `upstream_rate_limit.reset_at` / Sub2API `accounts.rate_limit_reset_at` 为准。`~/.local/bin/ttyd-device-gate-proxy` 注入 `codex_quota_limit_marker`，持续把顶栏写成 `当前 限额至 <本地时间>`、`5h 限额`、`7d 等待`，防止旧的 age-only 脚本把提示覆盖成 `已用 N 天`。改完只需重启 gate 服务 `systemctl --user restart ttyd-codex3.service ttyd-codex4.service ttyd-codex5.service`；不要杀 tmux 或重启 backend，除非 `/status` 不健康。
- 2026-07-15 上游 `Workspace deactivated (402)` 判据：当 `/v1/responses` 返回 `502 Upstream request failed`，并且 `accounts.error_message` 明确为 `Workspace deactivated (402): workspace has been deactivated` 时，该账号已被上游停用。重启 WebTTY、清 scheduler cache、`clear-error` 或等待本地 `rate_limit_reset_at` 都不会恢复它；保留页面入口供查看，但将该 slot 视为不可用，使用 `codex-sub2api-json-bind` 或 `codex-sub2api-claim-bind` 绑定新的有效且独立的 OAuth 来源后，再运行 provision health check。C4/C5 已确认是不同的 OpenAI 用户，但同属一个 `k12` workspace（仅比较指纹，绝不记录原值），且都没有 refresh token；因此它们不是同一账号，却共享同一工作区的可用性，不能互为独立备用。新增/复刻 slot 时应比较 workspace 指纹和 `refresh_token` 是否存在；已停用 workspace 中的多个用户不能充当彼此独立的备用账号。
- C4/C5 的停用观察由 `~/.local/bin/codex-k2-workspace-watch` 和 `codex-k2-workspace-watch.timer` 负责：每天用其 slot-local API key 做一次最小 `/v1/responses` 实测，状态写到 `~/.local/state/codex-k2-workspace-watch.json`，Mobile AI Workbench 会显示“上游工作区停用 · 观察 N/15 天”。任一探测成功即清零失败窗口；连续 15 天失败时，脚本禁用 C4/C5 的 WebTTY、backend 和 Haven timer，并结束其 tmux session，但保留 OAuth/数据库记录以便后续人工恢复。
- 停用观察状态必须同时出现在 Mobile AI Workbench 和所有 Codex WebTTY 顶栏 C1-C5 账号按钮中。`ttyd-device-gate-proxy` 将 state 文件附加到 `/quota.json` 的 `availability` 字段，并由 `codex_account_workspace_availability` 注入脚本把 C4/C5 按钮标红并显示“上游工作区停用 · 观察 N/15 天”。改动后重启五个 gate：`systemctl --user restart ttyd-codex.service ttyd-codex2.service ttyd-codex3.service ttyd-codex4.service ttyd-codex5.service`；不要重启 backend 或 tmux。
- 2026-07-15 账号按钮限额颜色：`ttyd-device-gate-proxy` 还注入 `codex_account_limit_button_status`。它每 5 秒读取 `/quota.json`，给限额账号按钮加 `cqs-limited` / `data-codex-limit=limited` 红色状态；每 1 秒按本地 `reset_at` 时间重新判断，到点后即使后端状态稍后才刷新，也会先恢复按钮普通颜色。验证页面是否拿到脚本：`curl -fsSL -H 'X-Device-Code: w19900422' 'http://127.0.0.1:19003/?device=w19900422' | rg 'codex_account_limit_button_status|setInterval\\(refresh,5000\\)'`。
- 2026-07-15 额度条并入账号按钮：独立 `#codex-quota-strip` 顶栏由 `codex_account_button_quota_bars` 隐藏，额度信息写入 C1-C5 账号按钮。限额账号显示 `限 MM-DD HH:mm` 并保持红色；官方额度账号显示 `5h`/`7d` 进度条；Sub2API/API 账号只显示精简 `API`。不要再注入旧的 `codex_account_limit_button_status` 纯文字脚本，否则它会和进度条互相覆盖造成闪烁。`codex_main_bar_task_status` 的账号渲染必须保留现有 `.cqs-quota` DOM，并避免 1 秒级整块重绘；`codex_account_button_stable_layout` 和 `codex_account_button_quota_bars` 必须后置，用于加宽按钮、固定高度，并在状态脚本重绘后同步恢复额度 DOM；legacy smart-account-zero guard 只隐藏/移除可见 `0` smart 按钮，不要移除 legacy-named `codex_smart_account_zero` host 注入。以后不要再新增独立额度浮条，额度入口应放入账号按钮、`更多` 或 `/quota` 页面。

Phase 1: manual router.

- Add explicit commands:
  - `codex-fast`: cheap route for lookup and explanation.
  - `codex-standard`: normal implementation route.
  - `codex-deep`: high-reasoning route.
  - `codex-smart`: thin CLI/WebTTY compatibility wrapper over `codex-router`;
    do not add a second classifier or model chooser there.
- Keep current token-safe command wrappers in all routes.
- Do not restart live tmux sessions automatically. Apply to new sessions first.

Phase 2: task ledger.

- Add a small ledger under `~/memory/codex-routing-ledger.jsonl`.
- Record:
  - task id
  - owner account
  - worker/reviewer/fallback accounts
  - route
  - files claimed
  - quota snapshot
  - risk/cooldown state
  - start/end status
  - verification command
- Refuse or warn when another live account claims the same file.

Phase 2.5: project registry and context packs.

- Implemented 2026-07-13 in `~/.local/bin/codex-router`.
- Project registry file: `~/memory/codex-projects.json`.
- Context packs directory: `~/memory/context-packs/`.
- Router now auto-detects project from task text and optional cwd, then chooses:
  - project id,
  - resolved cwd,
  - context pack,
  - preferred account bias,
  - preferred route mode bias.
- Initial seeded projects:
  - `codex-router`
  - `codex-webtty`
  - `haven-phone`
  - `termhive`
  - `opencode`
  - `system-home`
- Context packs are intentionally short. They carry stable local knowledge,
  key files, rules, and verification commands. They are loaded into the prompt
  instead of reusing large mixed-session history.
- Implemented 2026-07-13 follow-up:
  - If a project has `preferred_accounts` and at least one preferred account is
    healthy, router now ranks within that preferred pool first; non-preferred
    accounts are fallback only.
  - If the latest task used the same project on the same account, router adds a
    sticky bonus so follow-up work tends to continue on that account instead of
    hopping for marginal quota differences.
  - Verified 2026-07-13: `codex-smart --dry-run` and WebTTY `/smart/decide`
    return project/context pack fields, and `build_prompt()` includes the
    selected `context_pack_text`.
  - Fixed 2026-07-13: project scoring no longer gives a cwd bonus for the broad
    default `/var/home/charlie` project root. Without this, tasks such as
    `修 termhive 项目恢复` could be incorrectly classified as `codex-router`.
    Verify with:
    `codex-smart --dry-run "修 termhive 项目恢复"` -> `project=termhive`,
    `context_pack=termhive.md`.

Phase 3: WebTTY integration.

- Implemented 2026-07-13 in `~/.local/bin/ttyd-device-gate-proxy`:
  - `/smart/status` calls `codex-smart --status`.
  - `/smart/decide` calls `codex-smart --dry-run`.
  - `/smart/send` calls `codex-smart --send`.
  - `/smart/exec` calls `codex-smart --exec`.
  - Implemented 2026-07-13 follow-up: WebTTY `0 Smart` now injects into the
    terminal page by default and passes the active tmux pane cwd into
    `codex-smart`, so browser-triggered routing can follow the current project
    directory instead of always falling back to `/var/home/charlie`.
  - Implemented 2026-07-13 follow-up: automatic context is no longer limited to
    `0 Smart`. `ttyd-device-gate-proxy` exposes `/context/wrap` and routes
    `/tmux-send` through `~/.local/bin/codex-context-wrap` by default. The
    wrapper detects project/cwd/context pack, skips slash commands and shell-like
    commands, and prepends a short `[自动上下文]` block before sending to the
    current account pane. Native WebTTY typing also injects
    `codex_native_input_auto_context`, which watches ttyd WebSocket input and,
    on Enter for a natural-language line, clears the raw line and resubmits it
    through `/tmux-send`.
  - Verify automatic context for all account windows without touching live
    Codex sessions:
    `curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19000/ | rg 'codex_native_input_auto_context'`
    and
    `curl -X POST -H 'X-Device-Code: w19900422' --data '修 WebTTY 账号4 左上角天数' http://127.0.0.1:19000/context/wrap | jq '.result | {wrapped,project,context_pack}'`.
  - Implemented 2026-07-13 follow-up: injected pages include
    `codex_ui_auto_reload`, which polls `/ui-version` and reloads only when the
    proxy UI version changes. If a user is editing an input/textarea or the page
    is backgrounded, reload is delayed until focus/visibility returns. After
    changing injected WebTTY scripts, restart the gate/backend services once;
    current old pages should reconnect/reload, and future changes are handled by
    `/ui-version`.
  - `/smart/*` is retained only as a compatibility API for older callers; the
    visible WebTTY UI must expose a single Router panel, not a separate
    `0 Smart` panel.
  - Account `1/2/3` clicks are captured and rendered as same-page iframe tabs
    at z-index `2147483646`, so switching does not navigate away from the
    current terminal page.
  - Account 4 Sub2API setup defaults to `group_id=14` (`openai-codex-4`);
    do not reuse `group_id=3`, because that makes Codex 3 and Codex 4 compete
    for the same upstream account pool.
  - The `生成4` button calls `/smart/setup-account4`, which wraps
    `~/.local/bin/codex-account-provision --account 4 --primary-account-id 14
    --fallback-account-id 10 --restart --health-check --json`.
  - If account 4 shows `401 Unauthorized` with `API_KEY_DISABLED`, distinguish
    WebTTY/device-gate auth from Sub2API/model auth. A healthy page on `19003`
    can still have a stale Codex process environment. Check the pane pid from
    `/run/user/1000/tmux/codex4.sock` and compare `/proc/$PID/environ`
    `OPENAI_API_KEY` with the active `codex4-sub2api` key preview/hash. Rerun
    the provision command above so stale tmux sessions are killed and
    `/v1/responses` is health-checked.
  - Browser-level check on `19000`: clicking account `2` kept top-level
    `location.href` on `http://127.0.0.1:19000/`, created one iframe, and made
    account `2` visible.
  - Implemented 2026-07-13: each top-level Codex WebTTY page exposes
    `/model` and `/model/switch`. The visible compact dock is a right-side
    vertical bar with quick buttons for `gpt-5.4` and `gpt-5.5-mini`; switching
    writes the current account `config.toml`, archives the current screen, and
    restarts the account tmux session only after browser confirmation.
- Add route buttons to `/sessions` or the Codex task manager:
  - `Fast`
  - `Standard`
  - `Deep`
  - `Review`
- Show live ownership and claimed files beside each account.
- Use existing `/quota.json` and `/sessions.json` data to prefer the healthiest
  account and to avoid accounts currently capped, busy, or degraded.

Phase 4: bounded automatic escalation.

- Keep hot switching conservative:
  - no mid-turn model swap;
  - no automatic restart of live Codex panes;
  - escalation creates a new task handoff or asks the coordinator to resume with a stronger profile.
- Use the router classifier only for new tasks or explicit `codex-smart` launches.

## Implementation Tasks

1. Preserve Account 2's token-safety work.
   - Verify `env.sh` syntax.
   - Verify `codex-token-safe-run` clamps noisy commands.
   - Keep `codegraphcontext update /var/home/charlie` blocked.

2. Add route profiles.
   - Create `fast.config.toml`, `standard.config.toml`, and `deep.config.toml` for each `CODEX_HOME`.
   - Keep auth and provider details account-local.
   - Share only common policy text and MCP definitions.

3. Maintain `codex-smart` as a wrapper.
   - Do not duplicate deterministic keyword rules, explicit model parsing, or account scoring in `codex-smart`.
   - Add new routing policy to `codex-router` first.
   - Keep `codex-smart --send` as tmux paste only; it cannot hot-switch the running TUI model.
   - If all suitable accounts are capped, report reset times instead of forcing retries.

4. Add conflict ledger.
   - Start with advisory warnings, not hard locks.
   - Store ledger in shared memory.
   - Make entries expire or close when the pane/task completes.

5. Add verification.
   - `bash -n` for all wrappers.
   - TOML parse for all profile configs.
   - Dry-run classification examples:
     - "查一下日志为什么失败" -> fast
     - "修复这个单文件 bug 并跑测试" -> standard
     - "重构 Haven/Codex 多账号入口避免冲突" -> deep

6. Provision or repair API-backed Codex accounts with the script.
   - Example:
     `~/.local/bin/codex-account-provision --account 4 --primary-account-id 14 --fallback-account-id 10 --restart --health-check --json`
   - The script creates/repairs the `openai-codex-N` group, `codexN-sub2api`
     key, `~/.codex-N/auth.json`, `~/.codex-N/config.toml`,
     `~/.config/codexN-sub2api.env`, service restart, and a tiny responses
     health check.

7. Rotate slot `1/2/3` from a delivered claim code.
   - Example:
     `~/.local/bin/codex-sub2api-claim-bind 2 EUR-RQ9OYJKXW4`
   - Use this when the user bought a delivered Plus/Team/Codex claim code and
     wants the slot replaced without sharing quota with another slot.
   - Verification:
     - `sudo podman exec sub2api-postgres psql -U sub2api -d sub2api -c "select ag.account_id, a.name, a.status from account_groups ag left join accounts a on a.id=ag.account_id where ag.group_id=(select group_id from api_keys where name='codex2-sub2api' and deleted_at is null limit 1);"`
     - `curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19001/quota.json | jq '.accounts[] | select(.account=="2") | {upstream:(.sub2api.account.id), name:(.sub2api.account.name)}'`
     - `tmux -S /run/user/1000/tmux/codex2.sock capture-pane -t haven-codex2 -S -40 -p`

## Operational Notes

- 2026-07-16 smoothness fix: `codex3-sub2api-usage-sync.timer` runs every 5
  minutes at idle priority, not every minute. The script keeps
  `~/.local/state/codex3-sub2api-usage-sync/state.json` and skips Sub2API
  Postgres work when Codex 3 session JSONL file size/mtime signatures are
  unchanged. Verification:
  `~/.local/bin/codex3-sub2api-usage-sync; ~/.local/bin/codex3-sub2api-usage-sync`
  should return a normal first result and then
  `{"ok":true,"skipped":"unchanged","scanned":0,"inserted":0}` when no session
  files changed.

## Non-Goals

- Do not implement continuous in-session hot model switching first.
- Do not share account auth files.
- Do not permanently assign one account to one role.
- Do not treat unknown quota as unlimited quota.
- Do not route the same failing prompt through all accounts to bypass rate limits.
- Do not enable heavy MCPs globally just to make routing easier.
- Do not auto-restart existing Haven/WebTTY tmux sessions while user tasks are running.

- 2026-07-18 Workbench/account-button consolidation: for UI-only button cleanup, keep account WebTTY pages on one injected dock path instead of stacking legacy top-level overlays. In `~/.local/bin/ttyd-device-gate-proxy`, top-level account pages should inject the compact set: `codex_mobile_ime_stability`, `codex_mobile_viewport_lock`, `codex_c7_stable_behavior`, `duckdns_device_gate_inject`, `codex_interrupt_watch`, `codex_native_input_auto_context`, `codex_ios_panel_activation`, `codex_project_float`, `codex_simple_account_surface`, `codex_network_monitor_button`, `codex_external_tools`, smart sort except C5/C7/C8, and `codex_ui_auto_reload`. Do not re-add legacy competing docks such as `codex_stable_router_dock`, `codex_account_ui_final`, `codex_account_button_quota_bars`, or `codex_account_egress_labels` unless intentionally reverting. Workbench homepage should keep primary actions short (`派发` / `会话` / `多窗` / `新建` / `刷新`) and `/buttons` should be the organized account/tool panel. UI-only changes restart only `ttyd-codex*.service` gates and `mobile-ai-workbench.service`; verify with `curl -L ...19000/?device=...` for `codex_simple_account_surface` and absence of the legacy dock markers, plus `curl ...19888/api/status` showing all accounts.
- 2026-07-18 Workbench `/buttons` compact v2: user wanted a more visible reduction, not just label tweaks. `~/.local/bin/mobile-ai-workbench` now renders `/buttons` as `账号控制台` with a sticky six-button quick bar (`终端`, `派发`, `会话`, `多窗`, `额度`, `端口`), compact grouped account cards, and a collapsed `更多工具 / 低频入口` details section for plugins and Super. Account cards only select the active account; the quick bar actions apply to that active account. After editing, restart only `mobile-ai-workbench.service` and verify with headless DOM for markers `compact v2`, `data-panel="terminal"`, `C1 ·`, and `更多工具 / 低频入口`.
- 2026-07-18 Workbench duplicate 展/收 cleanup: Workbench root (`:19888/`) must not show its old bottom-right floating `tool-toggle` (`展/收 C<N>`) while embedding Codex account iframes, because the inner account dock already has the real `收/展 C<N>` control. Keep only the inner account dock on the terminal view and expose the organized `/buttons` account console as a normal top taskbar `账号` link. If duplicate collapse buttons return, inspect `~/.local/bin/mobile-ai-workbench` for `.tool-toggle` visibility and taskbar `/buttons` link; restart only `mobile-ai-workbench.service`. Verify with a 390x844 screenshot of `http://127.0.0.1:19888/?device=...`: one visible `收 C<N>` dock button and no bottom-right green `展 C<N>` floating button.
- 2026-07-18 mobile button sizing pass: phone UI buttons should use consistent touch sizes, not mixed tiny/giant controls. Workbench root `:19888/` taskbar buttons are 40px high, account tabs are about 118x54 on narrow screens, and scrollbars are hidden for horizontal strips. Workbench `/buttons` uses 42px quick buttons in a 3-column phone grid, account cards are single-column full-width cards around 62px min height, and low-frequency plugins stay collapsed. Individual Codex account pages should keep the right-side dock account list readable on mobile: `codex_account_smart_sort` uses one column under 520px, 58px account cards, 42px collapse/action buttons, and hides secondary meta instead of squeezing two unreadable columns. UI-only size changes restart `mobile-ai-workbench.service` and `ttyd-codex*.service`; verify with 390x844 screenshots for `/buttons`, `:19888/`, and `:19000/?view=frame`.

- 2026-07-18 Codex WebTTY 断连后输入法保活修复：用户报告“connect/重连旧逻辑不对，断开后输入法弹窗点击页面会马上关闭”。`~/.local/bin/ttyd-device-gate-proxy` 现在注入 `codex_input_panel_persist`：当 `#codex-stable-input.open` / `#codex-input-panel.open` / `#codex-ios-home-input.open` 存在时，终端区域的 `pointerdown/touchstart/click/focusin` 会被拦截并重新聚焦输入 textarea，避免 Android/iOS 输入法被页面焦点抢走。重连逻辑在移动端即使 `/status` 连续健康也只显示“手动重连”，不自动 `location.reload()`，避免断线恢复关闭输入法。验证：`for p in 19000 19001 19002 19003 19004 19005 19006 19007; do curl -fsS -H 'X-Device-Code: w19900422' "http://127.0.0.1:$p/?view=frame" | rg 'codex_input_panel_persist|不会自动关闭输入法|MIN_RELOAD_MS=10000'; done`，并确认不含 `codex_ttyd_reconnect_autofix`。UI-only 修改只重启 `ttyd-codex{,2,3,4,5,6,7,8}.service` 和 `mobile-ai-workbench.service`，不要重启 backend/tmux/Sub2API。

- 2026-07-18 Codex/WebTTY 多通道后台预热：Workbench 原本已有 `/speed` / `/api/speed`，但只在打开页面时测速。现在新增 `~/.local/bin/mobile-ai-route-prewarm` 和 `mobile-ai-route-prewarm.timer`，每 2 分钟后台触发 `http://127.0.0.1:19888/api/speed?force=1`，同时预热 C1-C8 的 `/status` 与 `/quota.json`，结果写入 `~/.local/state/mobile-ai-route-prewarm/latest.json`。Workbench 新增 `/api/route-best` 读取该状态，供手机页面/按钮选择最快可用通道。它只做 HTTP 轻量预热和测速，不建立 WebSocket，不创建 tmux 客户端，不重启账号。验证：`systemctl --user is-active mobile-ai-route-prewarm.timer`; `curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/api/route-best | jq '{ok,generated_at,speed_summary,best_codex:(.best[]|select(.short=="c1"))}'`。

- 2026-07-18 WebTTY 打开速度持续监控/优化：不要把 `/status ok` 当成“手机网页打开快”。用户实际感知仍可能是 2-3 秒。现在 `ttyd-device-gate-proxy` 注入 `codex_web_perf_beacon`，页面 `load` 后用 `navigator.sendBeacon('/perf', ...)` 上报 Navigation Timing 到 `~/.local/state/codex-webtty-perf/account-N.jsonl`；`codex-webtty-perf-summary.timer` 每 5 分钟生成 `~/.local/state/codex-webtty-perf/summary.json`，统计 24h `load_p50_ms/load_p95_ms/dcl_p95_ms/slow_count`。Workbench `/go/c1`-`/go/c8` 默认 `mode=smart`，本机请求走 local，手机请求根据 `mobile-ai-route-prewarm` 最近成功通道在 LAN/NetBird/DuckDNS/当前 host 间选择，不把手机重定向到 `127.0.0.1`。验证：`systemctl --user is-active mobile-ai-route-prewarm.timer codex-webtty-perf-summary.timer`; `curl -b mobile_ai_workbench_device=w19900422 -I http://127.0.0.1:19888/go/c1`; `cat ~/.local/state/codex-webtty-perf/summary.json | jq '.accounts'`。

- 2026-07-18 WebTTY 账号信息切换慢修复：用户报告切换账号看 Codex 页面信息约 5 秒。实测本机 `/status` 约 5ms、页面 HTML 约 15-19ms，不是后端/网络整体故障；瓶颈是首次 `/quota.json` 冷缓存聚合，C1 冷启动约 6.05s，缓存命中约 1ms。修复：`~/.local/bin/ttyd-device-gate-proxy` 默认 `CODEX_WEBTTY_QUOTA_CACHE_MS` 与 `CODEX_WEBTTY_SUB2API_CACHE_MS` 从 10s/15s 调为 180s，并由 `mobile-ai-route-prewarm.timer` 每 2 分钟预热 C1-C8 `/quota.json`。验证：`for p in 19000 19001 19002 19003 19004 19005 19006 19007; do curl -H 'X-Device-Code: w19900422' -o /dev/null -w "$p %{time_total}\n" http://127.0.0.1:$p/quota.json; done`，应约 1-5ms。若又出现 5s，先查额度冷缓存/预热 timer，不要先判定网络故障或重启账号。
- 2026-07-18 WebTTY 多通道测速修正：C1-C8 的 `19000-19007` 是 loopback gate，只能本机访问；LAN/NetBird/手机应使用 `19899/19900/19902/19903/19904/19905/19906/19907` 这些外部入口。`mobile-ai-route-prewarm` 已修正为 local 测 `1900x`，LAN/NetBird/DuckDNS 测外部端口，并强制禁用 Python urllib 代理，避免 `HTTP_PROXY` 导致 LAN/NetBird/DuckDNS 误报 timeout/502。新增手机侧 `phone-webtty-route-probe.timer`，每 2 分钟通过 ADB 从 PKR110 测 `192.168.123.71:19899`、`100.87.238.153:19899`、`charlie1990.duckdns.org:19899`，状态写入 `~/.local/state/phone-webtty-route-probe/latest.json`。这用于判定手机真实入口质量。

- 2026-07-18 Mobile-first WebTTY verification rule: PC/Fedora checks are insufficient for phone-reported WebTTY bugs. Always classify and verify the actual phone path: USB adb reverse `127.0.0.1:<external-port>`, LAN `192.168.123.71:<external-port>`, NetBird `100.87.238.153:<external-port>`, or DuckDNS/FRP `charlie1990.duckdns.org:<external-port>`. `19000-19007` are loopback-only gate ports and must not be used as phone/LAN/NetBird targets. Durable fallback: `webtty-usb-reverse-ensure.timer` keeps USB reverse for `19888`, `19899`, `19900`, `19902`, `19903`, `19904`, `19905`, `19906`, and `19907`; when USB is connected, the fastest and most isolated phone URL is `http://127.0.0.1:19899/?device=<device-code>` for C1 and corresponding external ports for other accounts. Phone evidence must include ADB-side curl/nc and a screenshot when the issue is visual/input/IME/blank terminal.

### 2026-07-18 C1 mobile `Press Enter to Reconnect` overlay repair

Symptom: real Android Chrome over USB reverse still showed ttyd native `Press ↵ to Reconnect` while the terminal text was visible in the background and server checks were healthy.

Evidence/interpretation:

- Phone USB route `http://127.0.0.1:19899/status?device=w19900422` returned HTTP 200 in a few milliseconds.
- C1 gate `http://127.0.0.1:19000/status` returned `ok=true`, pane `100x30`, `error=""`.
- Therefore this is a stale mobile Chrome/ttyd WebSocket overlay, not a Codex account, Sub2API, tmux, or network outage.

Fix applied: `~/.local/bin/ttyd-device-gate-proxy` now injects `codex_ttyd_overlay_reconnect_guard` on top-level and `?view=frame` Codex pages. The guard detects `Press Enter/↵ to Reconnect` or `连接待恢复`, checks `/status`, first simulates Enter, and if the stale overlay remains reloads only when the visible surface is foregrounded and no mobile IME/input panel is busy.

Safe recovery sequence:

```bash
node --check ~/.local/bin/ttyd-device-gate-proxy
systemctl --user restart ttyd-codex.service
curl -fsSL -H 'X-Device-Code: w19900422' 'http://127.0.0.1:19000/?device=w19900422' | rg 'codex_ttyd_overlay_reconnect_guard'
ts=$(date +%s)
~/.local/bin/adb-record --tag webtty-reconnect-fix -- -s ff3ef385 shell "am start -a android.intent.action.VIEW -d 'http://127.0.0.1:19899/?device=w19900422&r=$ts' com.android.chrome"
~/.local/bin/adb-record --tag webtty-reconnect-fix -- -s ff3ef385 shell screencap -p /sdcard/webtty-after-reconnect-fix.png
~/.local/bin/adb-record --tag webtty-reconnect-fix -- -s ff3ef385 pull /sdcard/webtty-after-reconnect-fix.png /tmp/webtty-phone/webtty-after-reconnect-fix.png
```

Do not restart backend ttyd, tmux, Sub2API, or rotate accounts for this signature.

### 2026-07-18 Workbench WebTTY route repair for 5G/mobile

`~/.local/bin/mobile-ai-workbench` had two route bugs:

1. `linkUrl()` treated `mode=lan` and `mode=netbird` like local mode and used `link.localPort` (`19000-19007`). Phones cannot reach those loopback-only gate ports. LAN/NetBird/DuckDNS must use the external WebTTY ports.
2. The homepage `activeUrl()` used account local ports when Workbench was opened via `127.0.0.1:19888` USB reverse. That made embedded account iframes target `127.0.0.1:19000`, which is not part of the USB reverse mapping. Workbench account frames now use external ports.

Current smart behavior: `/go/c1` through `/go/c8` with `mode=smart` should redirect to `http://charlie1990.duckdns.org:<external-port>/?device=...` when invoked from a local/USB Workbench page, so the URL survives 5G/off-LAN. Explicit modes remain available: `mode=lan`, `mode=duckdns`, `mode=netbird`, `mode=local`.



### 2026-07-19 PKR110 DuckDNS vs NetBird phone WebTTY

- Failure mode: Fedora local and public `curl --noproxy '*' http://charlie1990.duckdns.org:<port>/status` can be OK while PKR110 Chrome still shows `ERR_CONNECTION_REFUSED` for DuckDNS. Do not call the account/WebTTY backend down from that evidence alone.
- Verified phone result at 2026-07-19 15:37: `~/.local/bin/phone-webtty-route-probe auto` selected serial `100.87.37.3:5555`; best route for C1-C8 was NetBird `100.87.238.153` on external ports `19899/19900/19902/19903/19904/19905/19906/19907`. LAN timed out because PKR110 was on cellular/NetBird, not Wi-Fi LAN.
- Durable fix: `phone-webtty-route-probe.service` has drop-in `~/.config/systemd/user/phone-webtty-route-probe.service.d/10-auto-serial.conf` and no longer pins stale `127.0.0.1:15555`.
- Current user-facing workaround/default for PKR110 browser: open NetBird numeric URLs, e.g. `http://100.87.238.153:19899/` for C1, `:19900` for C2, `:19902` for C3, through `:19907` for C8. Numeric NetBird Chrome page was visually verified by UIAutomator showing the WebTTY `Connect` form.
- Do not install a persistent Android hosts override for `charlie1990.duckdns.org -> 100.87.238.153` unless explicitly requested; a temporary bind mount made shell DNS look OK but did not fix Chrome and would hide real DuckDNS/FRP diagnostics.

## 2026-07-19 Generic Sub2API Availability Display Fix

`/quota.json` must not show a Sub2API slot as `有额度` just because its API key/group exists. For every Sub2API-backed slot, check the bound upstream account status and `schedulable`; if the upstream error contains `Workspace deactivated (402)` / `workspace has been deactivated`, expose:

- `ok=false`
- `availability.state="stopped"`
- label similar to `上游工作区停用 · 不会自动恢复`
- recovery text saying a new valid upstream account must be imported/bound

This was added to `~/.local/bin/ttyd-device-gate-proxy` so C6 now behaves like C4 instead of silently lacking availability text. Rate-limited upstreams should show the concrete `rate_limit_reset_at` time, e.g. `预计 <ISO time> 恢复`.

Verify:

```bash
node --check ~/.local/bin/ttyd-device-gate-proxy
systemctl --user restart ttyd-codex.service ttyd-codex2.service ttyd-codex3.service ttyd-codex4.service ttyd-codex5.service ttyd-codex6.service ttyd-codex7.service ttyd-codex8.service
curl -fsS -H 'X-Device-Code: w19900422' http://127.0.0.1:19000/quota.json \
  | jq -r '.accounts[] | [.account, .ok, (.availability.label // ""), (.upstream_rate_limit.reset_at // ""), (.error // "")] | @tsv'
```

- 2026-07-19 Super Button board notice: `mobile-ai-workbench` `/api/super/notice` now includes `codex_line`, `codex_active`, and `codex_accounts[]` for all C1-C8, derived from the shared `19000/sessions.json` and filtered to concise human process/status text rather than code/log fragments. The Android AI Super Button APK polls that endpoint and renders two internal board rows inside the floating capsule/dropdown/expanded panel: first `流程` for the phone/Step flow, second `Codex` for C1-C8 process. It still does not create extra Android notification rows beyond the existing foreground-service notification. After changes, rebuild/install with `~/.local/bin/mobile-ai-super-button-build-install`; verify `curl -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/api/super/notice?device=w19900422` shows 8 `codex_accounts`, and take a real phone screenshot showing both board rows.

- 2026-07-19 Super Button board policy: when the user only gives a direction for the floating AI/notification panel, default to a two-row board layout and let Codex choose the hierarchy, filtering, and evolution. The stable pattern is `流程` first for phone/Step/project flow and `Codex` second for C1-C8 execution, each summarised as `起 / 过 / 尾` and stripped of code/log fragments. Use the board only for human process visibility; keep the Android foreground notification minimal.

## 2026-07-20 Mobile Workbench 手动输入/接码待办

用户希望以后 OpenAI 登录、Codex device-auth、SMS 接码、2FA、付款确认等需要人工操作时，手机 Workbench `:19888` 直接弹出待办，让用户在手机完成并点“我已完成”。

实现：

- Workbench 主程序：`~/.local/bin/mobile-ai-workbench`
- 待办状态：`~/.local/state/mobile-ai-workbench/manual-actions.json`，权限 `0600`
- 页面：`/manual-actions?device=w19900422`
- API：`/api/manual-actions`
- 首页：`/?device=w19900422` 每 10 秒轮询 pending 待办，并弹出触控安全卡片。
- Helper：`~/.local/bin/mobile-manual-action`

默认创建待办命令：

```bash
~/.local/bin/mobile-manual-action \
  --id c10-device-auth \
  --account 10 \
  --title 'C10 Codex 登录授权' \
  --message '请在手机完成 OpenAI 登录、2FA 和接码；完成后点“我已完成”。' \
  --url 'https://auth.openai.com/codex/device' \
  --code '<device-code>' \
  --expires-minutes 15 \
  --notify \
  --open-url \
  --json
```

完成/取消：

```bash
~/.local/bin/mobile-manual-action --id c10-device-auth --done --json
~/.local/bin/mobile-manual-action --id c10-device-auth --cancel --json
```

安全规则：不要把邮箱密码、TOTP secret、OAuth token、API key、SMS 平台 CDK 写进 `title/message/code/url`。页面只放设备码、非敏感链接、账号槽位、操作说明。真正密文继续存 `~/.local/state/codex-account-import/` 或 `~/.local/state/codex-sms/` 的 `0600` 文件。

验证：

```bash
python3 -m py_compile ~/.local/bin/mobile-manual-action
node --check ~/.local/bin/mobile-ai-workbench
systemctl --user restart mobile-ai-workbench.service
curl -fsS -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/api/manual-actions | jq '{ok,pending:(.pending|length)}'
curl --noproxy '*' -fsS -m 8 -H 'X-Device-Code: w19900422' http://charlie1990.duckdns.org:19888/api/manual-actions | jq '{ok,pending:(.pending|length)}'
```

Phone visual verification still requires ADB when available. If `adb devices` is empty, say phone screenshot validation is blocked, but Fedora local + DuckDNS API only prove service/public route health.

## 2026-07-20 Codex Account Manager direct-test recovery rule

`~/.local/bin/codex-account-manager` is now the default entry for Codex/Sub2API availability, repair, and evidence capture.

Current commands:

```bash
codex-account-manager summary
codex-account-manager summary --json
codex-account-manager direct-test --account-id <upstream_id> --model gpt-5.5
codex-account-manager repair --apply
```

Operational rule:

- If a Sub2API upstream still has `rate_limited_at` / `rate_limit_reset_at` but a recent `direct-test` returns top-level `ok=true` with event `test_complete success=true`, `repair --apply` may clear those stale local rate-limit/temp-unschedulable fields. This recovered upstream account `15` for C2 on 2026-07-20 and a real C2 slot smoke then used account `15` successfully.
- Do not clear a real direct-test 429. Upstreams `18`, `20`, `21`, and `22` returned OpenAI `usage_limit_reached` on 2026-07-20 and must keep their reset windows/fallback behavior.
- If a fallback account has the same OpenAI `sub_hash` as the primary, the manager reports `serving_mode=primary_equivalent` rather than counting it as real fallback capacity. This avoids over-counting C1-style duplicate identities.
- C10 upstream `22` still shares identity hash with C8 upstream `21`; redo C10 with `codex-c10-relogin-start` and finish with `codex-c10-relogin-finish` only after the phone/browser visibly authorizes the intended new C10 iCloud account.

Verification snapshot after the fix:

```bash
codex-account-manager summary
curl -fsS -H 'X-Device-Code: w19900422' http://127.0.0.1:19888/api/codex/accounts | jq '.counts'
```

Expected current count after C2 recovery: `primary_usable=5`, `serving_primary=5`, `serving_fallback=4`, `primary_rate_limited=4`, `routable_now=9`.

## 2026-07-20 C10 phone popup default and no-code-log rule

For C10 or any future Codex device-auth / SMS / 2FA step, create the Mobile AI Workbench manual action with both `--notify` and `--open-url` so the phone is brought to the foreground immediately. Do not only create the action and wait for the user to navigate manually.

Default pattern:

```bash
~/.local/bin/mobile-manual-action \
  --id c10-clean-device-auth \
  --account 10 \
  --title 'C10 干净重登 Codex' \
  --message '请确认授权的是目标账号；完成后点“我已完成”。' \
  --url 'https://auth.openai.com/codex/device' \
  --code '<ephemeral-device-code>' \
  --expires-minutes 30 \
  --notify \
  --open-url \
  --json
```

Privacy rule: if auto-filling a verification/device/SMS code into the phone is needed, do not send that code through `adb-record` or any logged wrapper. Use raw `adb` only for the sensitive input step, or prefer a Workbench card/copy button where the opened URL contains only the manual action id. Verify with:

```bash
tail -n 80 ~/.local/state/adb-ops/history.jsonl | rg '<code>' || echo ok_no_code_in_recent_adb_record
```

`~/.local/bin/codex-c10-relogin-start` now passes `--open-url` and no longer opens the OpenAI device page through `adb-record`; the phone foreground target is the Workbench manual-action card.

## 2026-07-20 Mobile Browser Bridge for phone popup/control

When a phone says a Workbench/manual-action page cannot open, do not assume the Workbench service is down and do not default to NetBird. Use the maintained bridge first:

```bash
mobile-browser-bridge probe
mobile-browser-bridge open-manual c10-clean-device-auth --force-stop
mobile-browser-bridge dump --screenshot
mobile-browser-bridge cdp-tabs
```

Current observed PKR110 behavior on 2026-07-20:

- Fedora Workbench `:19888` was healthy locally, on LAN, and on DuckDNS.
- Fedora NetBird was `LoginFailed` and `wt0` did not exist, so `100.87.238.153:19888` was not a valid route.
- Phone HTTP probes succeeded through ADB reverse `127.0.0.1:19888`, LAN `192.168.123.71:19888`, and DuckDNS.
- Android Chrome stayed on a stale NetBird tab until it was foregrounded with explicit `com.android.chrome/com.google.android.apps.chrome.Main` and `--force-stop`.
- Android Chrome exposes a `chrome_devtools_remote` socket, but CDP HTTP on `127.0.0.1:9222` timed out in this state; use UIAutomator text/screenshot as the reliable browser information plane.

`mobile-manual-action --open-url` now calls `mobile-browser-bridge open-manual <id> --force-stop`, which selects USB reverse/LAN/DuckDNS and avoids NetBird when host NetBird is down. It does not use `adb-record` for URL opening or future code autofill.

MCP wrapper:

- Server: `mobile-browser-bridge` in `~/.config/mcp/servers.yaml`
- Script: `~/.local/bin/mobile-browser-bridge-mcp.py`
- Tools: `mobile_browser_probe`, `mobile_browser_open_manual`, `mobile_browser_dump`, `mobile_browser_cdp_tabs`

### Firefox Nightly multi-account browser policy

PKR110 has Firefox Nightly package `org.mozilla.fenix`. For future OpenAI/Codex device-auth, prefer Firefox Nightly as the clean/multi-account browser path instead of Via, because Via and Chrome already showed stale OpenAI accounts.

Policy:

1. First choice: Firefox Nightly + verified working account/container isolation, one container/profile per Codex slot (`C1`, `C2`, ... `C10`).
2. If Multi-Account Containers is not functional on Android, use one dedicated browser package or Android work-profile/app-clone per slot.
3. Never authorize a device code from a page showing an unexpected saved account/display name. Confirm the visible email/identity is the intended slot before approval.
4. `mobile-browser-bridge` now supports `--browser firefox` / `--browser fenix` for explicit Firefox Nightly foregrounding.

### Firefox profile binding is mandatory for Codex accounts

User rule: Firefox Nightly must be configured as different profile/container identities for Codex account login work. Do not use one shared Firefox default profile for all OpenAI accounts.

State/CLI:

```bash
firefox-codex-profile-manager bind 10 --profile 'firefox-nightly:C10'
firefox-codex-profile-manager list
firefox-codex-profile-manager open 10 'https://auth.openai.com/codex/device' --force-stop
```

Important limitation: Android Firefox/Fenix does not expose a stable public `adb am start` argument that selects an internal profile/container. Therefore automation must treat the profile binding as a gate and still confirm the visible Firefox container/profile/account before authorizing. If the Multi-Account Containers/profile plugin exposes a usable Android UI/API later, wire it into `firefox-codex-profile-manager`; until then, do not auto-authorize from a mismatched or unlabelled profile.

### KDE Connect input test result for Firefox/OpenAI login

KDE Connect can be used as a phone input candidate, but on 2026-07-20 it was not reliable for the Firefox Nightly OpenAI email field:

- Paired device: `PKR110` / `75883083456a45978f45ca835c400474`.
- `kdeconnect-cli --help` supports `--send-keys` and `--send-clipboard`.
- Device may show paired but not available until the phone KDE Connect app is foregrounded and `kdeconnect-cli --refresh` runs.
- After setting Android IME to `org.kde.kdeconnect_tp/org.kde.kdeconnect.plugins.remotekeyboard.RemoteKeyboardService`, `kdeconnect-cli --device <id> --send-keys <text>` returned without error but did not inject text into Firefox Nightly's OpenAI login field.
- Restored IME to `com.iflytek.inputmethod.oem/com.iflytek.inputmethod.FlyIME` after the test.

Treat KDE Connect text input as a fallback only until a verified command path exists. For sensitive auth, do not keep retrying blind input; use visible phone confirmation or a dedicated input bridge such as FlexIME once verified.

## 2026-07-21 C1-C10 503 批量故障复盘

### 结论

- 10 个 Codex 账号**全部走 Sub2API**，不存在“正常原生/不用 sub2api”的账号。C1 已于 2026-07-20 转为 `apikey` 模式。
- 当前 **503 是真实 Sub2API 内部状态**，不是假信息，也不是单一 IP 封禁。
- **唯一完全可用的账号是 C9**（上游 25 HalbertTaladay0446@outlook.com）。
- C10 的 `rate_limit_reset_at` 是 stale marker；`direct-test` 返回 **401 token_invalidated**，不是真实 429 限额。

### 数据库实时状态（2026-07-21）

| 账号 | 上游 ID | status | schedulable | error_message | 分类 |
|------|---------|--------|-------------|---------------|------|
| C1 | 10 | error | f | 401 token_invalidated | 需重新 OAuth |
| C2 | 15 | error | f | 401 token_invalidated | 需重新 OAuth |
| C3 | 13 | error | f | 401 token_invalidated | 需重新 OAuth |
| C4 | 16 | error | f | 402 workspace deactivated | 换新上游 |
| C5 | 18 | error | f | 401 token_invalidated | 需重新 OAuth |
| C6 | 15/19 | error | f | 402 workspace deactivated | 换新上游 |
| C7 | 20 | error | f | 401 token_invalidated | 需重新 OAuth |
| C8 | 21 | error | f | 401 token_invalidated | 需重新 OAuth |
| C9 | 25 | active | t | — | 正常 |
| C10 | 22 | active | t | 无 | direct-test 401，实际失效 |

### GitHub 证据

- `Wei-Shaw/sub2api#3620`：401 后账号永久卡在 `status=error`，refresh worker 跳过 error 账号，不会自愈。
- `Wei-Shaw/sub2api#2258`：429 可能被误判成几小时/几天冷却，临时解是 Scheduled Test + auto_recover。
- `Wei-Shaw/sub2api#2040`：管理后台测试 bypass 调度器，不代表真实请求可用。
- `Wei-Shaw/sub2api#2990`：高负载下内存缓存与 DB 不同步，重启才恢复。
- `Wei-Shaw/sub2api#4113`：503 后 failover 耗尽，handler panic。
- `Wei-Shaw/sub2api#4599`：OAuth 账号 `/v1/responses` 任意模型 503，`excluded_account_count=0`。

### 为什么不是 IP 封禁

- 账号走不同代理出口，不是单一 IP。
- 错误分散为 401/402/429/rate_limit_reset_at，不是同一错误。
- DB 里账号 14 (`Lyy-9ECFE00BBDE6-26`) 仍为 `active/schedulable=true`，仅有一次网络 refused。

### 恢复方案

1. **C9**：直接使用，独立可用。
2. **C10**：`direct-test --account-id 22` 返回 401，不是假限流；需重新 OAuth 或换绑新上游。
3. **C2/C3/C5/C7/C8**：全部是 `401 token_invalidated`，必须在**干净/隔离浏览器**重新 `codex login --device-auth`，生成新 `auth.json`，再跑 `codex-sub2api-json-bind`。
4. **C4/C6**：`402 workspace deactivated`，无法恢复，直接换新上游。
5. **不要 reuse 旧 `auth.json`**：OpenAI 已明确 `token_invalidated` / `invalid_refresh_token`，旧 token 救不回来。

### 长期防护

- 升级并保持 **sub2api v0.1.162+**。
- 开启 **Scheduled Test + auto_recover**，让测试通过后自动清除假限流。
- 新账号必须在**干净浏览器/未登录 profile**里做 device auth，避免 reuse 旧登录态。
- 采购优先选**干净个人 Plus + 唯一 email/sub 身份**，避免共享池/Team/workspace。
- 保留 C9 作为主账号，其他 slot 作为任务池。
