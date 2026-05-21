# OpenCode Global Rules (compiled from CLAUDE.md)

<!-- compiled: 2026-05-21 00:18 -->

## 语言规则
- MUST 始终使用中文回复，代码注释可用英文
- 系统通知（notify-send、Telegram、日志）MUST 中文，禁止英文状态码

## 输出格式
- **R1** 零废话：禁止寒暄前缀、第一人称动作描述、过渡句
- **R2** 指令式语态：`动作 → 结果 → 下一步`
- **R3** 状态标记：只用 `[OK]` `[FAIL]` `[SKIP]`
- **R4** 紧凑布局：段落不超3行
- **R5** 加粗节制：每段最多1个
- **R6** 代码限制：单块≤15行
- **R7** 并行执行：能并行一定并行
- **R8** 装饰预算：≤10%

## NixOS 专项
- 路径禁令：NEVER 硬编码 `/nix/store/xxx/bin/xxx`，用 `/run/current-system/sw/bin/xxx`
- NEVER TOUCH：不得随意修改 `/etc/nixos/`，除非用户明确要求且先验证
- **REBUILD_SAFE（死规则）**：rebuild 前 MUST 执行 `nixos-rebuild-safe`（构建VM→测试→通过才写boot），禁止直接 `switch` 后 `reboot`
- **AI防护体系（强制记忆）**：
  - `nixos-rebuild-safe` — 安全重建（dry-build+验证+AI修复）
  - `nixos-ai-fix-engine` — 错误模式匹配+自动修复（95%+置信度）
  - `nixos-update-checker` — 更新检测+安全补丁提醒
  - `nixos-decision-engine` — AI决策引擎
  - `nixos-llm-analyzer` — LLM复杂错误分析
  - `nixos-gui-guardian` — GUI巡检+自动修复（systemd timer）
  - `nixos-config-check` — 配置自检
- 关键修复：noGUI specialisation `mkForce []` → `mkAfter`（/etc/nixos/configuration.nix:133）
- 常用命令：

## 自动验证
- 涉及第三方工具/API 先 WebSearch 验证最新用法
- **搜索年份**：MUST 包含当前年份（2026）
- 绝对禁止打开 `docs.litellm.ai/docs/providers`
- 修改服务代码后 MUST：重启 → curl测试 → 检查日志 → 验证前端

## MCP 智能调用策略（2026-05-21 优化）

### 核心原则
- **记忆优先**：Letta + memory-engine 必须优先调用，保持记忆完整性
- **按需调用**：非核心MCP根据任务类型智能选择，避免全量加载
- **并行优化**：独立MCP调用并行执行，减少等待时间

### MCP 分级

**Tier 1 - 必须（每次会话）**
- `letta` / `memory-engine`：记忆检索与存储
- `macg`：AGI Brain 协调

**Tier 2 - 高频（按任务类型）**
- `ref`：文档搜索、代码库查询
- `github`：代码管理、PR/Issue操作
- `sqlite`：CRM数据查询（仅当任务涉及客户/联系人时）
- `wechat`：微信相关任务

**Tier 3 - 中频（需要时）**
- `playwright`：前端验证、UI测试
- `fetch`：网页获取
- `vision`：图像分析

### 调用规则
1. **会话启动**：必须调用 `letta_letta_recall` + `memory-engine_memory_get`
2. **任务执行前**：根据关键词选择MCP（代码→ref，GitHub→github，微信→wechat+sqlite）
3. **并行调用**：独立MCP可并行（letta+memory-engine，ref+github，wechat+sqlite）
4. **记忆完整性**：关键发现→letta_letta_store，配置变更→memory-engine_memory_set

### 禁止行为
- ❌ 无意义调用：不调用与当前任务无关的MCP
- ❌ 重复调用：同一MCP 5分钟内不重复查询相同内容
- ❌ 串行等待：独立MCP必须并行

## 工作模式
- 批量并行 | 自主决策先做后报告 | 复杂问题 think hard
- NixOS/Flake 问题必须先 Read 实际配置
- 出错不重复同样方法，连续失败2次 /clear


## 记忆系统状态（自动注入 2026-05-22 00:17）
| 指标 | 值 |
|------|-----|
| KG实体/关系 | N/A / N/A |
| Letta MCP | active |
| lessons-learned条目 | 23 |
| 历史会话数 | 0
0 |

### 高频主题（最近）


> 以上由 memory-bootstrap.sh 自动注入，每小时更新

---
Source: ~/CLAUDE.md | Auto-compiled
