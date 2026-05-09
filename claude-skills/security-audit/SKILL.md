---
name: security-audit
description: "安全审计：检查NixOS配置中是否有敏感凭证泄露（grep hashedPassword/UUID/PSK）、验证SSH配置（PasswordAuthentication必须为false）、检查..."
user-invocable: false
version: "1.0.0"
category: security
tags: [security, audit, nixos, ssh, firewall, sops]
effort: medium
auto-generated: true
created: 2026-04-08
---

# Security Audit

## 场景
安全审计：检查NixOS配置中是否有敏感凭证泄露（grep hashedPassword/UUID/PSK）、验证SSH配置（PasswordAuthentication必须为false）、检查防火墙状态、审计exposed ports（ss -tlnp | grep 0.0.0.0）、验证sops-nix secrets是否正常解密、检查age key备份状态。

## 步骤
See content summary for details.

## 注意事项
Manually created — review and expand as needed.
