# Termius / Mosh / Haven Setup

Updated: 2026-07-04

## Preferred Mobile Setup

Use Termius over Tailscale for the normal shell. Termius Starter is local-only; official cross-device sync requires Pro, so use the Termux/Syncthing setup below when free sync is required.

- Group: `Fedora / TermHive`
- Host label: `Fedora Shell (Mosh)`
- Address: `100.120.189.27`
- Username: `charlie`
- SSH port: `22`
- Protocol: `Mosh`
- Key: `termius_fedora_ed25519`
- Encoding: `UTF-8`
- Locale: `zh_CN.UTF-8`
- Terminal type: `xterm-256color` or `tmux-256color`
- Mosh server command:

```sh
/var/home/charlie/.local/bin/mosh-server-termhive
```

If Termius requires a full raw server command instead of a path, use:

```sh
mosh-server new -s -p 60010:60020 -l LANG=zh_CN.UTF-8
```

Create a second Termius local host for Codex:

- Host label: `Fedora Codex (Mosh)`
- Address: `100.120.189.27`
- Username: `charlie`
- SSH port: `22`
- Protocol: `Mosh`
- Key: `termius_fedora_ed25519`
- Mosh server command:

```sh
/var/home/charlie/.local/bin/mosh-server-codex
```

## Codex Tmux After Connecting

For the normal shell profile, attach the preserved Codex session manually if needed:

```sh
tmux -S /run/user/1000/tmux/codex.sock attach -d -t haven-codex
```

The `Fedora Codex (Mosh)` profile starts this command automatically through `/var/home/charlie/.local/bin/mosh-server-codex`.

## Haven Fallback

Keep Haven as the forced-command SSH fallback:

- Host label: `3 · Fedora Codex (SSH fallback)`
- Address: `charlie1990.duckdns.org` or `100.120.189.27`
- Username: `charlie`
- SSH port: `2225`
- Protocol: `SSH`

Do not use Mosh on Haven ports `2223`, `2224`, or `2225`. Those ports use forced commands, while Mosh needs SSH to execute `mosh-server`.

## Sync To Tablet

Install Termius on the tablet, log into the same Termius account, and enable encrypted vault sync. Hosts, groups, identities, and terminal configuration sync through the Termius account.

## Server State

- `mosh` and `mosh-server` are installed live.
- Firewall permanently allows UDP `60000-61000`.
- Wrapper path: `/var/home/charlie/.local/bin/mosh-server-termhive`
- Codex wrapper path: `/var/home/charlie/.local/bin/mosh-server-codex`
- Tailscale host: `fedora-termhive`
- Tailscale IP: `100.120.189.27`
- Termius dedicated key:
  - Server private key backup: `/var/home/charlie/.ssh/termius_fedora`
  - Server public key: `/var/home/charlie/.ssh/termius_fedora.pub`
  - Phone import folder: `/sdcard/Download/Termius-Fedora/`
  - Public key is installed in `/var/home/charlie/.ssh/authorized_keys`.

## Haven Phone Profiles

- `3 · Fedora Codex (SSH fallback)` is plain SSH on `charlie1990.duckdns.org:2225`; do not enable Mosh on this forced-command profile.
- `6 · Fedora Shell (Mosh)` is Mosh on `100.120.189.27:22` for stable mobile shell use.
- `7 · Fedora Codex (Mosh)` is Mosh on `100.120.189.27:22` and uses the Haven key `Mosh Codex Direct`. The server-side `authorized_keys` entry for this key forces `/var/home/charlie/.local/bin/mosh-server-codex`, so tapping this profile immediately attaches the Codex tmux session.

## Free Sync Without Termius Pro

Termius official sync is a Pro feature. For free phone/tablet sync, use Termux + Syncthing:

- Phone shared source: `/sdcard/RemoteProfiles/`
- Phone installer: `/sdcard/RemoteProfiles/install-termux-remote-profiles.sh`
- Synced commands:
  - `fedora` opens normal Mosh shell.
  - `codex` opens Mosh and immediately attaches `haven-codex`.

Run this once inside Termux on each Android device after Syncthing has synced `/sdcard/RemoteProfiles`:

```sh
sh /sdcard/RemoteProfiles/install-termux-remote-profiles.sh
```

On the phone, this install has already been applied directly to Termux:

- `~/.ssh/config`
- `~/.ssh/termius_fedora`
- `~/bin/fedora`
- `~/bin/codex`
- `~/.profile` and `~/.bashrc` add `~/bin` to `PATH`.
