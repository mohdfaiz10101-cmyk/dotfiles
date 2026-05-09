# LiteLLM 启动诊断报告

**生成时间**：2026-04-13 02:30
**状态**：已诊断 + 已部分修复，Docker 已启动，LiteLLM 待配置

---

## 执行摘要

| 项目 | 状态 | 详情 |
|------|------|------|
| **根本原因** | ✅ 已确认 | Docker data-root 指向 NTFS 分区，ntfs3 驱动无法创建 POSIX 目录 |
| **Docker 启动** | ✅ 已修复 | 修改 NixOS 配置，指向 EXT4 分区 `/var/lib/docker`，Docker 已正常启动 |
| **LiteLLM 容器** | ⏳ 待启动 | Docker 就绪，但 LiteLLM 容器未自动部署，需手动启动 |
| **关键文件** | ✅ 已创建 | `/home/charlie/.local/bin/litellm-startup.sh` 启动脚本 |

---

## 修复步骤回顾（已完成）

### 问题诊断

```
症状: LiteLLM 每次开机都不启动
    ↓
根因链:
  1. Docker 启动失败（ExitCode=1）
  2. Docker data-root = /mnt/pool-disks/POOL-B1/docker（NTFS 分区）
  3. ntfs3 驱动无法创建 /tmp 目录（POSIX 权限冲突）
  4. Docker 无法初始化，systemd 重试 3 次后放弃
  5. 没有 LiteLLM 启动脚本或 systemd 单元定义
```

### 执行的修复

| # | 动作 | 文件/命令 | 结果 |
|---|------|---------|------|
| 1 | 清理损坏的 NTFS 目录 | `sudo rm -rf /mnt/pool-disks/.../tmp` | [OK] |
| 2 | 删除手动 daemon.json | `sudo rm /etc/docker/daemon.json` | [OK] |
| 3 | 修改 NixOS 配置 | `/etc/nixos/modules/virtualization.nix` | [OK] |
| 4 | 重建系统 | `nixos-rebuild switch --flake /etc/nixos#charlie` | [OK] |
| 5 | 重启 Docker | `systemctl start docker.service` | [OK] ✓ |
| 6 | 创建启动脚本 | `/home/charlie/.local/bin/litellm-startup.sh` | [OK] |

### Docker 验证

```bash
$ docker ps
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
(空 — 无 LiteLLM 容器)

$ systemctl status docker
● docker.service - Docker Application Container Engine
    Loaded: loaded (/etc/systemd/system/docker.service; enabled; preset: ignored)
    Active: active (running)
    ✓ Docker 已正常运行
```

---

## 后续步骤（用户操作）

### 第 1 步：找到 LiteLLM docker-compose.yml

查找以下位置之一：

```bash
# 可能位置列表
find / -name "docker-compose.yml" 2>/dev/null | grep -i litellm

# 常见位置：
/mnt/ai/litellm/
/mnt/ai-cluster/litellm/
/home/charlie/docker/litellm/
$HOME/.docker/litellm/
```

### 第 2 步：编辑启动脚本，指向正确位置

```bash
# 编辑脚本，修改第 8 行
nano /home/charlie/.local/bin/litellm-startup.sh

# 将
COMPOSE_DIR="/mnt/ai/litellm"

# 改为实际路径，例如：
COMPOSE_DIR="/mnt/ai-cluster/litellm"
```

### 第 3 步：启动 LiteLLM

```bash
# 启动
/home/charlie/.local/bin/litellm-startup.sh start

# 检查状态
/home/charlie/.local/bin/litellm-startup.sh status

# 验证（应返回模型数量）
curl -s http://localhost:4000/v1/models \
  -H "Authorization: Bearer sk-litellm-charlie-2026" \
  | jq '.data | length'
```

---

## 长期解决方案（可选）

### 方案 A：创建 systemd 用户服务（推荐 — 自动启动）

创建 `~/.config/systemd/user/litellm.service`：

```ini
[Unit]
Description = LiteLLM API Gateway
After = docker.service network-online.target
Requires = docker.service

[Service]
Type = simple
Restart = always
RestartSec = 10
WorkingDirectory = /mnt/ai-cluster/litellm  # 改为实际路径

ExecStartPre = /usr/bin/docker pull litellm/litellm:latest
ExecStart = /usr/bin/docker-compose -f docker-compose.yml up

ExecStop = /usr/bin/docker-compose -f docker-compose.yml down

TimeoutStartSec = 300
StandardOutput = journal
StandardError = journal

[Install]
WantedBy = default.target
```

启用：
```bash
systemctl --user daemon-reload
systemctl --user enable litellm.service
systemctl --user start litellm.service
systemctl --user status litellm.service
```

### 方案 B：在 NixOS ai.nix 中添加服务定义

修改 `/etc/nixos/modules/services/ai.nix`，添加：

```nix
litellm-service = {
  description = "LiteLLM API Gateway (Docker)";
  after = [ "docker.service" "network-online.target" ];
  wantedBy = [ "default.target" ];
  serviceConfig = {
    Type = "simple";
    WorkingDirectory = "/mnt/ai-cluster/litellm";
    ExecStart = "${pkgs.docker-compose}/bin/docker-compose up";
    ExecStop = "${pkgs.docker-compose}/bin/docker-compose down";
    Restart = "on-failure";
    RestartSec = 10;
  };
};
```

然后 `nixos-rebuild switch`。

---

## 关键文件位置总结

| 文件 | 路径 | 用途 |
|------|------|------|
| **NixOS Docker 配置** | `/etc/nixos/modules/virtualization.nix` | Docker data-root 定义（已修复） |
| **NixOS AI 服务** | `/etc/nixos/modules/services/ai.nix` | 其他 AI 服务定义（需补充 litellm） |
| **启动脚本** | `/home/charlie/.local/bin/litellm-startup.sh` | 手动启动 LiteLLM（已创建） |
| **LiteLLM 配置** | `{COMPOSE_DIR}/docker-compose.yml` | 容器定义（待定位） |
| **诊断报告** | `~/.claude/projects/-home-charlie/memory/litellm-startup-diagnosis.md` | 本文件 |

---

## 故障排查检查表

如果 LiteLLM 仍未启动，按顺序检查：

- [ ] Docker 运行：`docker ps` 能看到容器？
- [ ] 端口监听：`curl http://localhost:4000/health` 有响应？
- [ ] 容器日志：`docker logs litellm-litellm-1`，是否有错误？
- [ ] Redis 依赖：`docker ps | grep redis`，Redis 是否运行？
- [ ] 磁盘空间：`df -h /var/lib/docker`，是否有空间？
- [ ] 网络配置：检查 docker-compose.yml 中的端口映射是否正确？

---

## 相关配置文件内容

### /etc/nixos/modules/virtualization.nix（已修复）

```nix
virtualisation.docker = {
  enable = true;
  daemon.settings = {
    data-root = "/var/lib/docker";  # ✓ EXT4 分区
    storage-driver = "overlay2";
    registry-mirrors = [
      "https://docker.1ms.run"
      "https://docker.xuanyuan.me"
    ];
  };
};
```

### 历史配置问题（已解决）

之前 Nix 生成的 daemon.json 包含：
```json
{
  "data-root": "/mnt/pool-disks/POOL-B1/docker",  // ❌ NTFS，导致失败
  "proxies": { ... }
}
```

现在已指向正确路径。

---

## 记忆标签

`#docker #litellm #ntfs #启动失败 #systemd #nixos #已修复`

修复日期：2026-04-13
修复者：[Sonnet]
验证者：[待用户确认]

---

## 方案 B 实现记录（防护体系 + NixOS systemd 自启）

**实施日期**：2026-04-13 02:30
**实施者**：[Sonnet]
**方案类型**：NixOS 系统级服务 + Docker 路径硬防护

### 实施内容

#### 1. Docker 路径验证脚本
- **文件**：`/etc/nixos/scripts/docker-path-verify.sh`
- **功能**：
  - 删除手动 `/etc/docker/daemon.json`（避免与 NixOS 配置冲突）
  - 验证 `/var/lib/docker` 存在且可写
  - 检查文件系统类型（必须是 ext4/btrfs/xfs，拒绝 NTFS）
  - 检查磁盘空间（最少 5GB）
- **集成方式**：作为 Docker systemd 服务的 `preStart` 脚本，启动前执行

#### 2. Docker 配置强化
- **文件**：`/etc/nixos/modules/virtualization.nix`
- **修改**：
  - 添加 systemd preStart 钩子，调用路径验证脚本
  - 已有的 `data-root = "/var/lib/docker"` 硬编码（EXT4）保持不变
- **效果**：Docker 每次启动都会验证路径，避免误配置

#### 3. LiteLLM NixOS 服务定义
- **文件**：`/etc/nixos/modules/services/litellm-docker.nix`
- **服务名**：`litellm-docker`（避免与 nixpkgs 内置 `litellm` 冲突）
- **关键特性**：
  - 启动顺序：`docker.service` → `litellm-docker.service`
  - 前置检查：验证 docker-compose.yml 存在
  - 自动重试：失败时 10 秒后重启（最多 5 次）
  - 健康检查：启动后检查 `/health` 端点（15 秒延迟）
  - 日志输出：systemd journal（`journalctl -u litellm-docker`）
  - 开机自启：`WantedBy = [ "multi-user.target" ]`

#### 4. 系统配置集成
- **文件**：`/etc/nixos/configuration.nix`
- **修改**：
  - 导入 `./modules/services/litellm-docker.nix`
  - 添加配置示例（注释形式，用户自行启用）

### 使用步骤

#### 第 1 步：查找 LiteLLM docker-compose
```bash
# 搜索 docker-compose.yml
find ~ /mnt -name "docker-compose.yml" -type f 2>/dev/null | head -10
```

#### 第 2 步：启用 LiteLLM 服务
编辑 `/etc/nixos/configuration.nix`，取消注释并修改路径：
```nix
services.litellm-docker = {
  enable = true;
  composeDir = "/实际/路径/到/litellm";  # 改为第 1 步找到的目录
  port = 4000;
};
```

#### 第 3 步：应用配置
```bash
# 验证语法
nix flake check /etc/nixos

# 构建并应用
sudo nixos-rebuild switch --flake /etc/nixos#charlie
```

#### 第 4 步：验证
```bash
# 检查 Docker
systemctl status docker
docker ps | grep litellm

# 检查 LiteLLM 服务
systemctl status litellm-docker

# 检查服务日志
journalctl -u litellm-docker -n 50 -f

# 健康检查
curl -s http://localhost:4000/health | jq
```

### 防护机制总结

| 防护层 | 机制 | 触发时机 | 作用 |
|------|------|---------|------|
| L1 | 路径验证脚本 | Docker 启动前 | 检查 /var/lib/docker 有效性，拒绝 NTFS |
| L2 | NixOS 硬编码 | 系统配置 | data-root 由 NixOS 管理，手动改动无效 |
| L3 | systemd 顺序 | 系统启动 | LiteLLM 启动前确保 Docker 就绪 |
| L4 | 自动重试 | 服务失败 | 启动失败自动重试，最多 5 次 |
| L5 | 健康检查 | 启动后 | 验证服务真正运行，非仅进程存在 |

### 故障自愈能力

**场景 1**：有人手动创建 `/etc/docker/daemon.json`
→ 路径验证脚本删除它 → Docker 用 NixOS 配置启动 ✓

**场景 2**：`/var/lib/docker` 误指向 NTFS
→ 路径验证脚本检查失败 → Docker 不启动，systemd 报错 → 用户被迫修复 ✓

**场景 3**：LiteLLM 容器启动失败
→ systemd 等 10 秒后自动重启 → 重复最多 5 次 → 5 分钟内未恢复则放弃 ✓

**场景 4**：Docker socket 权限问题
→ LiteLLM 服务以 root 运行，无权限问题 ✓

### 成本优化

| 文件 | 行数 | 说明 |
|------|------|------|
| docker-path-verify.sh | 88 | 新增脚本 |
| virtualization.nix | +4 | 只添加 systemd 钩子 |
| litellm-docker.nix | 165 | 新增服务模块 |
| configuration.nix | +9 | 导入 + 配置示例 |
| **总计** | **~265** | **净新增 265 行** |

### 配置文件完整性检查

```bash
# 验证所有文件存在
ls -la /etc/nixos/scripts/docker-path-verify.sh
ls -la /etc/nixos/modules/services/litellm-docker.nix
ls -la /etc/nixos/modules/virtualization.nix
ls -la /etc/nixos/configuration.nix

# 验证脚本语法
bash -n /etc/nixos/scripts/docker-path-verify.sh

# 验证 Nix 语法
nix flake check /etc/nixos
```

### 后续维护

- **监控**：`journalctl -u litellm-docker --since 1h` 查看服务日志
- **升级**：修改 `composeDir` 后无需修改其他配置
- **禁用**：设置 `services.litellm-docker.enable = false;` 并 `nixos-rebuild switch`
- **手动干预**：`systemctl restart litellm-docker` 强制重启

### 链接文档

- 路径验证脚本实现：`/etc/nixos/scripts/docker-path-verify.sh`
- 服务定义：`/etc/nixos/modules/services/litellm-docker.nix`
- Docker 配置：`/etc/nixos/modules/virtualization.nix`
- 启用位置：`/etc/nixos/configuration.nix` 行 93-100
