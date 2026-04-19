# 跨会话待办

<!-- 清理日期: 2026-04-17 — 删除所有 [x] 已完成条目，只保留未完成任务 -->

## 高优先

- [ ] **全模型幻觉防护系统（P1）** — 覆盖所有 AI 模型（GLM/DeepSeek/Sonnet/Opus/Haiku）
  - **触发**：GLM 声称 OpenCode 已停止开发（幻觉）
  - 方案 A：AGENTS.md 加「工具现状速查表」（名称/版本/状态/验证命令）
  - 方案 B：op-tasks 执行前强制 shell 验证关键工具状态（不信 LLM 口头声明）
  - 方案 C：不确定工具状态时强制 WebSearch 验证（不走记忆/训练数据）
  - 方案 D：加入「知识截止声明」提示词：模型说新工具状态时必须标注 [需验证]
  - 优先实施 B+C，成本最低效果最直接

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
- [ ] **微信管理平台开发** — CLI + Web UI + PostgreSQL + 连接 OpenCode
- [ ] **Agent 知识库可视化方案设计**

## 架构缺陷修复（2026-04-17 审计）

- [ ] **op-tasks 已完成归档** — 定期 archive >24h 的 [x] 条目，保持活跃文件精简
- [ ] **chronos-subconscious 降频** — 从 20min 改为 1h，加 CPU idle 条件
- [ ] **PYTHONPATH 全局设置** — 统一 python3.13/3.12 或设全局 site-packages 路径

## 系统维护

- [ ] **成本审计服务修复（P1）** — 修复 LiteLLM 和 Ollama 不可用问题
  - [ ] 检查 LiteLLM 日志：`docker logs litellm --tail 100 | grep -i error`
  - [ ] 重启 LiteLLM：`docker restart litellm`
  - [ ] 启动 Ollama：`systemctl start ollama` 或 Docker 运行
  - [ ] 验证服务健康：`curl -sf http://localhost:4000/health` 和 `curl -sf http://localhost:11434/api/tags`
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
