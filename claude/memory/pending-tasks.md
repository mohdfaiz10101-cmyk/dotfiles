# 跨会话待办

<!-- 清理日期: 2026-04-24 — 删除7个已实现条目（TopBar健康灯/对话室/UniversalBar/GraphPanel/firewall/Paperclip归档/chronos降频） -->

## 2026 AGI 技术吸收（2026-04-21 派发 OP，今日执行）
- [ ] **[OP] n8n AI Nodes** → 文字触发工作流（接 Hub API）
- [ ] **[CC] OODA Loop** → OP执行框架改造
- [ ] **[CC] /intake 多意图** → iCARE分解+并行路由
- [ ] **[CC] Mem0三温** → memory_controller.py Hot/Warm/Cold
- [ ] **[CC] MAGMA tag** → Letta archival多维标签
- [ ] **[OP] Qwen3.5-Omni** → 语音/多模态输入部署
- [ ] **[CC] GLM-4.6V /intake** → 图片→意图→执行
- [ ] **[OP] MetaAgent** → 工具自发现→Tool RAG自动注册
- [ ] **[CC] AdaptOrch** → Claude Router动态路由升级
- [ ] **[CC] AFlow /api/plan-task** → MCTS多方案规划
- 详细规划见：`memory/ideas-roadmap.md` + `~/op-tasks.md`

## 高优先

### 3000 控制台升级路线图（[Sonnet] 2026-04-21）
- [x] ~~**P1** TopBar 服务健康灯~~ — 已实现（TopBar.tsx `/api/health-status`）
- [x] ~~**P1** Projects 里程碑改为 JSON 配置文件~~ — 已实现（projects.json + route.ts 读取）
- [x] ~~**P2** 通知中心~~  — 已实现（TopBar OP badge + 服务健康灯，HTTP检查覆盖Docker异常）
- [ ] **P3** Cmd+K 全局搜索跨面板

- [x] ~~**全模型幻觉防护系统（P1）**~~ — B+C 已实现：Rule B写入AGENTS.md，Rule C已在CLAUDE.md

- [ ] **Docker data-root 迁移到 POOL-D1**（[Sonnet] 2026-04-21）
  - 目标：`/mnt/pool-disks/POOL-D1/docker`（ext4, 617G 可用）
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

- [ ] **微信 Windows 端密钥提取** — 需在 Windows 运行 pywxdump 或 wechat-auto-decrypt.ps1
   - Windows DB: /mnt/data/WeChat Files/w422417869/Msg/（79 个加密文件）
   - 提取密钥后可用 wechat-finance 工具解密
   - 阻塞原因：等待用户在 Windows 端手动执行
- [ ] **微信管理平台开发** — CLI + Web UI + PostgreSQL + 连接 OpenCode
- [ ] **Agent 知识库可视化方案设计**

## 架构缺陷修复

- [x] ~~**op-tasks 已完成归档**~~ — 已执行（2026-04-24，归档231条，720行→477行）
- [ ] **PYTHONPATH 全局设置** — 统一 python3.13/3.12 或设全局 site-packages 路径

## 系统维护

- [ ] **成本审计服务修复（P1）** — LiteLLM 运行正常，Ollama 待启动
   - [ ] 启动 Ollama：`systemctl start ollama` 或 Docker 运行（当前不可达）
   - [ ] 配置成本告警通知（Telegram + notify-send）
   - [ ] 添加服务健康监控（systemd + 定时检查）
- [ ] **NixOS nixpkgs 更新** — `nix flake update nixpkgs --flake /etc/nixos` + rebuild（锁定 2026-04-09）
- [ ] **P0 Git 远程 origin** — 等用户提供远程仓库地址

## 开发项目

- [ ] **Sourcing 采购网站完善** — `~/projects/projects/sourcing-site/`（Astro 5 + Tailwind 4，端口 4322）
  - 现状：有 about/blog/contact/products/services 页面 + Footer/Nav 组件，API 端点待补充
  - 需要：连接 LiteLLM 替代 HyperChat、产品 CRUD API、完善各页面内容
- [ ] **Claude Code 风格宠物** — usik/tamagotchi Phase 2，AI Agent 互动插件
- [ ] **配置 DeepSeek 训练环境** — 安装 PyTorch 或配置 Docker 容器

## 低优先 / 待确认

- [ ] 系统健康监控优化（调整 system-health-monitor 避免误报）
- [ ] [ORCH→CC] [2026-04-17 17:52] 设计移动端专用状态卡片视图

## 微信人格模拟（P2）
- 从微信历史提取用户对话风格 → 训练/few-shot 人格模型
- 实现路径：wechat_merged DB → 提取用户消息 → 构建 few-shot prompt → 注入 GLM system prompt
- 输出：预测用户下一步走向，显示在 3000 dashboard 右侧面板

## 统一智能体系 — Universal AI Intake（P1，进行中）

> 目标：一个对话窗口（port 3000）自动识别任何输入 → 路由 → 执行 → 存档
> 现状（2026-04-24 更新）：
> - UniversalBar.tsx 已存在，GraphPanel.tsx 已存在，DialoguePanel.tsx 已存在
> - hub-api /intake 端点待确认；Letta 实体关联写入待实现
> - wechat-agent CRM 自动写入未验证

### 期一：修通微信 Agent（[OP] 可立即执行）

- [ ] **[OP-P1.1] 验证 UOS WeChat 消息读取**
  - 运行：`DRY_RUN=1 timeout 40 python3 ~/agi/wechat_agent.py 2>&1 | tee /tmp/wechat-dryrun.log`
  - 检查 /tmp/wechat-dryrun.log 是否有"本轮新消息 N 条"
  - 若无消息：检查 `ls ~/.cache/wechat-finance/decrypted/` 是否有解密 DB
  - 报告结果到 op-task-results.json

- [ ] **[OP-P1.2] 修复 Wine WeChat DB 解密**
  - Wine DB 路径：`/mnt/data/WeChat Files/w422417869/Msg/ChatMsg.db`
  - 检查 `~/.cache/wechat-finance/keys.json` 是否包含 wine 账号密钥
  - 若无：SSH Windows 运行密钥提取

- [ ] **[OP-P1.3] 修通 CRM 自动写入**
  - CRM DB 不存在，需先创建表再验证 poll 写入
  - 成功条件：contacts 表有新增记录

- [ ] **[OP-P1.4] 微信群消息分类管道**
  - 检查 wechat_agent.py 是否有 TRADE/CUSTOMER/GROUP 分类
  - 外贸意图触发自动在 Twenty CRM 创建 opportunity

### 期二：Universal Intake 串联（[CC] 执行）

- [x] ~~**[CC-P2.1] UniversalBar 组件**~~ — 已存在
- [x] ~~**[CC-P2.2] hub-api.py /intake 端点**~~ — 已实现（实体提取+对话室广播）
- [x] ~~**[CC-P2.3] Letta 实体关联写入**~~ — 已实现（2026-04-24）

### 期三：知识图谱可视化（[CC] 执行）

- [x] ~~**[CC-P3.1] GraphPanel 组件**~~ — 已实现
- [ ] **[CC-P3.2] 微信联系人 → CRM 自动建图**

### 期四：习惯学习（[OP] 定时）

- [ ] **[OP-P4.1] 用户行为模式追踪** — intake日志 + 每周日12:00分析top3意图
- [ ] **[OP-P4.2] 主动推送（晨报）** — 每天09:00微信未回复+op-tasks简报

## Windows 微信兼容性修复（2026-04-22）

- [ ] **[待定-长期] Win 微信 WeChatFerry 兼容性**
  - 根因：WeChatFerry 只支持 3.9.x，当前 Windows 是微信 4.x
  - 当前状态：暂缓，使用 UOS Linux 微信替代
- [ ] [OP→CC] [2026-04-24 23:07] Happy稳定性修复+OpenCode压缩: 1.sudo ln -sf /home/charlie/CLAUDE.md /CLAUDE.md 2.sudo ln -sf /home/charlie/.claude /.claude 3.happy-daemon.service ExecStart改为绝对路径/mnt/pool-disks/POOL-D1/home-offload/.npm-global/bin/happy daemon start-sync 然后 systemctl --user daemon-reload && systemctl --user restart happy-daemon 4.oh-my-openagent.jsonc加preemptive_compaction:true
- [ ] [OP→CC] [2026-04-24 23:17] 紧急：sudo setuid 位全部丢失，整个系统无任何 setuid root 二进制。需要用户手动在物理终端执行：su root → nixos-rebuild switch。或者如果有 TTY 登录权限，请在终端中执行 nixos-rebuild switch。之后再执行：sudo ln -sf /home/charlie/CLAUDE.md /CLAUDE.md && sudo ln -sf /home/charlie/.claude /.claude。平板 Termux 安装需要用 adb install-multiple 而非 pm install-create。
