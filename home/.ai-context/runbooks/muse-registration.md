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
