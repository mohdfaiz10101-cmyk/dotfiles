# Runbook: Syncthing

文件同步服务。

## Desired State

- `syncthing.service` — Web UI `127.0.0.1:8384`，同步端口 `:22000`（TCP）
- 配置: `~/.config/syncthing/`
- 自动发现局域网设备

## Verify

```bash
systemctl --user is-active syncthing
curl -s --noproxy '*' http://127.0.0.1:8384/rest/system/status | jq '.connections'
```

## Restart

```bash
systemctl --user restart syncthing
```

## Notes

- Web UI 默认仅 `127.0.0.1`，远程访问需走 Tailscale SSH 隧道
- 同步大文件时可能触发 btrfs 磁盘告警，检查 `/var/mnt/ai` 空间
