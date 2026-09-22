# Runbook: WeChat Linux Flatpak File Picker

## Symptom

- Linux WeChat cannot choose local files to send.
- File picker shows an incomplete local filesystem.
- Dragging Excel or other files into WeChat does not attach/send them.

## Known Cause

On this host, desktop WeChat runs as Flatpak app `com.tencent.WeChat`.
Its packaged metadata may only expose `xdg-download:ro`, so WeChat cannot see
the real XDG document/download folders under `/var/mnt/ai/xdg`.

The host XDG dirs are:

```bash
xdg-user-dir DOCUMENTS
xdg-user-dir DOWNLOAD
```

Expected current values:

- `/var/mnt/ai/xdg/文档`
- `/var/mnt/ai/xdg/下载`

## Fix

Do not grant the whole home directory for this app. On this host, host
`~/.xwechat` is a symlink to `/mnt/ai/cache/auto-migrate/.xwechat`, while the
Flatpak metadata also uses `persistent=.xwechat`. Broad home overrides can make
WeChat touch the host symlink instead of its private Flatpak state and fail
during startup with storage/crashinfo path errors such as:

```text
bwrap: Can't make symlink at /var/home/charlie/.xwechat: destination exists and is not a symlink
[0922/113141.414251:ERROR:filesystem_posix.cc(63)] mkdir /var/home/charlie/.xwechat/crashinfo: No such file or directory (2)
```

Use concrete send-file directories instead:

```bash
flatpak override --user --reset com.tencent.WeChat
flatpak override --user \
  --filesystem=/var/mnt/ai/xdg \
  --filesystem=/var/home/charlie/下载 \
  --filesystem=/var/home/charlie/Desktop:ro \
  com.tencent.WeChat
```

Also ensure the XDG download directory is user-writable. It has drifted to
`root:root` before:

```bash
sudo chown charlie:charlie /var/mnt/ai/xdg /var/mnt/ai/xdg/下载
```

Then fully quit and reopen WeChat. Existing WeChat processes keep their old
sandbox mounts until restart.

## Verify

```bash
flatpak override --user --show com.tencent.WeChat
flatpak run --command=sh com.tencent.WeChat -lc '
for d in /var/home/charlie/xwechat_files /var/mnt/ai/xdg/下载 /var/mnt/ai/xdg/文档 /var/home/charlie/Desktop; do
  if test -e "$d"; then
    if test -w "$d"; then echo "WRITE $d"; elif test -r "$d"; then echo "READONLY $d"; else echo "NOACCESS $d"; fi
  else
    echo "MISSING $d"
  fi
done'
```

Healthy result:

- `WRITE /var/home/charlie/xwechat_files`
- `WRITE /var/mnt/ai/xdg/下载`
- `WRITE` or `READONLY /var/mnt/ai/xdg/文档`
- `READONLY /var/home/charlie/Desktop`

Launch check:

```bash
setsid -f flatpak run com.tencent.WeChat >/tmp/wechat-flatpak-launch.log 2>&1
sleep 3
ps -eo pid,comm,args | rg -i 'bwrap --args .*wechat|/app/extra/wechat/wechat|WeChatAppEx'
swaymsg -t get_tree | jq -r '.. | objects | select(.app_id? or .window_properties?.class?) | [.name, .app_id, .window_properties.class, .pid, .visible] | @tsv' | rg -i 'wechat|微信|WeChat|xwechat'
```

Healthy visible window line:

```text
Weixin		wechat	<PID>	true
```

## Portal Note

If standard file picker behavior is still broken after restart, inspect:

```bash
systemctl --user status xdg-desktop-portal.service xdg-desktop-portal-wlr.service xdg-document-portal.service --no-pager --full
journalctl --user -u xdg-desktop-portal.service -u xdg-desktop-portal-wlr.service --since '30 min ago' --no-pager
```

`xdg-desktop-portal-wlr.service` should be active on Sway/wlroots. The file
permission fix above is still required even when portals are healthy.

## File Clipboard To Firefox

When copying a file from Linux WeChat and pasting into Firefox, check the
clipboard types first:

```bash
wl-paste --list-types
wl-paste --type text/uri-list
wl-paste --type x-special/gnome-copied-files
```

Healthy file clipboard includes:

- `text/uri-list`
- `x-special/gnome-copied-files`

On this host, WeChat may put file URIs under:

```text
file:///var/home/charlie/xwechat_files/...
```

but the real Flatpak storage is:

```text
/var/home/charlie/.var/app/com.tencent.WeChat/xwechat_files
```

Keep this host-side symlink present so Firefox can read WeChat-copied files:

```bash
/var/home/charlie/xwechat_files -> /var/home/charlie/.var/app/com.tencent.WeChat/xwechat_files
```

Verify a copied file URI:

```bash
python3 - <<'PY'
from urllib.parse import urlparse, unquote
import pathlib, subprocess
uri = subprocess.check_output(['wl-paste', '--type', 'text/uri-list'], text=True).strip().splitlines()[0]
path = pathlib.Path(unquote(urlparse(uri).path))
print(uri)
print(path)
print('exists', path.exists(), 'size', path.stat().st_size if path.exists() else None)
PY
```

If the file exists and Firefox still says paste is not allowed, the target web
page is rejecting file paste; use that page's upload/attachment button or drag
the readable host file path instead.

### Second Linux WeChat Clipboard

The isolated second Linux WeChat uses:

```text
HOME=/var/home/charlie/.local/share/wechat-flatpak-2/home
--wechat-files-path=/var/home/charlie/.local/share/wechat-flatpak-2/home/xwechat_files
```

Flatpak must be launched with a narrow filesystem grant for the second profile
root; otherwise WeChat can create the copied file only inside its private
mount namespace, while Firefox receives a host `file://` URI that does not
exist:

```bash
flatpak run \
  --filesystem=/var/home/charlie/.local/share/wechat-flatpak-2:create \
  --env=HOME=/var/home/charlie/.local/share/wechat-flatpak-2/home \
  --env=XDG_CONFIG_HOME=/var/home/charlie/.local/share/wechat-flatpak-2/config \
  --env=XDG_CACHE_HOME=/var/home/charlie/.local/share/wechat-flatpak-2/cache \
  --env=XDG_DATA_HOME=/var/home/charlie/.local/share/wechat-flatpak-2/data \
  com.tencent.WeChat
```

The durable launchers already include this grant:

```bash
~/.local/bin/wechat-flatpak-2
~/.local/bin/wechat-flatpak-ensure
```

If a currently copied file was produced before the fix, copy it out of the
running second-WeChat namespace before restarting that instance:

```bash
pid=<second-wechat-main-pid>
uri="$(wl-paste --type text/uri-list | sed -n '1p')"
python3 - "$pid" "$uri" <<'PY'
from pathlib import Path
from urllib.parse import urlparse, unquote
import shutil, sys
pid, uri = sys.argv[1], sys.argv[2]
host = Path(unquote(urlparse(uri).path))
ns = Path(f"/proc/{pid}/root") / host.relative_to("/")
if ns.exists() and not host.exists():
    host.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ns, host)
print(host, host.exists())
PY
```

Then restart only the second WeChat main process and let
`wechat-flatpak-ensure` recreate it. Verify the host and sandbox path have the
same device/inode:

```bash
stat -c '%d:%i %n' \
  /var/home/charlie/.local/share/wechat-flatpak-2/home/xwechat_files \
  /proc/<second-wechat-child-pid>/root/var/home/charlie/.local/share/wechat-flatpak-2/home/xwechat_files
```

Avoid `pgrep -f` for keepalive detection: it can match the shell command or
the script body. Use `ps` filtered to real `/app/extra/wechat` processes.

## Workspace And Keepalive

Desktop WeChat should run as two resident Linux instances and stay on Sway
workspace `2` (`通讯与远程`).

Instances:

- WeChat 1: default Flatpak profile, `HOME=/var/home/charlie`
- WeChat 2: isolated profile,
  `HOME=/var/home/charlie/.local/share/wechat-flatpak-2/home`

Second-instance launcher:

```bash
~/.local/bin/wechat-flatpak-2
~/.local/share/applications/wechat-flatpak-2.desktop
```

The keepalive script starts both profiles:

```bash
~/.local/bin/wechat-flatpak-ensure
```

It detects WeChat 1 by the default `~/.xwechat` / `~/xwechat_files` paths and
WeChat 2 by the isolated `wechat-flatpak-2/home` paths.

Durable placement is in:

```bash
~/.config/sway/workspace-policy.json
```

Rule:

```json
{
  "name": "WeChat",
  "workspace": "2",
  "class": "(?i)^wechat$"
}
```

This requires `~/.local/bin/sway-workspace-controller` to handle XWayland
windows where `app_id` is empty but `window_properties.class` is present.

Keepalive:

```bash
~/.local/bin/wechat-flatpak-ensure
~/.config/systemd/user/wechat-flatpak-keepalive.service
~/.config/systemd/user/wechat-flatpak-keepalive.timer
```

Verify:

```bash
systemctl --user is-active wechat-flatpak-keepalive.timer sway-workspace-controller.service
swaymsg -t get_tree | jq -r '.. | objects | select(.type? == "workspace") | .name as $ws | [.. | objects | select((.window_properties.class//"") == "wechat") | [$ws,.name,.app_id,.window_properties.class,.pid,.visible,((.marks//[])|join(","))] | @tsv] | .[]'
```

Healthy window line:

```text
2	Weixin		wechat	<PID1>	false	...
2	Weixin		wechat	<PID2>	false	...
```

Preferred Sway layout for dual WeChat:

- Workspace `2` stays outer `tabbed`, so the pair appears as one communication
  tab/page.
- The two `wechat` windows sit inside one horizontal split container at 50/50.
- Non-WeChat accidental windows, such as Nautilus file manager windows, should
  be moved out before arranging the pair.

One-shot layout repair:

```bash
swaymsg '[app_id="org.gnome.Nautilus"] move container to workspace number 4'
swaymsg 'workspace number 2'
swaymsg '[class="wechat"] floating disable'
swaymsg '[con_id=<wechat1>] resize set width 50 ppt'
swaymsg '[con_id=<wechat2>] resize set width 50 ppt'
```

Healthy representation:

```text
T[H[H[wechat wechat]]]
```

## Matrix / SchildiChat Sync Boundary

Existing durable sync components:

- `wechat-sync.timer`: runs UOS/Linux local decrypt sync via
  `wechat-msg-sync-wrapper.sh`, then Android ADB backup when reachable.
- `wechat-matrix-sync.timer`: imports decrypted Android DB snapshots to Matrix.
- `matrix-wechat.service`: live Matrix-WeChat bridge appservice.
- `wechat-matrix-restore-monitor.timer`: finalizes restore and SchildiChat
  room visibility.

Having desktop WeChat and iOS WeChat both online does not by itself add iOS
message decryption to the Matrix/SchildiChat pipeline. iOS needs a separate
data source, such as an accessible decrypted/backup WeChat database workflow,
before it can be imported. Do not claim iOS WeChat participates in decrypt sync
unless such a pipeline is explicitly added and verified.
