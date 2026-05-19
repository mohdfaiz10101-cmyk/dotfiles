---
name: AI工具决策必须联网搜最新文档
description: 涉及AI工具/框架的方案决策前必须WebSearch验证最新版本行为
type: feedback
---

AI 工具（OpenCode、LiteLLM、Letta、MCP、Claude API 等）相关决策 MUST 先联网搜索最新文档和 GitHub issues，不能依赖记忆中的旧判断。

**Why:** 2026-05-18 发现"删除坏 MCP 否则阻塞启动"这个判断已过时——OpenCode v1.15+ 已改为自动禁用失败 MCP，不再阻塞。旧记忆导致错误建议。

**How to apply:**
- 涉及 AI 工具版本行为差异时：WebSearch "site:github.com/sst/opencode <topic> 2026" 或对应仓库
- 必须包含当前年份（2026）确保结果新鲜
- 找到 GitHub issue/PR 后核对版本号是否匹配用户当前版本
- 搜索结果要区分：旧版 bug 已修复 vs 新版引入的 bug
