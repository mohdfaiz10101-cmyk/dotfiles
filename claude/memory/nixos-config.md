# NixOS 配置笔记

## 基础信息
- Flake 路径: /etc/nixos/
- 重建命令: `sudo nixos-rebuild switch --flake /etc/nixos#charlie`
- **Secrets 管理**: sops-nix + age 加密
  - age key: `~/.config/sops/age/keys.txt`（**必须备份，丢失无法恢复**）
  - 加密文件: `/etc/nixos/secrets/secrets.yaml`（sops AES256_GCM，可 git 追踪）
  - 配置文件: `/etc/nixos/.sops.yaml`
  - 解密测试: `nix-shell -p sops -p age --run "SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt sops --decrypt /etc/nixos/secrets/secrets.yaml"`
  - 编辑密文: `nix-shell -p sops -p age --run "SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt sops /etc/nixos/secrets/secrets.yaml"`

## 配置变更记录

### 2026-04-15 [Opus] storage.nix — ntfs3 → ntfs-3g 驱动切换
- **修改文件**：`/etc/nixos/modules/storage.nix`、`/etc/nixos/scripts/disk-pool-mount.sh`
- `/mnt/data`：`ntfs3` → `ntfs-3g`（可拆卸 HDD，ntfs3 遇脏卷会卡死）
- `/mnt/win_c`：保持 `ntfs3` + `ro,force`（NVMe 固定盘，ntfs-3g 因 MFT 损坏拒绝挂载）
- disk-pool-mount.sh：POOL 盘优先 ntfs-3g（删除 ntfs3 fallback 链）
- win_c MFT 已用 `ntfsfix /dev/nvme0n1p4` 修复，统一切到 ntfs-3g
- 三块 NTFS 全部 ntfsfix 修复：sdb4(POOL-A1)、sda1(POOL-B1)、nvme0n1p4(win_c)
- **当前状态**：/mnt/data 临时用 ntfs3（lazy unmount 残留），重启后自动切 ntfs-3g

### 2026-04-15 [Opus] 全局 oneshot 服务 TimeoutStartSec 防卡死
- **修改文件**：`disk-pool.nix`、`auto-services.nix`、`services.nix`
- 12 个 oneshot 服务从默认 infinity → 有限 timeout
- 关键保护：disk-pool(60s)、ai-docker-delayed(900s)、fwupd-refresh(120s, mkForce)
- home-backup: requires→wants mnt-data.mount（硬盘不在不阻塞 timer 触发）
- 用户级 auto-fix-services.service 也添加 60s timeout

### 2026-04-11 [Sonnet] 平板USB代理自动切换 — NetworkManager Dispatcher
- **新模块**：`/etc/nixos/modules/tablet-proxy.nix`（配置文件 5.7KB）
- **Dispatcher 脚本**：`/etc/NetworkManager/dispatcher.d/99-tablet-proxy`（自动监控 USB 网络接口）
- **配置存储**：`/var/lib/tablet-proxy/current.sh`（可写入，动态切换）
- **Shell 集成**：`/etc/profile.d/zzz-tablet-proxy.sh` → 新 shell 自动加载
- **切换逻辑**：
  - USB 网络接口 up + 192.168.80.242:7890 可达 → 切换到平板代理
  - USB 断开 / 代理不可达 → 恢复本地代理（127.0.0.1:7890）
  - GLM 保护：`no_proxy=open.bigmodel.cn` 不受影响
- **部署时间**：2026-04-11 01:00（nixos-rebuild switch）
- **首次切换**：2026-04-11 01:00:11 自动启用平板代理
- **验证结果**：Google/Anthropic 访问正常
- **手动工具**：`proxy-switch [tablet|local|status]`（待修复）
- **日志位置**：`/var/log/tablet-proxy.log`

### 2026-04-13 [Sonnet] Docker 路径硬防护 + LiteLLM NixOS systemd 自启
- **防护方案**：方案 B（NixOS systemd 自启），包含多层防护体系
- **新增脚本**：`/etc/nixos/scripts/docker-path-verify.sh`（88 行）
  - 前置检查：删除手动 daemon.json、验证 /var/lib/docker 存在/可写/权限正确
  - 文件系统检查：拒绝 NTFS（MFT 损坏导致容器启动失败）
  - 磁盘空间检查：至少 5GB 可用
- **Docker 配置强化**：修改 `/etc/nixos/modules/virtualization.nix`
  - 添加 systemd preStart 钩子：启动前自动运行路径验证脚本
  - data-root 保持硬编码为 `/var/lib/docker`（EXT4）
- **LiteLLM 服务定义**：新增 `/etc/nixos/modules/services/litellm-docker.nix`（165 行）
  - 服务名：`services.litellm-docker`（避免与 nixpkgs 26.05 内置 litellm 冲突）
  - 配置选项：enable、composeDir、port
  - 启动顺序：docker.service → litellm-docker.service
  - 自动重试：失败 10 秒后重启，最多 5 次，5 分钟内未恢复则停止
  - 健康检查：启动后 15 秒检查 /health 端点
  - 日志输出：systemd journal（journalctl -u litellm-docker）
- **系统配置集成**：修改 `/etc/nixos/configuration.nix`
  - 导入 `./modules/services/litellm-docker.nix`
  - 添加配置示例（注释形式，用户自行启用）
- **启用步骤**：
  1. 找到 docker-compose.yml 路径：`find ~ /mnt -name docker-compose.yml 2>/dev/null`
  2. 编辑 configuration.nix，取消注释示例，修改 composeDir
  3. 验证：`nix flake check /etc/nixos`
  4. 应用：`sudo nixos-rebuild switch --flake /etc/nixos#charlie`
  5. 验证：`systemctl status litellm-docker` + `curl http://localhost:4000/health`
- **防护层次**：
  - L1: 脚本检查（启动前验证路径、FS、空间）
  - L2: NixOS 硬编码（data-root 由系统管理）
  - L3: systemd 顺序（依赖关系确保 Docker 先启动）
  - L4: 自动重试（启动失败自恢复）
  - L5: 健康检查（验证真正运行）
- **避坑**：
  - Nix flake check 报 "path does not exist" → git add 新文件后重试
  - systemd 冲突：nixpkgs 26.05 有内置 litellm（Python 版），改名为 litellm-docker 避免冲突
  - ExecStartPre vs preStart：前者数组支持多条，后者合并单个脚本，选择 preStart 更清晰
- **验证日期**：2026-04-13 待用户应用后验证

### 2026-04-11 [Sonnet] 平板USB代理验证
- **设备**：Xiaomi Pad 5（USB网络 192.168.80.242）
- **代理端口**：7890（HTTP代理）✅ 可用，7891（SOCKS）❌ 未开放，9090（控制面板）❌ 未开放
- **验证结果**：Google/Anthropic API 访问正常
- **GLM 保护**：`no_proxy=open.bigmodel.cn` 已配置，不受代理影响
- **ADB 状态**：2fd06d4e unauthorized（需在平板授权）
- **使用方式**：`export http_proxy=http://192.168.80.242:7890`

### 2026-04-09 [Sonnet] 安全加固 — PAM 进程数限制（防 fork bomb）
- **新模块** `/etc/nixos/modules/security.nix`，配置 PAM loginLimits：
  - `* hard nproc 4096` — 绝对上限
  - `* soft nproc 2048` — 默认上限（允许 ulimit 提升至 hard）
- **背景**：zsh fork bomb 事件（235 segfault/31秒，2290 进程/秒）暴露系统缺少进程数防护
- **生效方式**：重新登录后新 shell 生效（当前 session 不受影响）
- **验证**：`cat /nix/store/*-limits.conf` 查看配置，`ulimit -u` 查看限制（重登录后）
- **配置文件**：`configuration.nix` imports `modules/security.nix`

### 2026-04-08 [Sonnet] P1 重构 — configuration.nix 拆分为模块化架构
- **新模块文件**：
  - `modules/boot.nix` — 引导加载、内核、zram
  - `modules/desktop.nix` — KDE Plasma 6 桌面
  - `modules/users.nix` — 用户账户、shell、aliases、sops age key
  - `modules/virtualization.nix` — Docker + libvirt
  - `modules/audio.nix` — PipeWire 音频
  - `modules/networking.nix` — 网络、防火墙、SSH
  - `modules/services.nix` — 系统服务入口（imports services/ 子目录）
- **services/ 子目录拆分**：
  - `modules/services/ai.nix` — Ollama、LiteLLM、GLM proxy
  - `modules/services/timers.nix` — 用户定时任务
  - `modules/services/tools.nix` — 系统工具服务
  - `modules/services/web.nix` — Web 服务
- **新增**：
  - `modules/packages.nix` — 统一包管理
  - `packages/wechat-uos.nix` — 微信 UOS overlay
- **flake.nix 精简**：添加 sops-nix input，移除 openclaw/cosmic
- **sops-nix 加密凭证**：`secrets/secrets.yaml` + age key
- **rebuild 命令**（Go modules 需网络时）：`sudo env GOPROXY=https://goproxy.cn,direct nixos-rebuild switch --flake /etc/nixos#charlie --option sandbox false`

### 2026-04-06 [GLM] 浏览器配置声明式管理 — modules/browser.nix
- **新模块** `/etc/nixos/modules/browser.nix`，管理 4 项配置：
  1. Floorp 代理 user.js（activationScript 自动注入活跃 profile）
  2. cookie-sync-server（systemd user service，port 9977）
  3. 截图贴图脚本（screenshot-pin / paste-image-pinned 部署到 /etc/nixos/scripts/）
  4. KDE khotkeysrc 占位管理
- **旧文件清理**：删除 `~/.config/systemd/user/cookie-sync-server.service`，`~/.local/bin/` 下 3 个脚本改为 symlink → `/etc/nixos/scripts/`
- **坑**：`XDG_CACHE_HOME` 指向 mergerfs（FUSE），Nix 的 fetcher-cache SQLite 不支持 FUSE 文件锁。临时用 `XDG_CACHE_HOME=/home/charlie/.cache` 绕过
- **永久修复**：activationScript + 手动在 POOL-A1 创建 `/mnt/pool/offload/cache-charlie/nix` → `/home/charlie/.cache/nix` symlink，mergerfs first-found policy 优先使用 POOL-A1 的 symlink 而非 POOL-B1 损坏目录

## 2026-04-06：Docker 迁移 + LiteLLM 扩展

### Docker 配置变更
```nix
virtualisation.docker.daemon.settings = {
  data-root = "/opt/docker-data";  # 2026-04-06: NTFS3→ext4根分区; 2026-04-08: 根分区→/mnt/ai ext4; 2026-04-13: /mnt/ai镜像缺失→/opt/docker-data根分区ext4
}
```

**迁移历史**：
- 2026-04-06: NTFS3 → `/var/lib/docker`（根分区 ext4）
- 2026-04-08: `/var/lib/docker` → `/mnt/ai/docker`（释放根分区 8GB，降至 73%）
- 2026-04-13: `/mnt/ai/docker` → `/opt/docker-data`（/mnt/ai loopback 镜像不存在，rebuild 失败，改用根分区 /opt 目录）

### LiteLLM SiliconFlow 模型（更新 2026-04-07）
- **域名修复**：`api.siliconflow.com` → `api.siliconflow.cn`（.com 不认当前 Key）
- **模型名修正**：`DeepSeek-V3.2-Exp` → `DeepSeek-V3.2`，`DeepSeek-V3.1` → `DeepSeek-V3.1-Terminus`
- **DeepSeek V3 系列**：`silicon/deepseek-v3.2`、`silicon/deepseek-v3.1`
- **DeepSeek R1 全系列**（对标 Opus 推理强度）：

| 路由名 | 实际模型 | 参数 | 价格/M tokens |
|--------|---------|------|--------------|
| `r1-full` | R1 671B + Pro 加速版 | temp=0.6, top_p=0.95, max=32768 | ¥4/¥16 |
| `r1-smart` | R1-32B → R1-14B 自动降级 | temp=0.6, top_p=0.95, max=16384 | ¥1.26/¥1.26 |
| `silicon/deepseek-r1` | R1 满血 671B | 同 r1-full | ¥4/¥16 |
| `silicon/deepseek-r1-pro` | Pro/DeepSeek-R1 | 同 r1-full | ¥4/¥16 |
| `silicon/deepseek-r1-32b` | R1-Distill-Qwen-32B | max=16384 | ¥1.26/¥1.26 |
| `silicon/deepseek-r1-14b` | R1-Distill-Qwen-14B | max=8192 | ¥0.70/¥0.70 |
| `silicon/deepseek-r1-8b` | R1-0528-Qwen3-8B | max=8192 | 待确认 |
| `silicon/deepseek-r1-7b` | R1-Distill-Qwen-7B | max=4096 | **免费** |

- **Fallback 链**：
  - `r1-full` → `silicon/deepseek-r1` → `r1-32b` → `deepseek-v3.2`
  - `r1-smart` → `r1-7b` → `deepseek-v3.2` → `local/deepseek-r1-14b`
  - `glm-code` → `glm-4` → `silicon/deepseek-v3.2` → `free/mistral-codestral`
- **API Key**：`SILICONFLOW_API_KEY` 环境变量，仅 `.cn` 域名有效

### Redis 缓存配置
```yaml
litellm_settings:
  cache: true
  cache_params:
    type: redis
    host: redis  # Docker Compose service name
    port: 6379
    password: os.environ/REDIS_PASSWORD
    ttl: 3600
```

### Paperclip 共享指导
路径：`/home/charlie/.paperclip/shared-instructions/`
- CODING_GUIDELINES.md
- MEMORY.md
- NIXOS_SAFETY.md
- AGENTS.md

## 2026-04-06：Nix GC 策略优化

### 变更
```nix
nix.gc.options = "--delete-older-than 3d";  # 从 7d 缩短到 3d
```
- Generation 68（此次 switch 产生）

### 磁盘清理架构
- **nix.gc**（系统级 timer，daily）：`-d --delete-older-than 7d`（删除 >7d 的 generations + GC，2026-04-08 修复）
  - **重要**：`-d` 参数必须包含，否则只清理 derivations，不清理 system generations，导致 /nix/store 无法有效回收
- **disk-sentinel v2**（用户级 timer，每 5 分钟）：
  - 85%+ → 清理 result 残留 + 大目录迁移扫描
  - 90%+ → AppImage 缓存 + Docker prune + nix profile 清理 + tmp 清理
  - 95%+ → 全量清理 + journal 压缩
- **disk-cleanup**（用户级 timer，每周日 10:00）：定期深度清理
- [2026-04-08] [Sonnet] 所有定时任务已从凌晨改为白天（08:00-22:00），详见 timers.nix / services.nix / disk-pool.nix / auto-services.nix
- [2026-04-08] [Sonnet] Docker 镜像积累问题：/var/lib/docker 占用 20GB，定期执行 `docker system prune -a --volumes` 清理未使用镜像

### 已移除的 GC Roots
- `pinned-stable-system`（旧 Feb 17 系统）
- `stable-system`（旧 Feb 17 系统）
- 以后 pin generation 需评估是否真正需要

### 2026-04-06 (Letta Distill)
- NixOS系统维护手册，记录配置变更与维护指南。

### 2026-04-06 (Letta Distill)
- 记录NixOS系统关键分区UUID及配置信息，包括根分区和EFI分区的文件系统类型与设备路径。

### 2026-04-06 (Letta Distill)
- NixOS系统维护命令与恢复操作步骤，包含重构、清理、远程恢复及紧急回滚方法

### 2026-04-06 (Letta Distill)
- 列举NixOS系统关键配置模块及其功能，包括主配置、硬件检测、代理方案、AI服务等配置文件结构。

### 2026-04-06 (Letta Distill)
- 代理架构配置，包含mihomo设置、订阅更新及移除TUN模式以避免断网。

### 2026-04-06 (Letta Distill)
- 通过开机菜单选项强制启用NetworkManager和allowUnfree以启动恢复稳定模式

### 2026-04-06 (Letta Distill)
- 记录AI服务架构配置，包含Ollama/OpenClaw部署参数、模型安装路径、Gemini API密钥管理及secrets目录规范

### 2026-04-06 (Letta Distill)
- 存储架构配置及Docker修复、AI集群部署与插件配置问题记录

### 2026-04-06 (Letta Distill)
- NixOS系统上下文信息，涉及配置记录或架构背景。

### 2026-04-06 (Letta Distill)
- 记录NixOS系统架构配置，包含Flake结构、引导方式、桌面环境及硬件组件设置

### 2026-04-06 (Letta Distill)
- 磁盘分区布局及挂载点设置，包含根分区、EFI分区及外接硬盘配置。

### 2026-04-06 (Letta Distill)
- 本文详细描述了NixOS配置文件结构，包括flake.nix、modules目录下的各模块职责及旧配置文件说明，用于系统配置管理。

### 2026-04-06 (Letta Distill)
- NixOS配置文件引用变更，旧模块已整合或弃用，当前仅引用指定硬件和AI相关配置模块。

### 2026-04-06 (Letta Distill)
- 记录NixOS系统配置中的硬件驱动、引导设置、虚拟化工具及用户环境等模块的配置项与依赖工具

### 2026-04-06 (Letta Distill)
- NixOS中AI服务配置：Ollama作为推理后端（11434端口），OpenClaw Gateway对接本地Ollama（18789端口），默认模型qwen2.5-coder:7b，通过Nix Store JSON配置，systemd服务root运行且自动重启，防火墙开放对应端口。

### 2026-04-06 (Letta Distill)
- 记录NixOS系统GRUB防护配置、紧急回滚命令、磁盘保护设置及包管理安全策略，确保系统稳定与安全

### 2026-04-06 (Letta Distill)
- 记录NixOS系统中mihomo代理配置，包含端口设置、Web UI地址、环境变量及工具移除等网络代理相关变更

### 2026-04-06 (Letta Distill)
- 用户记录NixOS配置偏好，包括文件权限设置、Zsh多行指令封装及IDE编辑权限配置。

### 2026-04-06 (Letta Distill)
- 记录NixOS配置变更及系统存储状态，包括挂载点调整、磁盘使用情况和目录结构。

### 2026-04-06 (Letta Distill)
- 记录NixOS系统最近提交及磁盘使用情况，包含配置变更与目录结构信息

### 2026-04-06 (Letta Distill)
- 记录NixOS最近提交的配置变更及/mnt/data目录结构与磁盘使用情况。

### 2026-04-06 (Letta Distill)
- 记录NixOS系统最近提交、/mnt/data目录结构及磁盘使用情况，用于系统状态监控与存储管理。

### 2026-04-06 (Letta Distill)
- 记录NixOS最近提交、系统目录结构及磁盘使用情况

### 2026-04-06 (Letta Distill)
- 记录NixOS最近提交、/mnt/data目录结构及磁盘使用情况，展示系统状态快照

### 2026-04-06 (Letta Distill)
- 记录NixOS系统配置，包括磁盘池声明式管理、KDE托盘自动隐藏脚本、Claude自动登录脚本及APK项目模板设置。

### 2026-04-06 (Letta Distill)
- 记录NixOS系统KDE活动布局与任务栏配置，及Whisper语音输入的安装路径与使用脚本。

### 2026-04-06 (Letta Distill)
- 记录了NixOS配置、AI算力方案、Whisper语音输入及KDE窗口规则等系统设置

### 2026-04-06 (Letta Distill)
- NixOS配置包含磁盘池声明式管理、KDE托盘隐藏脚本、剪贴板同步服务、Claude自动登录脚本及APK项目模板设置。

### 2026-04-06 (Letta Distill)
- 记录NixOS系统配置变更，包括Letta保障系统、md同步脚本、HyperChat修复、disk-pool存储池声明式配置等关键服务与存储方案

### 2026-04-06 (Letta Distill)
- 记录NixOS系统配置变更，包括互联服务集成、系统监控仪表板、HyperChat功能增强及API新增，优化资源管理与用户体验。

### 2026-04-06 (Letta Distill)
- 记录NixOS配置变更，包括统一搜索系统v5.0升级、服务禁用、脚本修复及系统服务与防火墙配置

### 2026-04-06 (Letta Distill)
- 记录NixOS系统已安装服务及代理三级故障转移架构，包含 watchdog 管理、免费代理刷新策略及环境变量配置注意事项

### 2026-04-06 (Letta Distill)
- NixOS配置更新包含langchain-hub服务设置、新增生产力工具及Whisper语音输入配置

### 2026-04-06 (Letta Distill)
- 记录NixOS系统配置，包含服务启用、组件设置及首次配置步骤，如Tailscale和Sunshine的初始化配置。

### 2026-04-06 (Letta Distill)
- NixOS配置变更需严格验证，包含修改后执行nix flake check、kreadconfig6确认写入及记录变更到nixos-config.md的规范

### 2026-04-06 (Letta Distill)
- NixOS配置调整及问题解决，涉及服务配置、SSH设置、磁盘池脚本优化等

### 2026-04-06 (Letta Distill)
- 记录多设备的网络拓扑和详细配置，用于分布式管理与跨设备调度。

### 2026-04-06 (Letta Distill)
- 记录NixOS与平板、手机等设备的SSH连接配置、端口设置及任务分配方案

### 2026-04-06 (Letta Distill)
- 记录NixOS配置路径、网络设备IP、SSH连接方式及系统缓存路径等系统设置信息。

### 2026-04-06 (Letta Distill)
- 记录NixOS Flake架构配置，入口flake.nix输出端点charlie，UEFI+GRUB引导及EFI分区与Win11共享设置

### 2026-04-06 (Letta Distill)
- 记录根分区/dev/nvme0n1p9（89GB ext4，需保持<70%使用率）和数据盘/mnt/data（932GB NTFS）的磁盘配置信息

### 2026-04-06 (Letta Distill)
- 配置AI盘挂载点/mnt/ai为ext4文件系统并设置Docker数据根目录为/mnt/ai/docker

### 2026-04-06 (Letta Distill)
- Flake纯求值不支持读取/etc路径，需用builtins.toJSON内联配置modules/proxy.nix

### 2026-04-06 (Letta Distill)
- NixOS系统安全重建与清理命令：先构建验证再切换安装引导程序，使用nix-collect-garbage清理缓存

### 2026-04-06 (Letta Distill)
- NixOS脚本推荐使用#!/usr/bin/env bash而非/bin/bash以确保兼容性。

### 2026-04-06 (Letta Distill)
- 将AI Watchdog与Patrol的通知系统迁移到Telegram，更新脚本调用tg-push并配置Bot Token与Chat ID，完成测试后重启相关服务。

### 2026-04-06 (Letta Distill)
- NixOS系统中numpy安装及服务配置、ffplay管道模式使用、系统亮度控制命令等配置记录

### 2026-04-06 (Letta Distill)
- 配置memory-sync和obsidian-git同步脚本，新增搜索API并设置systemd定时任务实现自动化同步与归档

### 2026-04-06 (Letta Distill)
- 在NixOS上安装Voxtype需自定义包并配置daemon直接监听硬件按键，设置快捷键及systemd服务自动启动

### 2026-04-07 (Letta Distill)
- 记录NixOS系统GPU优化、持久化模式、AI算力配置及多设备协同方案的详细配置信息

### 2026-04-07 (Letta Distill)
- 记录NixOS系统配置变更，包括KDE托盘隐藏、Letta防护系统监控、磁盘池服务配置等系统设置。

### 2026-04-07 (Letta Distill)
- NixOS LiveCD定制配置包含ISO路径、内置Claude Code应用及USB镜像复制至Ventoy的详细设置。

### 2026-04-07 [Sonnet] Charlie Hub 新增架构流动图路由
- **新增服务路由**：`/arch` → `~/hub/static/arch.html`（3D 星球架构可视化）
- **Caddy 配置**：`/arch` handle 反向代理到 Hub API :9801
- **FastAPI 端点**：`@app.get("/arch")` 返回 arch.html
- **导航配置**：`nav-config.json` 总览组新增"架构流动图"项（badge: 3D）
- **服务重启**：charlie-hub.service + hub-caddy.service 已重启生效
- **访问地址**：`http://localhost:9800/arch` 或 Hub 左侧导航 → 总览

## [2026-04-07] AI 记忆系统集成配置

**Systemd 服务**：
- `ai-archival-sync.timer` — 每 6 小时触发 GLM↔Letta + Memory→Letta 同步
- `ai-archival-sync.service` — 调用 `~/.config/ai-shared/sync-all.sh` wrapper

**同步脚本**：
- `~/.config/ai-shared/sync-archival.py` — GLM archival ↔ Letta 双向同步
- `~/.config/ai-shared/sync-memory-to-letta.py` — Memory files → Letta 单向同步
- `~/.config/ai-shared/sync-all.sh` — 统一调度脚本

**AI CLI 脚本**：
- `/home/charlie/.local/bin/glm` — 启动时加载 4 个 memory 文件（tail -100）
- `/home/charlie/.local/bin/aider-with-memory` — Aider wrapper，自动 --read memory 文件

**AGI Brain**：
- `~/agi/think.py` — _load_memory_context() 模块级加载，注入 SYSTEM_PROMPT

**Hub API**：
- `~/hub/hub-api.py` — load_memory_summary() + /api/chat endpoint 新对话注入

**Letta 配置**：
- URL: `http://localhost:8283`
- Agent: `agent-02380eae-9ac2-45f4-b9b2-dabf40e0abea` (code-assistant)
- Auth: `Authorization: Bearer letta`

**Memory 文件路径**：
- `~/.claude/projects/-home-charlie/memory/`
  - MEMORY.md, lessons-learned.md, nixos-config.md, ideas-roadmap.md, codebase-map.md, troubleshooting.md

### 2026-04-08 (Letta Distill)
- 记录NixOS LiveCD定制配置、同步系统设置、Anything.One APK项目信息及KDE Plasma版本配置详情

- [2026-04-08] [Sonnet] NixOS 安全加固：
  1. SSH: PasswordAuthentication=false, PubkeyAuthentication=true
  2. 防火墙: networking.firewall.enable=true, 仅保留 22 端口对外
  3. swappiness: vm.swappiness=10（配合 zramSwap 50%）
  4. 代理加固: Mihomo Web UI 127.0.0.1:9091, networking.proxy 改为 127.0.0.1
  5. 移除 ai.nix 和 proxy.nix 中不必要的端口暴露，服务走 Tailscale trustedInterface
  6. Xray inbound 保持 0.0.0.0（LAN 设备需要局域网代理）
  7. nix flake check 通过

## 2026-04-09 Docker 防火墙修复
- **问题**：NixOS 防火墙（`nixos-fw` 链）默认拒绝 Docker bridge → host 的所有非白名单端口，导致 Letta/LiteLLM 容器无法访问 host Ollama (11434)
- **修复**：`/home/charlie/launcher/docker-iptables-allow.sh` 动态添加 iptables 规则，放通所有 Docker 网段到 11434
- **持久化**：systemd user service `docker-iptables-allow.service`（登录时执行）+ sudoers 免密规则 `/etc/sudoers.d/docker-iptables`
- **长期方案**：应在 `modules/networking.nix` 的 `networking.firewall.extraCommands` 中配置，避免依赖外部脚本

## 2026-04-08 安全加固变更
- SSH: PasswordAuthentication false（原 true）
- 防火墙: networking.firewall.enable = true，放行 SSH(22)
- swappiness: 10（原默认 60）
- 代理: Mihomo Web UI 9091 绑定 0.0.0.0（Claude 路由规则走 🇺🇸 美国 节点组）
- 凭证: hashedPassword/VLESS UUID/WiFi PSK 迁移到 /etc/nixos/secrets.nix（.gitignore 排除）
- 新增 timers: docker-prune(周)、disk-space-monitor(日)、backup-cleanup(月)
- 废弃文件清理: 删除 10 个 .bak/.error + hardware-cofiguration.nix(typo)
- ⚠️ 需要 nixos-rebuild switch 生效
- [OK] rebuild switch 已于 2026-04-08 执行，generation 已激活

### 2026-04-08 [Sonnet] user-services.nix 按功能域拆分
- **原始文件**: `/etc/nixos/modules/user-services.nix` (785 行单文件)
- **拆分为 4 个独立 NixOS module**:
  1. `modules/services/ai.nix` (207 行) — 13 个 AI 持久守护服务
  2. `modules/services/web.nix` (78 行) — 4 个 Web/终端持久服务
  3. `modules/services/tools.nix` (86 行) — 5 个工具类服务
  4. `modules/services/timers.nix` (457 行) — 21 个 oneshot + 21 个 timer
- **聚合入口**: `modules/user-services.nix` (20 行，只做 imports)
- **纯重构**: 33 个 service + 21 个 timer 数量和配置完全不变
- **`config.charlie.sharedPythonEnv` 引用**: ai.nix / web.nix / timers.nix 各自 let 块中独立引用
- **configuration.nix 无需修改**: `./modules/user-services.nix` import 路径不变

## [2026-04-08] [Sonnet] configuration.nix 模块拆分

- **前**: configuration.nix 612 行，所有配置混合在一起
- **后**: configuration.nix 84 行，只保留 imports + hardware + packages + i18n + nix settings
- **新增模块**:
  - `modules/boot.nix` (46 行) — GRUB, zram, swappiness, win_efi mount
  - `modules/desktop.nix` (76 行) — NVIDIA, KDE Plasma, SDDM, Sunshine, cursor, electron fixes, udev, fcitx5 session vars, XDG cache
  - `modules/users.nix` (97 行) — 用户定义, sudo, zsh, direnv, tmux, nix-ld, secrets 引用
  - `modules/virtualization.nix` (29 行) — Docker, libvirtd, Waydroid, Flatpak
  - `modules/audio.nix` (10 行) — snd-hda-intel, ydotool
  - `modules/networking.nix` (34 行) — hostname, NM, hosts, firewall, SSH
  - `modules/services.nix` (143 行) — F3 recovery, freeze-detector, home-backup, health-monitor, test-notify, claude-to-obsidian, floorp-bookmark-backup
- **额外修复**: proxy.nix 需要自己的 secrets let 块（原来依赖 configuration.nix 的 let）
- **flake check**: 通过（需要 secrets.yaml 临时 readable）

## 2026-04-08 P1 架构重构
- configuration.nix: 612→84 行，拆分为 7 个模块（boot/desktop/users/virtualization/audio/networking/services）
- user-services.nix: 728 行→services/ 子目录 4 文件（ai/web/tools/timers）
- 新增 modules/packages.nix: 统一 ~90 个包声明（消除 6 处重复）
- 新增 packages/wechat-uos.nix: 微信 FHS overlay 独立文件
- flake.nix: 140→41 行，添加 sops-nix，移除 openclaw/cosmic
- sops-nix: age 加密 secrets.yaml，凭证不再明文存储
- 删除废弃文件: packages.nix / proxy.nix / user/charlie.nix / openclaw-config-fix
- 当前模块总数: 20+ 个独立模块

### 2026-04-08 (Letta Distill)
- 记录NixOS系统配置变更，包括KDE托盘隐藏、Letta防护系统、磁盘池服务等自动化脚本与服务设置。

### 2026-04-08 (Letta Distill)
- 记录NixOS LiveCD定制配置，包含ISO路径、内置Claude Code启动项、Ventoy USB镜像及KDE Plasma 6.6.0显卡设置。

### 2026-04-09
- [Sonnet] mihomo external-controller 端口从 0.0.0.0:9090 改为 127.0.0.1:9091（避免 Cockpit 冲突），修改位置：/etc/mihomo/config.yaml L16 + /etc/nixos/modules/proxy.nix L144/L155/L9 注释。Xray sops-nix secrets 需 nixos-rebuild switch 才能激活到 /run/secrets/

### 2026-04-09 (Letta Distill)
- 记录NixOS配置变更及AI工具部署，包含模型运行、语音输入、窗口管理规则，优化算力使用与系统自动化。

### 2026-04-09 (Letta Distill)
- 记录NixOS磁盘池配置、Letta防护系统、KDE托盘隐藏等系统配置方案，包含服务设置、脚本路径及自动化监控策略。

### 2026-04-09 [Sonnet] 代理系统全面修复 + 五重防护
- **mihomo config.yaml IPv6 引号修复**：7 个 IPv6 节点（L71/73/83/86/87/93/94）双引号嵌套 → 去引号；21 个 proxy-group 截断引用 → 恢复完整节点名；external-controller 0.0.0.0:9091 → 127.0.0.1:9091
- **FlClashCore 端口冲突**：FlClashCore 占用 7890 导致 mihomo 无法启动，kill 后 mihomo 恢复。FlClash 是桌面 GUI 应用会自动重启，需注意不要同时运行
- **sops-nix secrets 手动激活**：nixos-rebuild switch 后 /run/secrets/ 仍为空（sops-install-secrets 未正确解密），手动通过 `SOPS_AGE_KEY_FILE sops --decrypt` 创建
- **Xray 恢复**：secrets 就位后 xray 正常启动，HTTP 200/SOCKS5 200
- **GLM 代理绕行**：glm 脚本已有 no_proxy=open.bigmodel.cn 保护
- **新工具**：`~/.local/bin/mihomo-config-validate` — 配置预验证（YAML 语法 + 截断引用检测 + 节点引用校验）
- **架构**：xray（Tier1 VPS）和 mihomo（Tier2 免费节点）互斥（conflicts），同一时刻只有一个在 7890 端口

### 2026-04-09 [Sonnet] mihomo-guardian 增强 — 通知 + watch + 缩短间隔
- **脚本增强**（`~/.local/bin/mihomo-guardian`）：
  - 回滚成功 → `notify-send -u critical` 桌面通知
  - 回滚失败 → `notify-send -u critical` 警告通知
  - 节点切换成功 → `notify-send -u normal` 通知
  - 新增 `--watch` 模式：inotifywait 监控 config.yaml 变更，变化后 3s 延迟执行 do_check
- **timer 缩短**（`modules/services/timers.nix`）：
  - mihomo-guardian: OnBootSec 3min→2min, OnUnitActiveSec 10min→3min
- **新 systemd service**：`mihomo-watch.service`（user unit）
  - Type=simple, ExecStart=mihomo-guardian --watch
  - wantedBy=default.target（登录自启）
  - path 包含 inotify-tools
  - environment=graphicalEnv（notify-send 需要 DBUS）
- mihomo-guardian service 也增加了 environment=graphicalEnv（通知所需）

### 2026-04-10 [Sonnet] 系统架构审计修复
- **flake update**：nixpkgs 2026-02-18→2026-04-05，sops-nix→2026-04-08，zen-browser→2026-04-09
- **fail2ban**：`modules/security.nix` 新增 SSH 暴力破解防护（maxretry=5, bantime=1h，使用 NixOS 内置 sshd jail）
- **CLAUDE.md 修复**：R1 UTF-8 编码修复、R2 格式冲突统一、R3 模板计数措辞统一、R4 删除内联 lesson 残留
- **Router CLAUDE.md**：`╔═╗` 框线格式 → `▸` 单行格式，与主 CLAUDE.md R8 装饰预算一致
- **settings.json**：添加 `mcpServers.letta`（SSE transport, localhost:8788）
- **Docker 清理**：释放 2.09GB 未使用镜像
- **rebuild generation**：system-89 → system-90（pending）
- [2026-04-12] [RooCode-019d7fa4] 找到问题：ScrollLock键被KDE热键系统占用（配置在[`khotkeysrc`](../.config/khotkeysrc:55)），导致语音输入无法正常接收按键事件。

**解决方案：**

1. 禁用ScrollLock热键绑定
2. 或修改为其他按键

选择处理方式：
- [2026-04-12] [RooCode-019d7b4e] MCP 配置完成。关于自动审批 — Roo Code 的 `allowedCommands` 只覆盖特定命令，完整自动审批需要在 Roo Code UI 中设置（点击 ⚙️ → Auto-approve）。

现在更新 Custom Instructions，移植 CLAUDE.md 核心规则：
- [2026-04-12] [RooCode-019d7b4e] 关于 "Roo 输出结果自动打开文档" — 这是 Roo Code 的默认行为，修改文件时会自动在编辑器中打开。如果没生效，可能需要在 Roo Code 设置中确认 `Auto-open output files` 选项。

现在同步更新 `~/roo-code-settings.json` 和模板文件：
- [2026-04-12] [RooCode-019d7b4e] 关于审批问题 — `allowedCommands` 只控制**哪些命令被允许**，不控制**是否需要审批**。完整的自动审批需要在 **Roo Code UI** 中设置：

**操作路径**: Roo Code 侧边栏 → 点击 ⚙️ 设置图标 → 开启以下选项：
- ✅ Auto-approve Read Operations
- ✅ Auto-approve Write Operation
- [2026-04-12] [RooCode-019d7b4e] 找到根因了！`~/roo-code-settings.json` 内容是旧的 — 没有 MCP、没有更新的 Custom Instructions。而且 `roo-cline.autoImportSettingsPath` 是 **Cline** 的设置，Roo Code Nightly 可能不读取它。

让我修复：
- [2026-04-12] [RooCode-019d7b4e] 现在检查 Roo Code Nightly 是否有自己的 auto-import 设置：
- [2026-04-12] [RooCode-019d7b4e] `roo-cline.autoImportSettingsPath` 可能不被 Roo Code Nightly 读取。添加 Nightly 版本的自动导入设置：
- [2026-04-12] [RooCode-019d7b4e] 同步更新 Roo Code 全局 MCP 设置：
- [2026-04-12] [RooCode-019d7b4e] 找到了！Token 在 `~/.config/discord-bot/env`。现有的 Discord Bot 正在崩溃重启。让我检查现有 Bot 代码，直接把 `!roo` 命令加进去：
- [2026-04-12] [RooCode-019d7b4e] Roo Code 的任务恢复是**免费功能**，不需要会员。使用方法：

**在 Roo Code 侧边栏：**
1. 点击顶部的 **📅 历史按钮**（时钟图标）
2. 显示所有历史任务列表
3. 点击任意任务 → **继续对话**

**从任意设备继续：**
Roo Code 的任务数据存储在本地：
```
~/.config/Code/User/globalStorage/rooveteri
- [2026-04-12] [RooCode-019d7b4e] Gemini 配置在 LiteLLM 的 `config.yaml` 中。需要给 Gemini 模型添加 US 代理。让我添加：
- [2026-04-12] [RooCode-019d7b4e] NixOS 配置已正确设置 `data-root = "/mnt/ai/docker"`（ext4），但系统未重建，实际运行的 daemon.json 还是旧的 NTFS 路径。需要重建 NixOS：
- [2026-04-12] [RooCode-019d7b4e] Rebuild 正在执行 `switch-to-configuration` 阶段。同时查看 LiteLLM docker-compose 配置：
- [2026-04-12] [RooCode-019d7b4e] 找到配置丢失的根因了！`~/roo-code-settings.json` 的格式不对。Roo Code 的 `autoImportSettingsPath` 期望的是 `providerProfiles.apiConfigs` 结构，而不是 `apiConfiguration`。让我修复：
- [2026-04-12] [RooCode-019d7b4e] 现在完全理解了 Roo Code 的导入格式。`~/roo-code-settings.json` 需要用 `providerProfiles.apiConfigs` 结构。重写配置文件：
- [2026-04-12] [RooCode-019d7b4e] 找到错误了！日志显示 `[providerProfiles.currentApiConfigName]: Required`。`providerProfiles` 还需要一个 `currentApiConfigName` 字段。让我检查完整 schema：
- [2026-04-12] [RooCode-019d7b4e] 找到两个问题：
1. `currentApiConfigName` 必须在 `providerProfiles` 内（不是 `globalSettings`）
2. 每个 config 需要 `apiProvider: "openai"` 字段

修复配置文件：
- [2026-04-13] [RooCode-019d8424] 根本原因确认：
- 宿主机代理 `127.0.0.1:7890` [OK] 可访问 z.ai API
- 容器内 `host.docker.internal` 无法解析，无代理环境变量
- Docker daemon 的 proxy 设置**不会**传递给容器

需要测试容器是否能直连 z.ai（不需要代理）：
- [2026-04-13] [RooCode-019d82e1] 根据搜索结果，发现 `~/roo-code-settings.json` 配置文件存在，但 VSCode 配置中缺少 `autoImportSettingsPath` 设置，导致 Roo Code 启动时无法自动导入配置。

需要在 VSCode 用户配置中添加自动导入路径：
- [2026-04-14] [RooCode-019d8424] 根本原因确认：
- 宿主机代理 `127.0.0.1:7890` [OK] 可访问 z.ai API
- 容器内 `host.docker.internal` 无法解析，无代理环境变量
- Docker daemon 的 proxy 设置**不会**传递给容器

需要测试容器是否能直连 z.ai（不需要代理）：
- [2026-04-14] [RooCode-019d82e1] 根据搜索结果，发现 `~/roo-code-settings.json` 配置文件存在，但 VSCode 配置中缺少 `autoImportSettingsPath` 设置，导致 Roo Code 启动时无法自动导入配置。

需要在 VSCode 用户配置中添加自动导入路径：
- [2026-04-14] [RooCode-019d8c37] 当前 DPI 配置分析：

| 配置项 | 当前值 | 实际 DPI |
|--------|--------|----------|
| [`Gdk/UnscaledDPI`](home/charlie/.config/xsettingsd/xsettingsd.conf:1) | 98304 | 96 DPI |
| [`gtk-xft-dpi`](home/charlie/.config/g
- [2026-04-14] [RooCode-019d8c37] 用户反馈还要求增大 KDE 缩放到 1.25x。更新 [`kwinoutputconfig.json`](home/charlie/.config/kwinoutputconfig.json:35)：
- [2026-04-14] [RooCode-019d8826] 先读取 VSCode 设置和系统审计剩余部分：
- [2026-04-14] [RooCode-019d8826] 检查全局 VSCode 设置和 Roo Code 状态：
- [2026-04-14] [RooCode-019d87e9] 分析完成。以下是完整的架构诊断和解决方案。

---

## 问题诊断

### 数据存储架构

Roo Code 的配置分散在 **4 个不同位置**，这是问题的根源：

| 存储位置 | 内容 | 状态 |
|---------|------|------|
| [`state.vscdb`](/home/charlie/.config/Code/User/globalStorage/stat
- [2026-04-14] [RooCode-019d876e] 找到了！[`opencode.json`](/home/charlie/.config/opencode/opencode.json) 中的模型 ID 和 LiteLLM 不匹配：

| OpenCode 配置的模型 | LiteLLM 实际有 | 状态 |
|---|---|---|
| `deepseek-v3.2` | `deepseek-v3.2` | ✅ 刚添加 |
| `qwen2-7
- [2026-04-14] [RooCode-019d876e] 找到问题了！Roo Code 的 VS Code 状态数据库中：

- `currentApiConfigName`: `"default"`（应该是 `"litellm-local"`）
- `apiProvider`: `"zai"`（应该是 `"litellm"`）
- `apiModelId`: `"glm-5"`（应该是 `"deepseek-v3.2"`）

`roo-code-set
- [2026-04-14] [RooCode-019d87a2] `nix flake check` 退出码为 0，输出中只有镜像下载的网络警告（SSL/连接问题），**配置本身无错误**。关键行 `checking NixOS configuration 'nixosConfigurations.minipc'...` 已通过验证。
- [2026-04-15] [RooCode-019d8c37] 当前 DPI 配置分析：

| 配置项 | 当前值 | 实际 DPI |
|--------|--------|----------|
| [`Gdk/UnscaledDPI`](home/charlie/.config/xsettingsd/xsettingsd.conf:1) | 98304 | 96 DPI |
| [`gtk-xft-dpi`](home/charlie/.config/g
- [2026-04-15] [RooCode-019d8c37] 用户反馈还要求增大 KDE 缩放到 1.25x。更新 [`kwinoutputconfig.json`](home/charlie/.config/kwinoutputconfig.json:35)：

### 2026-04-15 [Opus] 终端工具扩展 — Ghostty + WezTerm
- **packages.nix 终端区块新增**：`ghostty` (1.3.1) + `wezterm` (0-unstable-2026-03-31)
- 原有终端：warp-terminal、kitty、zellij
- Ghostty 使用 GTK4/libadwaita 渲染，NVIDIA Wayland 下正常工作
- 用途：OpenCode 等 AI CLI 工具推荐使用现代终端（Ghostty/WezTerm 比 Konsole 协议支持更好）
- Ghostty NVIDIA 修复：`GSK_RENDERER=ngl`，desktop 文件在 `~/.local/share/applications/com.mitchellh.ghostty.desktop`

### 2026-04-15 [Opus] SDDM 自动重登录 + 根分区清理
- **SDDM Relogin=true**：desktop.nix 新增，防止 KDE 崩溃后卡登录界面
- **根分区清理**：91% → 84%，释放 6G。脚本 `~/launcher/disk-expand-phase1-cleanup.sh`
- **LiveCD v2**：`~/nixos-livecd/iso.nix`，XFCE + GParted + Claude Code + 自动扩容脚本
- **GParted 扩容方案**：
  - 方案 A：删 p7(8.9G WinRE) → 根分区 +8.9G（推荐，1 分钟）
  - 方案 B：删 p7+p1(21.8G) → 根分区 +30G（需移动分区，30 分钟）
- **Ventoy USB**：sde (7.2G)，ISO 名 `nixos-charlie-toolkit.iso`

### 2026-04-15 [Opus] Dolphin 存储设备免认证
- **storage.nix 新增**：polkit 规则允许 `users` 组无密码挂载/卸载/弹出/解锁设备
- 覆盖操作：`filesystem-mount` / `filesystem-mount-system` / `mount-other-seat` / `unmount-others` / `encrypted-unlock` / `eject-media` / `power-off-drive`
- 效果：Dolphin 侧边栏点击存储设备不再弹密码框
