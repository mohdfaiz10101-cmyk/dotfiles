# Machine Backup

Generated from `fedora` at `2026-08-30T16:00:00Z`.

This repository is a portable user-space restore set, not a raw disk image.
It intentionally excludes private keys, OAuth/session files, browser profiles,
container layers, caches, games, and large generated exports.

Restore on a different machine:

```bash
git clone -b machine-backup git@github.com:mohdfaiz10101-cmyk/dotfiles.git machine-backup
cd machine-backup
./restore.sh --dry-run
./restore.sh --apply
```

After restore, review `manifest/packages.txt`, `manifest/flatpaks.txt`,
and `manifest/systemd-user-units.txt` for host-specific package/service work.
