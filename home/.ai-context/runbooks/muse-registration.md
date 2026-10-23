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
