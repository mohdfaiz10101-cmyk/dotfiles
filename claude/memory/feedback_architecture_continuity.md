---
name: 架构延续性 — 禁止每次重新发明
description: 新会话必须先检查已有架构决策和代码，延续而非重做
type: feedback
---

每次新会话涉及架构/系统设计时，MUST 先检查已有代码和决策记录，延续而非重新发明。

**Why:** 用户多次反馈"每次都在变来变去"，之前规划好的架构（macg.py LangGraph、flows/、unified-agent-command-center plan）没有被延续，反而每次新会话都从零开始做新东西。这浪费了大量时间和 token。

**How to apply:**
1. 涉及"统一界面""控制台""架构"话题时 → 先 grep `memory/app-dev-journal.md` + `~/.claude/plans/` + `~/agi/`
2. 发现已有代码/方案 → 在此基础上迭代，不新建
3. 关键已有资产：
   - `~/agi/macg.py` — LangGraph Multi-Agent CLI（统一入口）
   - `~/agi/flows/` — 5 个 LangGraph 工作流
   - `~/.claude/plans/unified-agent-command-center.md` — 总规划
   - `/mnt/ai/apps/agi-control-plane/` — 前端+后端
4. 禁止：做完东西不给访问入口、每次重写前端、忽略已有 LangGraph 代码
