---
name: age-key-backup
description: "age加密密钥备份和验证：密钥位置~/.config/sops/age/keys.txt(600权限)。--verify模式：检查主密钥存在性、验证sops解密、对比主密钥与备份副本checks..."
user-invocable: false
version: "1.0.0"
category: security
tags: [security, sops, age, backup, encryption]
effort: medium
auto-generated: true
created: 2026-04-08
---

# Age Key Backup

## 场景
age加密密钥备份和验证：密钥位置~/.config/sops/age/keys.txt(600权限)。--verify模式：检查主密钥存在性、验证sops解密、对比主密钥与备份副本checksum。备份模式：复制到/mnt/ai/secrets-backup/age-keys.txt+本地.backup副本。--restore从备份恢复。每次调用MUST显示警告：age key是NixOS全部secrets的唯一解密密钥，丢失=永久不可逆数据丢失。

## 步骤
See content summary for details.

## 注意事项
Manually created — review and expand as needed.
