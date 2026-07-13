# Runbook: Machine GitHub Backup

Portable user-space machine backup for restoring onto different hardware.

## Entry Points

- Script: `~/.local/bin/machine-github-backup`
- Restore helper: `~/.local/bin/machine-github-restore`
- Local worktree: `~/.local/share/machine-github-backup`
- GitHub target: `git@github.com:mohdfaiz10101-cmyk/dotfiles.git`, branch `machine-backup`
- Codex WebTTY button: right-side `备份` button on the stable Codex dock; API `POST /machine-backup`

## Restore

```bash
git clone -b machine-backup git@github.com:mohdfaiz10101-cmyk/dotfiles.git machine-backup
cd machine-backup
./restore.sh --dry-run
./restore.sh --apply
```

Then review `manifest/packages.txt`, `manifest/flatpaks.txt`,
`manifest/systemd-user-units.txt`, `manifest/git-remotes.txt`, and
`manifest/local-bin.txt`.

## Safety Rules

- This is not a raw disk image. It backs up portable user config, selected repos,
  systemd user units, and manifests.
- Do not commit secrets. The backup intentionally excludes private keys, browser
  profiles, Codex auth/session/cache/logs, `~/ai`, `~/memory`, and executable
  script contents under `~/.local/bin`; only `manifest/local-bin.txt` records
  local command names.
- After any backup script change, scan the local worktree before trusting the
  branch:

```bash
find ~/.local/share/machine-github-backup -type f -size +50M -printf '%p %s\n'
rg -n --hidden -S '(BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY|ghp_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,}|csk-[A-Za-z0-9]{20,})' \
  ~/.local/share/machine-github-backup -g '!/.git/**' -g '!manifest/**'
```

## Known Failure Modes

- GitHub rejects files over 100 MB. Do not put raw binaries from `~/.local/bin`
  into the branch.
- `rsync --exclude` does not delete excluded files already present at the
  destination. Clear the destination subdirectory or rebuild the backup worktree
  before force-pushing a cleaned snapshot.
- If a dirty snapshot with secrets is pushed, immediately rebuild a clean
  worktree and `git push --force` the `machine-backup` branch, then rotate the
  exposed credentials.
