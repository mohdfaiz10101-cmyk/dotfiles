# Chromium Network Recovery

## Confirmed Incident (2026-09-07)

Existing desktop Chromium timed out for both localhost:19910 and :19976,
including explicit 127.0.0.1. Fresh Chromium loaded the WebUI and authenticated
terminal. Recreating only the existing NetworkService child restored all
three original URLs, including webui.charlie1990.duckdns.org:19976.

The exact trigger is unknown. Mihomo restarted at 21:45 and the LAN address
was reapplied at 21:59, but temporal proximity does not prove causation.
No pre-recovery Chromium netlog/stack was captured. Do not call this a proven
Chromium bug, a proven Wi-Fi bug, or a guarantee against recurrence.

## Recovery Tool

- Inspect: `~/.local/bin/chromium-network-recover`
- Recover after confirming the browser symptom:
  `~/.local/bin/chromium-network-recover --repair`
- Desktop launcher: `Chromium Network Recovery` / `浏览器网络恢复`.
- Evidence: `~/.local/state/chromium-network-recover/latest.json` and
  `events.jsonl`; stores no URLs from browsing history, cookies or credentials.
- Requires exactly one current-user default-profile Chromium NetworkService;
  excludes automated/custom-profile browsers, uses pidfd identity protection,
  checks both backend ports first, and applies a five-minute cooldown.
- Keeps browser windows/profile data; ongoing requests/WebSockets may reconnect.
- The tool reports HTTP probes as backend-only and never declares UI healthy.
  Refresh affected tabs and verify the original browser with screenshots.
- No automatic periodic restart: backend health cannot detect an existing
  browser's stuck network state, and unconditional resets interrupt user work.
- Validation: Python compilation and desktop entry validation passed; read-only
  host execution identified exactly one real desktop NetworkService and both
  HTTP probes returned 200. The new repair mode was not invoked against the
  now-healthy browser. The same SIGTERM recovery was verified in the incident.

## Next Recurrence

1. Capture the original error, exact URL, and current device/network path.
2. Compare original browser with a fresh browser and direct backend probes.
3. If practical, capture a default (no sensitive/raw-byte options) Chromium
   net-export before recovery; keep it private and inspect only relevant events.
4. Use the recovery tool only for the matching browser-specific failure.
5. Verify page content/terminal connection, not merely HTTP 200.

Public DNS-over-HTTPS confirmed the webui hostname existed. A local lookup
failure does not prove NXDOMAIN. Phone ADB was offline during this incident;
desktop success does not establish phone or arbitrary external Wi-Fi access.
