# Fedora Overlay

Use local listener ports that do not conflict with host services. Do not
enable Android `redir-port` or UID iptables rules on Fedora. Bind any Mihomo
external controller to loopback unless it is placed behind authenticated LAN
or mesh access.

## Codex Fixed Egress

Codex account traffic is account-pinned, not `AUTO`: C1/C3/C6 use
`美国-US-3`, C2 uses `荷兰-NL-4`, C4 uses `德国-DE-2`, and C5 uses
`德国-DE-3`. The active Fedora profile defines loopback-only mixed listeners
`7892-7897` for groups `OPENAI-C1-OPENAI-C6`; do not expose these ports.
Keep `OPENAI-STABLE` fixed to the C1 US node for native C1 traffic.

Sub2API's per-upstream proxy records use these listener ports for C2-C6.
After changing a selected node, validate the Mihomo group via its loopback
controller, restart `sub2api.service`, and make a minimal `/v1/models`
request through each account's local API key. The Codex WebTTY `更多` cards
and Workbench status must continue to show the matching node label.
