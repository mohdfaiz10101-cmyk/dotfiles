---
name: agent-wechat-deploy
description: "agent-wechat Docker 容器部署：Wine+Xvfb+AT-SPI 微信容器，auth-token 文件挂载方式传入认证令牌，端口 6174 REST/noVNC API"
user-invocable: false
version: "1.0.0"
category: docker
tags: [wechat, docker, wine, xvfb, agent-wechat, deploy]
effort: medium
auto-generated: true
created: 2026-04-23
---

# Agent Wechat Deploy

## 场景
# agent-wechat 部署流程\n\n## 前置\n- Docker Root 确认在大磁盘（/mnt/ai/docker）\n- ghcr.io/thisnick/agent-wechat:latest\n\n## 关键点\n- AGENT_WECHAT_TOKEN 不能用 -e 传入（zsh token展开失败），必须写文件挂载 /data/auth-token\n- 需要 --cap-add SYS_PTRACE --cap-add NET_ADMIN --security-opt seccomp=unconfined\n- Session 配置读取失败（Failed to read: session.*）是正常现象，不影响运行\n\n## 步骤\n```bash\nmkdir -p /mnt/ai/agent-wechat-data\npython3 -c "import secrets; t=secrets.token_hex(32); open('/mnt/ai/agent-wechat-data/auth-token','w').write(t); print('TOKEN:', t)"\n\ndocker run -d \\n  --name agent-wechat \\n  --security-opt seccomp=unconfined \\n  --cap-add SYS_PTRACE \\n  --cap-add NET_ADMIN \\n  -p 6174:6174 \\n  -e DISPLAY=:99 \\n  -v /mnt/ai/agent-wechat-data:/data \\n  ghcr.io/thisnick/agent-wechat:latest\n```\n\n## 验证\n```bash\ncurl -s -H "Authorization: Bearer $(cat /mnt/ai/agent-wechat-data/auth-token)" http://localhost:6174/health\ncurl -s -H "Authorization: Bearer $(cat /mnt/ai/agent-wechat-data/auth-token)" http://localhost:6174/api/status\n# noVNC 扫码: http://localhost:6174/vnc/\n```\n\n## 登录状态\n- logged_out → 打开 noVNC 扫码\n- logged_in → 可调用消息 API

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
