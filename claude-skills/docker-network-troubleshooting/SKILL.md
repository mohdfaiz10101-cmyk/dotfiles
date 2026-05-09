---
name: docker-network-troubleshooting
description: Docker 容器网络问题排查：端口冲突、DNS、代理配置
category: containers
tags: [docker, networking, troubleshooting]
version: "1.0.0"
effort: medium
user-invocable: false
---

# Docker Network Troubleshooting

快速诊断和解决 Docker 容器网络问题。

## 场景
- 容器无法访问外网
- 端口映射后外部无法访问
- 容器间网络不通
- DNS 解析失败

## 排查步骤

### 1. 检查容器网络状态
```bash
docker inspect <container_id> | jq '.[0].NetworkSettings'
docker exec <container_id> ip addr
docker exec <container_id> ping -c 3 8.8.8.8
```

### 2. 常见问题修复

**端口冲突**：
```bash
# 检查端口占用
ss -tlnp | grep <port>
# 修改 docker-compose.yml 端口映射
```

**DNS 问题**：
```bash
# 检查 DNS 配置
docker exec <container_id> cat /etc/resolv.conf
# 修改 daemon.json 添加 DNS
echo '{"dns": ["8.8.8.8", "1.1.1.1"]}' | sudo tee /etc/docker/daemon.json
systemctl restart docker
```

**代理配置**：
```bash
# 设置 Docker daemon 代理
mkdir -p /etc/systemd/system/docker.service.d
cat <<EOF > /etc/systemd/system/docker.service.d/http-proxy.conf
[Service]
Environment="HTTP_PROXY=http://127.0.0.1:7890"
Environment="HTTPS_PROXY=http://127.0.0.1:7890"
Environment="NO_PROXY=localhost,127.0.0.1"
EOF
systemctl daemon-reload
systemctl restart docker
```

### 3. 网络模式切换
```bash
# 切换到 host 模式测试
docker run --network=host <image>
# 创建自定义网络
docker network create --driver bridge custom_net
```

## 注意事项
- 重启 Docker daemon 会中断所有容器
- host 模式绕过网络隔离，注意安全性
- 代理配置需同时设置 daemon 和容器级别
