# Unified Mihomo Control

This directory is the versioned policy source for Fedora and Android. It never
contains a subscription URL, node credential, or generated client profile.

## Control Plane

- Sub-Store: `http://127.0.0.1:19887` on Fedora, owned by `sub-store.service`.
- Sub-Store data: `~/.local/share/sub-store/` (local only; not versioned).
- Policy source: this directory.
- Android runtime: `/data/adb/mihomo_netbird`, managed by Magisk root service
  `/data/adb/service.d/97-mihomo.sh`.

Sub-Store owns the upstream subscription, provider refresh, renaming and
filtering. Generate a Clash Meta/Mihomo profile from it, then apply the common
rules in `rules/common.yaml` and the platform overlay before distributing it.

## Default Policy

1. Private and LAN traffic is direct.
2. Advertising domains are rejected.
3. Chinese domains and IP ranges are direct.
4. All remaining traffic uses the `PROXY` group.

This is intentionally "CN direct, foreign proxy", not GFW-list-only. It keeps
new or uncategorized foreign services working without waiting for a GFW list
update.

## Android Refresh

Keep Clash Meta stopped. Use it only to refresh the source subscription or
edit its profile. After that, apply the generated/active profile to root
Mihomo with:

```bash
./scripts/sync-android-root
```

The root runtime excludes NetBird's UID so NetBird owns Android's only VPN
slot. Clash Meta's VPN-only per-app selection does not transfer; root bypasses
must be explicit UID rules in the Magisk service script.
