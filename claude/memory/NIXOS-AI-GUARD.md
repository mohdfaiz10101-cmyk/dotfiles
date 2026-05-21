
# NixOS AI防护体系 - 强制记忆

## 已部署工具（2026-05-20）

### 核心工具
- **nixos-rebuild-safe** — 安全重建（dry-build+验证+AI修复）
- **nixos-ai-fix-engine** — 错误模式匹配+自动修复（95%+置信度）
- **nixos-update-checker** — 更新检测+安全补丁提醒
- **nixos-decision-engine** — AI决策引擎
- **nixos-llm-analyzer** — LLM复杂错误分析
- **nixos-gui-guardian** — GUI巡检+自动修复（systemd timer）
- **nixos-config-check** — 配置自检工具

### 关键修复
- noGUI specialisation: `boot.kernelParams = lib.mkForce []` → `lib.mkAfter ["nomodeset" "systemd.unit=multi-user.target"]`
- 文件: `/etc/nixos/configuration.nix:133`

### 使用习惯
```bash
nixos-rebuild-safe test --ai-fix      # 先测试+AI修复
nixos-rebuild-safe switch --ai-fix    # 确认后切换
nixos-config-check                    # 配置自检
sudo nixos-gui-guardian --fix         # 手动巡检
```

### 决策逻辑
- 置信度≥90% → 自动修复
- 置信度70-90% → 半自动（建议+确认）
- 置信度<70% → 记录+提示用户
- 安全补丁 → 立即创建任务
- 功能更新 → 每周汇总

## 待执行
- [ ] sudo nixos-rebuild switch（激活新配置）
- [ ] 验证 systemd timer 生效
- [ ] 验证所有工具可用
