# 跨会话待办

<!-- 清理日期: 2026-04-17 — 删除所有 [x] 已完成条目，只保留未完成任务 -->

## 高优先

### 3000 控制台升级路线图（[Sonnet] 2026-04-21）
- [ ] **P1** TopBar 服务健康灯：每30s ping 关键端口（4000/8283/9800/3001），显示红绿点
- [ ] **P1** Projects 里程碑改为 JSON 配置文件（不再硬编码在 route.ts）
- [ ] **P2** 通知中心：OP失败/Docker unhealthy 推送到右上角 badge
- [ ] **P3** Cmd+K 全局搜索跨面板
- 提醒：下次会话主动问用户是否推进 3000 控制台升级

- [ ] **全模型幻觉防护系统（P1）** — 覆盖所有 AI 模型（GLM/DeepSeek/Sonnet/Opus/Haiku）
  - **触发**：GLM 声称 OpenCode 已停止开发（幻觉）
  - 方案 A：AGENTS.md 加「工具现状速查表」（名称/版本/状态/验证命令）
  - 方案 B：op-tasks 执行前强制 shell 验证关键工具状态（不信 LLM 口头声明）
  - 方案 C：不确定工具状态时强制 WebSearch 验证（不走记忆/训练数据）
  - 方案 D：加入「知识截止声明」提示词：模型说新工具状态时必须标注 [需验证]
  - 优先实施 B+C，成本最低效果最直接

- [ ] **Docker data-root 迁移到 POOL-D1**（[Sonnet] 2026-04-21）
  - 目标：`/mnt/pool-disks/POOL-D1/docker`（ext4, 748G）
  - 步骤：改 `/etc/nixos/modules/virtualization.nix` data-root → nixos-rebuild → 验证
  - 前提：docker 停止，rsync 数据已同步完成
  - 完成后删除 `/mnt/ai/docker/` 释放空间

## 中优先

- [ ] **综合方案：你的个人 AI 系统** — Week 1-2 完成(2026-04-08)，Week 3-4 待执行
  - [ ] Week 2 Part 2：技能提炼（Qwen3 Judge + 业务知识投喂）
  - [ ] Week 3：工具接入（Playwright + 文件读写 + Qdrant）
  - [ ] Week 4：业务对接（UI-TARS + DeepSeek + 真实询盘）
- [ ] **Mastra.js 自主采购代理** — 框架完成，LiteLLM 已修复(2026-04-08)，待验证运行

## 配置持久化

- [ ] 为新 git 仓库设置远程 origin（需用户提供 URL）
  - `~/.claude/projects/-home-charlie` 和 `~/.claude/skills`
- [ ] 虚拟机测试完整恢复流程（按 6 步恢复指南验证）
- [ ] 自动化健康检查（Docker 容器状态 + Git 仓库完整性定期验证）

## 微信体系

- [x] **AGI Brain 构建（2026-04-20验证）** — ✅ 服务正常运行（PID: 2185071）
   - 相关文件：`~/agi/brain.py`
   - 服务状态：`systemctl --user status agi-brain`
- [ ] **微信 Windows 端密钥提取** — 需在 Windows 运行 pywxdump 或 wechat-auto-decrypt.ps1
   - Windows DB: /mnt/data/WeChat Files/w422417869/Msg/（79 个加密文件）
   - 提取密钥后可用 wechat-finance 工具解密
   - 阻塞原因：等待用户在 Windows 端手动执行
- [ ] **微信管理平台开发** — CLI + Web UI + PostgreSQL + 连接 OpenCode
- [ ] **Agent 知识库可视化方案设计**

## 架构缺陷修复（2026-04-17 审计）

- [ ] **op-tasks 已完成归档** — 定期 archive >24h 的 [x] 条目，保持活跃文件精简
- [ ] **chronos-subconscious 降频** — 从 20min 改为 1h，加 CPU idle 条件
- [ ] **PYTHONPATH 全局设置** — 统一 python3.13/3.12 或设全局 site-packages 路径

## 系统维护

- [ ] **成本审计服务修复（P1）** — LiteLLM 已验证运行，Ollama 待启动
   - [x] 检查 LiteLLM 状态：✅ 运行正常（Up 10h, healthy）
   - [x] 验证 LiteLLM API：✅ http://localhost:4000/health 可达
   - [ ] 启动 Ollama：`systemctl start ollama` 或 Docker 运行（当前不可达）
   - [ ] 配置成本告警通知（Telegram + notify-send）
   - [ ] 添加服务健康监控（systemd + 定时检查）
- [ ] **firewall.service 修复** — 运行 `sudo /etc/nixos/scripts/fix-firewall.sh`（4步，脚本已就绪）
- [ ] **NixOS nixpkgs 更新** — `nix flake update nixpkgs --flake /etc/nixos` + rebuild（锁定 2026-04-09）
- [ ] **Paperclip 空壳 agent 归档** — 停止 6 个空壳 agent 心跳
- [ ] **P0 Git 远程 origin** — 等用户提供远程仓库地址

## 开发项目

- [ ] **Sourcing 采购网站完善** — `~/projects/projects/sourcing-site/`（Astro 5 + Tailwind 4，端口 4322）
  - 现状：半成品，只有 index.html 主页（Hero + 产品分类 + AI产品生成器 + 报价表单）
  - api/components/layouts 目录为空
  - src/pages/ 只有 index.html
  - 需要：拆分组件、补充 API 端点、连接 LiteLLM 替代 HyperChat、产品 CRUD
- [ ] **Claude Code 风格宠物** — usik/tamagotchi Phase 2，AI Agent 互动插件
- [ ] **配置 DeepSeek 训练环境** — 安装 PyTorch 或配置 Docker 容器

## 低优先 / 待确认

- [ ] 系统健康监控优化（调整 system-health-monitor 避免误报）

## IO Wait 待诊断

- [ ] [ORCH→CC] [2026-04-17 17:52] 设计移动端专用状态卡片视图
- 注: IO Wait 高问题已通过架构优化缓解（loop0 迁移到 /mnt/ai ext4），暂无需专门诊断

## 三方实时对话室（P1）
- 方案2：WebSocket 三方对话室 — CC/OP/用户实时互看对话
- 技术选型：FastAPI WebSocket + hub.html 嵌入 + op-live-feed.jsonl 作为消息总线
- CC 和 OP 各自身份广播到 /ws/dialogue，浏览器实时显示
- 集成到 agi-control-plane 3000 新增 "对话室" tab
- 优先级：高（用户强需求）

## 微信人格模拟（P2）
- 从微信历史提取用户对话风格 → 训练/few-shot 人格模型
- 社区最佳实践：CharacterLM / PersonaHub / LIMA instruction tuning
- 实现路径：wechat_merged DB → 提取用户消息 → 构建 few-shot prompt → 注入 GLM system prompt
- 输出：预测用户下一步走向，显示在 3000 dashboard 右侧面板

## 统一智能体系 — Universal AI Intake（P1，分4期）

> 目标：一个对话窗口（port 3000）自动识别任何输入 → 路由 → 执行 → 存档
> 现状诊断（2026-04-20）：
> - wechat-agent 运行但静默（Wine WeChat DB 加密，UOS 未验证）
> - Skills/CRM/hub-api 存在但未串联
> - Universal Intake / 知识图谱 完全未实现

### 期一：修通微信 Agent（[OP] 可立即执行）

- [ ] **[OP-P1.1] 验证 UOS WeChat 消息读取**
  - 运行：`DRY_RUN=1 timeout 40 python3 ~/agi/wechat_agent.py 2>&1 | tee /tmp/wechat-dryrun.log`
  - 检查 /tmp/wechat-dryrun.log 是否有"本轮新消息 N 条"
  - 若无消息：检查 `ls ~/.cache/wechat-finance/decrypted/` 是否有解密 DB
  - 若解密 DB 存在：`sqlite3 ~/.cache/wechat-finance/decrypted/message_0.db "SELECT COUNT(*) FROM MSG"` 验证行数
  - 报告结果到 op-task-results.json

- [ ] **[OP-P1.2] 修复 Wine WeChat DB 解密**
  - Wine DB 路径：`/mnt/data/WeChat Files/w422417869/Msg/ChatMsg.db`（file is not a database = 需解密）
  - 检查 `~/.cache/wechat-finance/keys.json` 是否包含 wine 账号密钥
  - 若无：通过 SSH 在 Windows 运行密钥提取：
    ```
    ssh G@192.168.2.36 "cmd /c C:\Python312\python.exe C:\Users\G\pywxdump\main.py key"
    ```
  - 若 pywxdump 不存在：`ssh G@192.168.2.36 "cmd /c winget install python && pip install pywxdump"`
  - 密钥格式 hex 写入 keys.json

- [ ] **[OP-P1.3] 修通 CRM 自动写入**
  - 验证：`sqlite3 /mnt/ai/apps/wechat-agent/data/crm.db "SELECT COUNT(*) FROM contacts"` 
  - 若表不存在：检查 `grep -n "CREATE TABLE\|upsert_contact" ~/agi/wechat_agent.py | head -10`
  - 运行一次真实 poll（非 DRY_RUN），等待 60s 观察 CRM 行数变化
  - 成功条件：contacts 表有新增记录

- [ ] **[OP-P1.4] 微信群消息分类管道**
  - 检查 wechat_agent.py classify_message 函数是否有 TRADE/CUSTOMER/GROUP 分类
  - 若无外贸意图分类：追加到 classify 逻辑：
    - 关键词：询价/报价/样品/FOB/MOQ/delivery → intent=TRADE_INQUIRY
    - 联系人名片截图 → intent=CONTACT_CARD  
    - 群@我 → intent=GROUP_MENTION
  - 外贸意图触发自动在 Twenty CRM 创建 opportunity（调 hub-api `/api/crm/opportunity`）

### 期二：Universal Intake 接入 3000（[CC] 执行）

- [ ] **[CC-P2.1] port 3000 添加 Universal Bar 组件**
  - 文件：`/mnt/ai/apps/agi-control-plane/frontend/app/components/intake/UniversalBar.tsx`
  - 单行输入框 + 拖拽区域（图片/文件/文字）
  - 拖入图片 → POST `/intake` with base64 + type=image
  - 拖入文件 → POST `/intake` with filepath + type=file  
  - 文字 → POST `/intake` with text + type=text
  - 放在 3000 布局底部（类似浮动 bar）

- [ ] **[CC-P2.2] hub-api.py 添加 /intake 端点**
  - 接收任意输入 → 实体提取（GLM 4.6v-flash）
  - 实体类型：人名/公司/任务/时间/地点/金额
  - 路由规则：
    - 含联系人姓名 → 查 Twenty CRM → 拉相关 context
    - 含图片 → 调 multimodal-looker（via LiteLLM）
    - 含 op-task 关键词 → 写 op-tasks.md
    - 外贸意图 → 创建 CRM opportunity

- [ ] **[CC-P2.3] Letta 实体关联写入**
  - 每次 /intake 处理后，调 letta_store 存储：
    - `"[日期] [实体1] ←→ [实体2] 关系类型：context"`
    - tags: intake-graph, entity-link
  - 下次 /intake 提到相关实体时，letta_search 拉出关联

### 期三：知识图谱可视化（[CC] 执行）

- [ ] **[CC-P3.1] 3000 添加"关联图谱" Tab**
  - 使用 react-force-graph 或 vis.js
  - 数据来源：Letta archival（带 entity-link tag 的记录）+ Twenty CRM contacts
  - 节点类型：人/公司/任务/消息/文件（不同颜色）
  - 点击节点 → 右侧面板显示详情 + 关联 context

- [ ] **[CC-P3.2] 微信联系人 → CRM 自动建图**
  - wechat-agent 每次 upsert_contact 后，同时调 Letta 写关系
  - 格式：`联系人X 在微信群Y 发送了 外贸意图 消息，公司Z`

### 期四：习惯学习（[OP] 定时）

- [ ] **[OP-P4.1] 用户行为模式追踪**
  - 每次 /intake 请求追加日志到 `~/.local/share/ai-learning/intake-patterns.jsonl`
  - 格式：`{"time": "HH:MM", "type": "image|text|file", "intent": "...", "action_taken": "..."}`
  - 每周日 12:00 OP 运行分析：最高频意图 top3 → 建议新 skill

- [ ] **[OP-P4.2] 主动推送（晨报）**
  - 每天 09:00 OP 执行：读取昨日微信未回复消息 + 今日 op-tasks
  - 生成中文简报 → notify-send + 写 ~/Desktop/巡检报告/晨报-YYYY-MM-DD.md

