---
name: 必须提供访问入口
description: 每次创建/部署 Web 服务或前端后，必须告诉用户访问 URL 和启动命令
type: feedback
---

每次部署或启动 Web 服务/前端/API 后，MUST 在回复中明确给出访问入口。

**Why:** 用户反馈"每次做好东西都没给入口"，所有 AI 都有这个问题。做完不给链接 = 没做。

**How to apply:**
- 部署 Web 服务后 → 输出 `访问: http://localhost:{端口}`
- 启动前端后 → 输出启动命令 + URL
- 创建 API 后 → 输出 curl 示例
- 不要只说"已部署"，必须附带可点击/可复制的访问方式
