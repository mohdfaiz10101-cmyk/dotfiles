# OP 待办任务

## 待处理

### OPENCODE-GUARD — opencode 配置自检（每次 heartbeat 前置检查）

### DREAMMAIL-SEARCH — DreamMail数据搜索（低负载时执行）

### WIN-GIT-RETRY — Windows git备份重试
- [!] [失败 2026-04-21 11:01] SSH 连接拒绝（Connection refused），Windows 主机无响应

### BUSINESS-DATA-IMPORT — 外贸业务数据索引入库（2026-04-19 CC发现后派发）

- [!] [失败 2026-04-19 22:18] WIN-GIT-01 — Windows SSH服务在git commit时卡死（No space left on device误报→SSH端口不响应），需手动重启sshd服务后重试 [OP] [2026-04-19] [medium] Windows 数据备份：SSH到Win，git init ~/backup，定时把 Desktop/Documents/Downloads git commit推送到NixOS或本地仓库

### CRM-WECHAT-BRIDGE — 客户管理+微信+记忆打通（2026-04-19 CC诊断后派发）

- [!] [失败 2026-04-19 23:02] EMAIL-SEARCH — 需CC协助（SSH Windows+DreamMail数据定位），OP单次执行超限 邮件索引：(1) SSH Windows 192.168.2.36 找 DreamMail6 数据目录 (C:\\Users\\G\\AppData\\Roaming\\DreamMail 或 Program Files\\DreamMail6)，列出邮件文件；(2) sde1 只有 BoxCounter.ini 元数据，无实际邮件；(3) 找到邮件后 scp 到 /mnt/ai/data/dreammail-export/，解析写 email-index.json，top-500 发件人/收件人索引到 Letta

### HYPER-ABSORB — HyperChat/HyperOS精华吸收到3000（2026-04-19 CC审计后派发）

### FEATURES-3000 — 3000面板缺失功能补全（2026-04-19 CC全面扫描后派发）

### WECHAT-LIVE — 微信实时监控 + 看板推送（2026-04-19 CC派发）

### MONITOR-UNIFIED — 统一监控入口（2026-04-19 CC派发）

### P1-C 混合 AI SDK（CC 已完成 2026-04-19）

## 已完成（2026-04-19）

## 已完成（2026-04-18）

## 已清理（2026-04-19 过夜残留）

以下 AGI→OP/OP→CC 任务已确认服务在线或为假阳性，标记清理：

## 执行规则
- 完成后 `[ ]` → `[x]` + 日期 | 失败 2 次 → `[!]` 流转 CC
- AGI Brain 生成的"重启服务"任务一律忽略（Letta/Hub 均已确认在线）

---

## CRM-AUTO — 营销/网站自动化 + CRM

**目标**：基于 hub-api + Letta + macg + 微信，搭建私域 CRM 和营销自动化体系。

### CRM-01 [OP] 搭建 CRM 服务骨架（端口 3001）

### CRM-02 [OP] 客户档案存入 Letta

### CRM-03 [OP] 微信消息 → CRM 自动归档

### CRM-04 [OP] macg 营销任务调度

### CRM-05 [OP] CRM 看板页面（复用 9875 风格）

### CRM-06 [OP] 落地页/网站自动化（可选）

---

## UPGRADE-BATCH — 已有功能升级

> 升级原则：最小侵入，接入已有服务，不重建；验证：curl 测试 + 前端可见

### UPGRADE-01 [OP] Kanban Hub (9875) 接入实时数据

### UPGRADE-02 [OP] AGI Brain 升级模型路由 + 写入 Letta

### UPGRADE-03 [OP] macg 新增工具

### UPGRADE-04 [OP] wechat-agent 接入 Letta + macg

### UPGRADE-05 [OP] hub-mobile APK 升级 — webview 改为 3000

### UPGRADE-06 [OP] Chronos-Zenith 数据接入 3000 Dashboard

### UPGRADE-07 [OP] tech-digest 接入 3000 Dashboard
- [!] [2026-04-19 11:38] 无数据源 — 未找到 digest JSON 文件或 systemd 服务，需先实现 digest 生成器（roo-digest 脚本存在但无输出文件）

### UPGRADE-08 [OP] Letta distill 升级

### UPGRADE-09 [OP] Twenty CRM 启动 + HyperChat 数据迁移

---

## SELF-IMPROVE — GLM 自我改进 Agent

### SELF-IMPROVE-01 [OP] 创建 self-improve-agent.py

### SELF-IMPROVE-02 [OP] 创建每日定时器

---

## SENSE-UPGRADE — 感知系统升级（事件驱动 + 插件化）

**目标**：从"每分钟无脑轮询 + LLM 分析"升级为"有变化才触发 LLM"，减少浪费，提升感知质量。

### SENSE-01 [OP] 事件驱动感知层 — 只在状态变化时触发 LLM

当前：brain.py 每60s无论有无变化都调 LLM（约1440次/天，大量无效调用）。

### SENSE-02 [OP] 感知插件化 — 每类传感器独立脚本

当前：sense() 函数把所有采集逻辑堆在 brain.py 里（CPU/内存/服务/Android/浏览器/Chronos）。

  - `sensors/sys_metrics.py` → CPU/内存/磁盘（读 /proc） ✅
  - `sensors/service_health.py` → HTTP 健康检查（letta/litellm/hub-api） ✅
  - `sensors/cpu_hog.py` → 高 CPU 进程检测 ✅
  - `sensors/chronos_data.py` → 读 /tmp/chronos/*.json ✅
  - `sensors/wechat_status.py` → 微信 Agent 状态 ✅

### SENSE-03 [OP] 感知数据写入 hub-api（供 3000 前端实时展示）

当前：sense 数据只写 /tmp/agi-brain-status.json，前端无法直接读取。

### SENSE-04 [OP] 告警去重 + 冷却机制

当前：同一告警可能每分钟重复写入 op-tasks.md（已有 grep 去重但不完善）。

### [SELF-IMPROVE 2026-04-19] GLM 自动代码审查

---

## WECHAT-3000 — 微信历史系统融合到 3000 前端

**背景**：`~/launcher/wechat-history.html` 已有完整微信聊天查看器，后端 API 在 launcher-server.py(9875)，数据在 `/mnt/ai/data/wechat-merged/`。现在融合到 3000 控制台。

### WECHAT-3000-01 [CC完成 2026-04-19] 把 wechat-history.html 作为 iframe tab 嵌入 3000

### WECHAT-3000-02 [OP] 升级 WechatPanel 接入 launcher-server API

### WECHAT-3000-03 [OP] CRM 看板接入微信历史
## TOKEN-OPTIMIZE — 模型路由策略（2026-04-19 确认）
## LETTA-HEALTH — Letta 记忆健康修复（2026-04-19）

### LETTA-01 [OP] 定时 Letta 健康检查 + 自动写入

### LETTA-02 [OP] memory/*.md → Letta 批量蒸馏

### LETTA-03 [OP] AGI Brain 强制写入策略
  - 内容：CPU/内存/服务状态摘要
  - 不依赖是否有 alerts

## VERIFY-3000 — 前端实现验证（2026-04-19）

### VERIFY-01 [OP] 验证 WECHAT-3000-02

### VERIFY-02 [OP] 验证 WECHAT-3000-03

### VERIFY-03 [OP] 验证前端 3000 正常运行

### BUG-OPGUARD [OP] 修复误报：op-connection-guard.sh 检测逻辑

## PANEL-UPGRADE — 3000 面板升级（2026-04-19）

### PANEL-01 [OP] 集成 adk-generative-dashboard 图表组件

### PANEL-02 [OP] 参考 mission-control 升级 op-tasks 可视化看板

### PANEL-03 [OP] 参考 Agent Control 在 brain.py 加调用频率守卫

---

## DEPT 部门化执行体系（2026-04-19 新增）

### DEPT-01 [OP] 修复 tech-digest.py 输出 JSON 文件
**目标**：让 tech-digest.py 在抓取完成后，将结果写入 `~/Desktop/巡检报告/tech-digest-latest.json`
**具体步骤**：
1. 读 `~/launcher/tech-digest.py`，找到最终 report 输出的位置
2. 在输出 ideas-roadmap.md 之后，追加写入 JSON：
   ```python
   import json, pathlib
   out = pathlib.Path.home() / "Desktop/巡检报告/tech-digest-latest.json"
   out.parent.mkdir(parents=True, exist_ok=True)
   out.write_text(json.dumps({"timestamp": datetime.datetime.now().isoformat(), "items": report_items}, ensure_ascii=False, indent=2))
   ```
3. 运行 `python3 ~/launcher/tech-digest.py --dry-run` 或正常运行验证 JSON 文件生成
4. 验证：`ls -la ~/Desktop/巡检报告/tech-digest-latest.json`

### DEPT-02 [OP] 更新各部门 agent 写标准结果文件
**目标**：每个部门 agent 执行后将结果写入 `~/Desktop/巡检报告/{dept}-latest.json`
**涉及文件**：`~/.config/opencode/agents/marketing-coordinator.md`、`tech-researcher.md`、`tech-architect.md`、`ops-dispatcher.md`
**具体步骤**：
1. 在每个 agent 的"输出规范"章节末尾添加：
   ```
   ## 强制输出文件（每次执行 MUST 写入）
   执行完成后 MUST 运行 bash 命令将结果写入：
   ~/Desktop/巡检报告/{dept}-latest.json
   格式：{"dept": "{dept}", "timestamp": "ISO时间", "status": "ok/fail", "summary": "一句话", "items": [...最多10条]}
   ```
2. 确保 `~/Desktop/巡检报告/` 目录存在（`mkdir -p ~/Desktop/巡检报告`）
3. 验证：手动运行一个 agent，检查 JSON 文件生成

### DEPT-03 [OP] hub-api.py 新增 /api/dept-reports 端点
**目标**：读取 ~/Desktop/巡检报告/ 下所有 *-latest.json，返回聚合结果
**文件**：`~/hub/hub-api.py`
**具体步骤**：
1. 在 `/api/op-tasks` 端点之后添加：
   ```python
   DEPT_REPORTS_DIR = Path.home() / "Desktop/巡检报告"
   
   @app.get("/api/dept-reports")
   async def get_dept_reports():
       reports = {}
       for f in DEPT_REPORTS_DIR.glob("*-latest.json"):
           try:
               data = json.loads(f.read_text())
               dept = f.stem.replace("-latest", "")
               reports[dept] = data
           except:
               pass
       return {"reports": reports, "count": len(reports)}
   ```
2. 重启 hub-api 服务：`systemctl --user restart hub-api`
3. 测试：`curl http://localhost:7422/api/dept-reports`

### DEPT-04 [OP] marketing-coordinator 接入 tech-digest 数据
**目标**：marketing-coordinator 每次运行时先读 tech-digest-latest.json，生成与系统相关的营销洞察
**文件**：`~/.config/opencode/agents/marketing-coordinator.md`
**具体步骤**：
1. 在"工作流程"章节 Step 1 之前添加：
   ```
   ## 每日技术热点接入（MUST 执行）
   每次运行 MUST 先读取 `~/Desktop/巡检报告/tech-digest-latest.json`（若文件不存在则跳过）
   提取与 SpectrAI 产品相关的技术热点（AI/agent/llm 相关），转化为营销机会
   写入 ~/Desktop/巡检报告/marketing-latest.json
   ```
2. 手动触发测试：`systemctl --user start opencode-job-charlie-b445f233ebb8-marketing-scan.service`
3. 验证：`cat ~/Desktop/巡检报告/marketing-latest.json`

[x] [完成 2026-04-19 21:45] [已知假阳性] [OP→CC] [2026-04-19 21:10] heartbeat-task-check 连续 3 次重启失败，需 CC 人工排查根因（检查 LiteLLM 健康/模型配置/Docker 网络）
[x] [完成 2026-04-19 21:45] [已知假阳性] [OP→CC] [2026-04-19 21:10] service-nurse 连续 3 次重启失败，需 CC 人工排查根因（检查 LiteLLM 健康/模型配置/Docker 网络）
[x] [完成 2026-04-19 21:45] [已知假阳性] [OP→CC] [2026-04-19 21:30] discord-butler 连续 3 次重启失败，需 CC 人工排查根因（检查 LiteLLM 健康/模型配置/Docker 网络）
[x] [完成 2026-04-19 21:57] [已知假阳性] [OP→CC] [2026-04-19 21:50] [high] OP agent discord-butler 连续 3 次重启失败，需 CC 人工排查根因（检查 LiteLLM 健康/模型配置/Docker 网络）
- [!] FEAT-OP-CENTER-01 [OP] [2026-04-19] [high] 3000控制台新增"OP控制中心"Tab：任务看板(读op-tasks.md)、实时Feed(轮询op-live-feed.jsonl)、AGI状态(curl 9900)、触发OP按钮。参考/mnt/ai/apps/agi-control-plane/frontend/app/components/launcher/LauncherPanel.tsx格式

## 2026-04-20 网盘迁移 + 系统维护

- [!] [失败 2026-04-22 12:04] 需要root权限，sudo未配置setuid位，无法执行 — `sudo /etc/nixos/scripts/fix-firewall.sh`

  - `docker logs litellm --tail 50 | grep -i error`
  - `docker restart litellm`
  - `curl -sf http://localhost:4000/health && echo OK`

### ALIST-DEPLOY — 百度→123网盘迁移（AList Docker）

### WECHAT-WIN-KEY — 微信Windows端密钥提取

### 微信体系-期一（2026-04-21 CC派发）

- [!] [失败 2026-04-21 16:33] [OP-P1.2] 修复Wine WeChat DB解密 — WeChat未运行，需先启动Windows WeChat再提取密钥：SSH G@192.168.2.36 "cmd /c C:\Python312\python.exe -c \"import subprocess; r=subprocess.run(['wmic','process','where','name=WeChat.exe','get','ProcessId'],capture_output=True,text=True); print(r.stdout)\"" 获取PID；再用pywxdump提取密钥；密钥写入 ~/.cache/wechat-finance/keys.json；若SSH失败记录[!]

### Paperclip + 成本审计（2026-04-21 CC派发）
- [!] [失败 2026-04-22 12:04] Paperclip服务不可达 (localhost:3100)，无法获取agent列表：curl -s http://localhost:3100/api/agents 列出所有agent；停止无活跃任务的空跑agent心跳（预计6个）；结果写 /tmp/op-task-results.json
- [ ] [OP] [2026-04-21] 成本审计修复：docker logs litellm --tail 30 检查错误；curl -sf http://localhost:4000/health；检查Ollama状态并启动；结果写 /tmp/op-task-results.json
- [ ] [CC] [2026-04-21 14:00] AI配置告警需处理: 🔴 关键配置被篡改: opencode.json (CHANGED)
- [ ] [CC] [2026-04-21 14:00] AI配置告警需处理: 🔴 关键配置被篡改: oh-my-openagent.jsonc (CHANGED)
- [ ] [CC] [2026-04-21 22:30] AI配置告警需处理: 🔴 关键配置被篡改: AGENTS.md (CHANGED)
- [ ] [CC] [2026-04-21 22:30] AI配置告警需处理: 🔴 AGENTS.md 缺 FALSE_POSITIVE_GUARD 规则

## Agentic Loop 五模块（[CC] 2026-04-21 批量派发 → [OP] 执行）

### ① 反思循环（Reflection Loop）
- [ ] [OP-REFLECT] [$DATE] 在 op-tasks 执行框架加反思层
  - 每个 OP 任务完成后调 LiteLLM glm-4.6v-flash 打分（0-10）
  - 打分 prompt：`任务: {描述}\n执行结果: {result}\n打分标准：完成度/准确性/副作用，输出JSON {"score":N,"reason":"..."}`
  - score < 7 → 自动重试一次（最多2轮），重试记录写入 op-task-results.json
  - 实现位置：`~/hub/hub-api.py` 的 `/api/op-complete` 端点（或新建 `/api/op-reflect`）
  - 完成后写入 op-task-results.json，key=reflect_loop_enabled, value=true

### ② 工具 RAG（Tool Discovery via ChromaDB）
- [ ] [OP-TOOLRAG] [$DATE] 把所有可用工具描述向量化存入 ChromaDB
  - 扫描 `~/.claude/skills/` 下所有 skill 文件，提取 name/description/tags
  - 扫描 `~/hub/hub-api.py` endpoints 列表（grep "app.get\|app.post"）
  - 扫描 `~/.config/opencode/AGENTS.md` 工具节
  - 每条记录格式：`{"id": slug, "content": "工具名: desc\n用途: tags", "metadata": {"type": "skill|api|tool"}}`
  - 存入 ChromaDB（localhost:8000）collection: `tools-rag`
  - 写一个查询脚本 `~/.local/bin/tool-search.sh "<query>"` → top5 工具名+描述
  - 完成后在 op-task-results.json 写入 tool_rag_count=N

### ③ 置信度驱动介入（Confidence-gated Interruption）
- [ ] [OP-CONFIDENCE] [$DATE] 在 OP 任务执行前加置信度自评
  - 每个任务开始时用 glm-4.6v-flash 自评：`任务: {desc}\n我有多大把握完成？输出JSON {"confidence": 0-100, "blockers": [...]}`
  - confidence < 60 → 不执行，写入 op-task-results.json status=needs_human，内容=blockers
  - confidence 60-80 → 执行但执行后强制反思循环
  - confidence > 80 → 正常执行
  - 实现：在 OP 任务分发脚本（`~/hub/hub-api.py` 的 `run_op_task`）前插入这层判断

### ④ 经验回放（Experience Replay → Letta Archival）
- [ ] [OP-EXPreplay] [$DATE] 自动把 OP 任务结果写入 Letta archival memory
  - 格式：`[EXPERIENCE] {date} 任务: {desc} | 策略: {approach} | 结果: {outcome} | 耗时: {duration}s`
  - tags: experience-replay, op-task, {task_type}
  - Letta agent: agent-02380eae-9ac2-45f4-b9b2-dabf40e0abea（code-assistant）
  - API: POST /v1/agents/{id}/archival-memory  body: {"text": "...", "tags": [...]}
  - 在 hub-api.py op-complete 端点里追加这个写入
  - 同时把成功经验追加到 memory/lessons-learned.md（格式：`- [日期] [OP-auto] 场景：内容`）

### ⑤ SubTask DAG（并行任务图）
- [ ] [OP-DAG] [$DATE] OP 收到复杂任务时输出 SubTask DAG 再执行
  - 实现：`~/.local/bin/op-dag-plan.py`
  - 输入：任务描述文字
  - 用 glm-4.6v-flash 分解：`把以下任务拆分为并行子任务DAG，输出JSON {"tasks":[{"id":"t1","desc":"...","depends_on":[]},...]}`
  - 无依赖的子任务并行执行（asyncio/threading）
  - 执行结果汇总写入 op-task-results.json，key=dag_{task_hash}
  - 集成到 hub-api.py POST /api/op-dag 端点

## AI 资讯 Feed 集成到 3000 控制台（[CC] 2026-04-21）

### [CC-FEED-1] hub-api.py 加 /api/ai-news 端点
- [ ] 在 `~/hub/hub-api.py` 新增 GET `/api/ai-news`
  - 读取 `~/Desktop/巡检报告/` 目录下所有 planning-*.md 和晨报-*.md
  - 每个文件提取：日期、标题、前200字摘要
  - 返回 JSON：`[{"date": "...", "type": "planning|morning", "title": "...", "summary": "...", "path": "..."}]`
  - 按日期降序，最多返回30条

### [CC-FEED-2] 3000 控制台新增 "AI 资讯" Tab
- [ ] 文件：`/mnt/ai/apps/agi-control-plane/frontend/app/components/feed/AINewsFeed.tsx`
  - 轮询 `/api/ai-news`（每5分钟）
  - 卡片布局：日期 + 类型徽章（规划/晨报）+ 摘要文本
  - Catppuccin Mocha 配色，点击展开全文（modal 或展开行）
- [ ] 把 AINewsFeed 加到 `/mnt/ai/apps/agi-control-plane/frontend/app/page.tsx` 或 layout 的 Tab 导航
  - Tab 名："资讯" 或 "Feed"，图标 📰

### [CC-FEED-3] OP 每日研究结果写入 Feed
- [ ] 修改 Letta planning-trigger.sh：写完 planning-*.md 后调用 `/api/feed-ingest` 同步
- [ ] 新增 `/api/feed-ingest` 端点接收任意文本+类型，追加到 feed 存储

## 2026 AGI 全技术吸收计划（[CC+OP] 2026-04-21 今日全部执行）

### [CC-N8N] n8n AI Nodes 接通 Hub API
- [ ] 在 n8n 创建工作流：HTTP触发 → GLM-4.6v-flash 意图分类 → 路由到 Hub API 对应端点
  - n8n 地址：检查 `docker ps | grep n8n` 获取端口
  - 创建 Webhook 节点监听 POST /webhook/intake
  - 加 HTTP Request 节点调 LiteLLM `http://172.19.0.1:4000/v1/chat/completions` model=glm-4.6v-flash
  - 意图分类 prompt：`输入:{text} 分类到: TASK/CRM/WECHAT/KNOWLEDGE/QUERY，输出JSON{"intent":"..."}`
  - 按 intent 路由到 Hub API 对应端点（/api/op-tasks、/api/crm/opportunity 等）
  - 完成后写 op-task-results.json n8n_ai_workflow=true

### [CC-OODA] OP 任务执行改造为 OODA Loop 结构
- [ ] 修改 `~/hub/hub-api.py` 的 OP 任务执行逻辑，每个任务按 OODA 四阶段执行：
  - **Observe**：收集任务相关上下文（读 Letta archival 相关经验 + 检查系统状态）
  - **Orient**：GLM 分析：`已知信息:{ctx} 任务:{desc} 最佳策略是?` → 生成执行计划
  - **Decide**：置信度评估（≥60 执行，<60 → needs_human）
  - **Act**：执行 + 反思循环（score<7 重试）
  - 每阶段结果写入 `/tmp/ooda-{task_id}.json` 便于调试
  - 完成后 op-task-results.json 写入 ooda_loop_enabled=true

### [CC-INTAKE] /intake 多意图分解 + Fast Intent 路由
- [ ] 升级 `~/hub/hub-api.py` POST `/intake` 端点：
  - 接收输入后先用 glm-4.6v-flash 做 **多意图分解**：
    `输入:{text} 识别所有意图，输出JSON{"intents":[{"type":"TASK|CRM|KNOWLEDGE|WECHAT|QUERY","content":"...","priority":1-3}]}`
  - 每个意图并行处理（asyncio.gather）
  - 意图类型路由表：
    - TASK → 写 op-tasks.md + 触发 OP
    - CRM → POST /api/crm/opportunity（Twenty）
    - KNOWLEDGE → POST /api/knowledge/store（Letta archival）
    - WECHAT → macg_wechat_reply MCP
    - QUERY → 直接 GLM 回答
  - 结果聚合返回 `{"intents_processed": N, "results": [...]}`
  - 同时在 3000 /intake 显示每个意图的处理状态

### [CC-MEM0] Mem0 三温记忆控制器
- [ ] 创建 `~/hub/memory_controller.py` 实现三温模型：
  - **Hot（0-24h）**：直接存提示窗口变量（字典缓存），最多50条，超出淘汰到 Warm
  - **Warm（1-30天）**：Letta core memory block（结构化事实），调 `/v1/blocks/{id}` PATCH 更新
  - **Cold（>30天）**：Letta archival memory，标 tag: cold-storage
  - 提供函数：`mem_store(text, importance=1-5)` 自动按重要性+时间分层
  - `mem_retrieve(query, max_results=5)` 先查Hot→再查Warm→最后查Cold，返回最相关
  - 在 hub-api.py 注册为 `/api/memory/store` 和 `/api/memory/search`
  - 完成后测试：写入3条不同重要性记录，验证分层存储

### [CC-MAGMA] MAGMA 多图记忆 tag 策略
- [ ] 所有写入 Letta archival 的记录改为带多维 tag：
  - semantic: 语义类型（task/contact/knowledge/event）
  - temporal: 时间戳 epoch
  - causal: 因果链 ID（任务触发的知识关联同一 chain_id）
  - entity: 涉及实体名（人名/公司/工具名）
  - 修改 hub-api.py 中所有 letta archival write 调用，追加以上 metadata
  - 升级 `/api/memory/search` 支持按 tag 过滤查询（`?tag=semantic:task&entity=Charlie`）
  - 3000 知识图谱页（/graph）从 ChromaDB + Letta 双源拉节点数据

### [OP-OMNI] Qwen3.5-Omni 部署（语音+多模态输入）
- [ ] 检查可用 GPU 内存：`nvidia-smi --query-gpu=memory.free --format=csv`
  - 若空闲 VRAM ≥ 8GB：拉取 Qwen3.5-Omni 镜像 `docker pull qwenomni/qwen3.5-omni:latest`（或 HuggingFace 路径）
  - 若不足：跳过，改用 API 模式（SiliconFlow qwen-omni API）
  - 配置 LiteLLM 新增 model: `qwen-omni` → 路由到本地或 SiliconFlow
  - 在 hub-api.py POST `/api/voice-intake` 接收 base64 audio → Omni 转文字+意图 → /intake
  - 桌宠加语音按钮（后续 CC 完成）
  - 完成后写 op-task-results.json omni_deployed=true/api_mode

### [CC-VISION] GLM-4.6V 多模态 /intake（图片→意图→执行）
- [ ] 升级 hub-api.py POST `/intake` 支持图片输入：
  - 接收 base64 image 字段时，调 LiteLLM model=glm-4.6v-flash（vision）
  - prompt：`图片内容是什么？识别任务意图，输出JSON{"intent":"...","action":"...","entities":[]}`
  - 识别到截图/UI → 自动执行 Playwright 操作（调 /api/browser 端点）
  - 识别到文档/发票 → 结构化提取 → 存 knowledge
  - 识别到联系人名片 → 写 Twenty CRM
  - 3000 UniversalBar 已支持拖入图片（检查 UniversalBar.tsx 确认 base64 传递）

### [OP-EVOLVE] MetaAgent 工具自发现 + 自动注册
- [ ] 基于 OP-TOOLRAG（已派），追加自发现逻辑：
  - 每次 OP 任务完成后，检查是否调用了未在 Tool RAG 中的命令
  - 新命令 → 自动生成描述：`命令:{cmd} 功能是什么?` → GLM → 写入 ChromaDB tools-rag
  - 每周日 OP 运行"工具进化"：读取 op-task-results.json 中频繁成功的模式 → 打包为新 skill
  - 新 skill 写入 `~/.claude/skills/` 并更新 Tool RAG
  - 完成后 op-task-results.json 写入 meta_tool_learning=true

### [CC-ROUTER] AdaptOrch 升级 Claude Router Hook
- [ ] 修改 `~/.local/bin/cc-letta-check.sh`（UserPromptSubmit hook）：
  - 当前：固定路由规则（DELEGATE TO HAIKU/OPUS/standard）
  - 升级为：先提取任务特征（长度/关键词/复杂度/领域），再动态选路由
  - 特征提取：`任务:{prompt[:100]} 复杂度(1-5)/领域(code|ops|chat|research)/模型推荐，输出JSON`
  - 按特征路由：复杂度1-2+chat → GLM（零成本）| 复杂度3+code → Sonnet | 复杂度5+research → Opus
  - 保持与现有 `[LETTA: xxx]` 上下文注入兼容
  - 完成后运行3个测试 prompt 验证路由准确性

### [CC-AFLOW] AFlow 风格任务规划端点
- [ ] hub-api.py 新增 POST `/api/plan-task`：
  - 输入：`{"task": "...", "context": "..."}`
  - 用 GLM 做多轮搜索：先生成3个执行方案 → 评估每个方案成本/成功率 → 选最优
  - 输出：`{"plan": [...steps], "confidence": N, "alternatives": [...]}`
  - OP 接到复杂任务时可先调此端点获取最优计划再执行
  - 集成到 3000 OP中心面板：任务详情页加"AI规划"按钮

## [CC→OP] MUSETALK-BUILD — MuseTalk P2 部署（2026-04-23）

- [ ] **MUSETALK-B1** 下载模型权重（在 /mnt/ai/apps/musetalk 目录执行）
  ```bash
  cd /mnt/ai/apps/musetalk
  export HF_ENDPOINT=https://hf-mirror.com
  mkdir -p ~/agi/models/musetalk/{musetalkV15,musetalk,sd-vae,whisper,dwpose,syncnet,face-parse-bisent}
  # 下载到宿主机 models 目录（容器挂载点）
  pip install -U "huggingface_hub[cli]" gdown -q
  # MuseTalk V1.5 主模型
  huggingface-cli download TMElyralab/MuseTalk \
    --local-dir ~/agi/models/musetalk \
    --include "musetalkV15/musetalk.json" "musetalkV15/unet.pth"
  # SD VAE
  huggingface-cli download stabilityai/sd-vae-ft-mse \
    --local-dir ~/agi/models/musetalk/sd-vae \
    --include "config.json" "diffusion_pytorch_model.bin"
  # Whisper tiny
  huggingface-cli download openai/whisper-tiny \
    --local-dir ~/agi/models/musetalk/whisper \
    --include "config.json" "pytorch_model.bin" "preprocessor_config.json"
  # DWPose
  huggingface-cli download yzd-v/DWPose \
    --local-dir ~/agi/models/musetalk/dwpose \
    --include "dw-ll_ucoco_384.pth"
  # Face parse
  gdown --id 154JgKpzCPW82qINcVieuPH3fZ2e0P812 -O ~/agi/models/musetalk/face-parse-bisent/79999_iter.pth
  curl -L https://download.pytorch.org/models/resnet18-5c106cde.pth \
    -o ~/agi/models/musetalk/face-parse-bisent/resnet18-5c106cde.pth
  ```
  成功条件：`ls ~/agi/models/musetalk/musetalkV15/unet.pth` 存在

- [ ] **MUSETALK-B2** 构建 Docker 镜像（约30分钟）
  ```bash
  cd /mnt/ai/apps/musetalk
  docker build -t musetalk:local . 2>&1 | tee /tmp/musetalk-build.log
  echo "build exit: $?"
  ```
  成功条件：`docker images | grep musetalk:local` 有输出

- [ ] **MUSETALK-B3** 启动容器 + 验证 API
  ```bash
  # 复制头像到 avatar 目录
  cp ~/agi/data/avatar/niumoumou.jpg ~/agi/data/avatar/
  cd ~/agi/docker/virtual-person
  docker compose --profile musetalk up -d musetalk
  sleep 10
  curl -s http://localhost:9881/health
  ```
  成功条件：health 返回 {"status":"ok","models_ready":true}
  结果写入 op-task-results.json


## WECHAT-PIPELINE — 微信 Agent 管道验证（2026-04-24 CC派发）

- [ ] **[OP-P1.1]** 验证 UOS WeChat 消息读取
  ```bash
  DRY_RUN=1 timeout 40 python3 ~/agi/wechat_agent.py 2>&1 | tee /tmp/wechat-dryrun.log
  cat /tmp/wechat-dryrun.log | tail -20
  ls ~/.cache/wechat-finance/decrypted/ 2>/dev/null | head -5 || echo "无解密DB"
  ```
  成功条件："本轮新消息 N 条" 或有解密DB存在；结果写入 op-task-results.json

- [ ] **[OP-P1.3]** 建立 CRM DB 并验证自动写入
  ```bash
  # 检查并创建 CRM DB
  mkdir -p /mnt/ai/apps/wechat-agent/data
  sqlite3 /mnt/ai/apps/wechat-agent/data/crm.db "SELECT COUNT(*) FROM contacts" 2>/dev/null || \
    python3 -c "import sqlite3; conn=sqlite3.connect('/mnt/ai/apps/wechat-agent/data/crm.db'); conn.execute('CREATE TABLE IF NOT EXISTS contacts(id INTEGER PRIMARY KEY, name TEXT, wxid TEXT, last_seen TEXT)'); conn.commit(); print('TABLE_OK')"
  # 运行一次非DRY_RUN poll（等60s）
  timeout 90 python3 ~/agi/wechat_agent.py 2>&1 | tail -10
  sqlite3 /mnt/ai/apps/wechat-agent/data/crm.db "SELECT COUNT(*) FROM contacts"
  ```
  成功条件：contacts 表 count > 0；结果写入 op-task-results.json

- [ ] **[OP-P4.2]** 配置每日晨报（09:00 自动推送）
  ```bash
  # 创建晨报脚本
  cat > ~/.local/bin/morning-brief.sh << 'SCRIPT'
  #!/bin/bash
  TODAY=$(date '+%Y-%m-%d')
  PENDING=$(grep -c '^\- \[ \]' ~/op-tasks.md 2>/dev/null || echo 0)
  FAILED=$(grep -c '^\- \[!\]' ~/op-tasks.md 2>/dev/null || echo 0)
  BRIEF="今日待办: ${PENDING}条 | 失败: ${FAILED}条 | $(date '+%H:%M')"
  notify-send "AGI 晨报" "$BRIEF" --urgency=normal
  mkdir -p ~/Desktop/巡检报告
  echo "# 晨报 ${TODAY}" > ~/Desktop/巡检报告/晨报-${TODAY}.md
  echo "待处理: ${PENDING} | 失败: ${FAILED}" >> ~/Desktop/巡检报告/晨报-${TODAY}.md
  SCRIPT
  chmod +x ~/.local/bin/morning-brief.sh
  # 创建 systemd timer
  mkdir -p ~/.config/systemd/user
  cat > ~/.config/systemd/user/morning-brief.service << 'SVC'
  [Unit]
  Description=AGI 每日晨报
  [Service]
  Type=oneshot
  ExecStart=/bin/bash /home/charlie/.local/bin/morning-brief.sh
  SVC
  cat > ~/.config/systemd/user/morning-brief.timer << 'TIMER'
  [Unit]
  Description=AGI 晨报 09:00 触发
  [Timer]
  OnCalendar=*-*-* 09:00:00
  Persistent=true
  [Install]
  WantedBy=timers.target
  TIMER
  systemctl --user daemon-reload
  systemctl --user enable --now morning-brief.timer
  systemctl --user list-timers morning-brief.timer
  ```
  成功条件：timer 已启动，`systemctl --user list-timers` 显示下次09:00触发；结果写入 op-task-results.json
