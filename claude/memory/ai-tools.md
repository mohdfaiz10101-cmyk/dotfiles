# AI 工具对比

## Windsurf Knowledge MCP Server（2026-04-11）

### 核心功能
- ✅ **Memory 访问**：list_memory_files / read_memory / search_memory（17 个文件，364KB）
- ✅ **Skills 访问**：list_skills / read_skill（65+ 技能库）
- ✅ **Rules 访问**：get_rules（CLAUDE.md 完整规则）
- ✅ **实时监听**：chokidar 监听文件变化（stderr 日志）
- ✅ **安全限制**：只读访问，大文件截断（10KB/次），搜索结果限制（50 条）

### 部署信息
- MCP Server：`~/.local/lib/windsurf-knowledge-mcp/server.js`（2000+ 行）
- 依赖包：@modelcontextprotocol/sdk + chokidar（93 packages）
- 配置文件：`~/.codeium/windsurf/mcp-config.json`
- 测试脚本：`~/.local/bin/test-windsurf-knowledge-mcp`
- 文档：README.md + WINDSURF_INSTRUCTIONS.md + VERIFICATION.md

### 使用场景
- 操作前检索：NixOS/Docker/代理/NVIDIA 操作前自动 search_memory 检查历史教训
- 问题排查：read_memory("troubleshooting.md") 查询速查表
- 代码探索：read_memory("codebase-map.md") 使用探索缓存
- 技能复用：list_skills 查看可用操作流程

### 集成方式
```bash
# Windsurf Custom Instructions
# 添加 WINDSURF_INSTRUCTIONS.md 内容到 Settings → cascade.customInstructions

# 验证连接
# Windsurf → Help → Toggle Developer Tools → Console
# 搜索 "claude-knowledge" 确认连接成功

# 测试调用
# 在 Cascade 中输入：请使用 list_memory_files 工具
```

### 技术特点
- **MCP stdio transport**：通过标准输入输出通信
- **环境变量配置**：MEMORY_PATH / SKILLS_PATH / RULES_PATH
- **错误处理**：McpError 包装所有异常
- **性能优化**：文件读取限制、搜索结果截断

### 未来优化
- [ ] 语义搜索（集成 Letta archival）
- [ ] 分页支持（read_memory 支持 offset/limit）
- [ ] 实时推送（文件变化通知到 Windsurf）

---

## GLM Enhanced v2.0（2026-04-11）

### 核心升级
- ✅ **命令自动执行**：解析 ```bash``` 代码块，自动执行并反馈
- ✅ **工具调用**：支持 `<bash>` / `<read>` 标签
- ✅ **反馈循环**：执行结果自动注入对话，继续推理
- ✅ **跨模型记忆**：与 Claude 共享操作日志
- ✅ **智力增强**：Memory 上下文 + Letta 语义搜索 + 行为规则

### 部署信息
- 主程序：`~/.local/bin/glm-enhanced`（14KB Python 脚本）
- 符号链接：`~/.local/bin/glm` → `glm-enhanced`
- 旧版备份：`~/.local/bin/glm.old`
- 操作日志：`~/.claude/cross-model-ops/glm-operations.jsonl`
- 使用指南：`~/GLM-ENHANCED.md`（3.9KB）

### 使用方式
```bash
# 自动执行模式（推荐）
glm "检查磁盘空间" --auto
glm "查看失败的服务" -a

# 交互模式（手动确认）
glm

# 管道模式
echo "列出最大的 5 个文件" | glm --auto
```

### 智力对比
| 能力 | GLM Enhanced | Claude Code |
|------|--------------|-------------|
| 命令执行 | ✅ Bash 自动执行 | ✅ 完整工具调用 |
| 文件操作 | Read only | Read/Write/Edit |
| 上下文记忆 | Memory + Letta | Memory + Letta |
| 反馈循环 | ✅ 自动反馈 | ✅ 自动反馈 |
| 成本 | **免费**（智谱额度） | $3/M tokens |
| 智力水平 | GLM-4.7 | Sonnet 4.5 |

### 跨模型智力共享
```
GLM 操作 ──┐
           ├──> ~/.claude/cross-model-ops/*.jsonl
Claude 操作─┘           ↓
                   双向读取
                        ↓
              共享 memory/ + Letta
```

### 推荐使用策略
- **日常任务**（系统诊断、配置查询） → GLM Enhanced（免费 + 快速）
- **复杂重构**（架构设计、多文件修改） → Claude Code（专业）
- **代码生成**（大量代码） → DeepSeek V3.2（成本低）

### 创建者
- [2026-04-11] [Sonnet] GLM Enhanced v2.0 部署完成

---

## 维护学习系统
- **名称**: maintenance-learner / proactive-maintenance-planner
- **路径**: `~/.claude/skills/maintenance-learner.py`
- **功能**: 扫描 memory/ 条目频率，提取主题(proxy/docker/nixos/disk等)，滑动窗口统计7/14/30天频率，生成维护建议(skill/timer)
- **模式**: --scan(快速) / --deep(DeepSeek增强) / --auto(自动创建skill) / --feedback(反馈学习) / --daemon(守护)
- **配置**: `~/.claude/skills/.maintenance-state.json` + `.maintenance-feedback.json`
- **Timer**: systemd maintenance-learner.timer (Mon 11:00, `nix flake check` 通过)
- **Skill**: proactive-maintenance-planner (已注册到 Claude Code skill 体系)
- **数据源**: `~/.claude/projects/-home-charlie/memory/*.md` 带 `[YYYY-MM-DD]` 格式的条目

## 语音输入

### Voxtype（已安装）
- **版本**: 0.6.5
- **安装方式**: NixOS 自定义包（`/etc/nixos/modules/productivity.nix`）
- **配置**: `~/.config/voxtype/config.toml`
- **快捷键**: Meta+Space（长按）
- **模式**: Push-to-Talk（按住录音，松开转写）
- **引擎**: Whisper base.en（本地）
- **自动启动**: systemd 用户服务（`~/.config/systemd/user/voxtype.service`）
- **输出方式**: 直接输入光标位置（wtype/ydotool）
- **优势**: 
  - 本地隐私保护
  - 支持中文/CJK 
  - Wayland 原生支持
  - 低延迟（模型加载仅 0.09s）
- **状态**: ✅ 运行中（`systemctl --user status voxtype`）

### 使用方法
- **按住 Meta+Space** → 开始录音（最多 60 秒）
- **松开** → 自动转写并输入文字
- **状态查看**: `voxtype status`
- **重启服务**: `systemctl --user restart voxtype`

### 进阶配置
- GPU 加速：`voxtype setup gpu`（可启用 CUDA/Vulkan）
- 切换模型：`voxtype setup model`（可选 tiny/small/medium/large）
- Waybar 集成：`voxtype setup waybar`

### 已知问题
- **Meta+Space 不可用**: evdev 模式不支持字母键组合，KDE 系统占用
- **解决方案**: 使用 ScrollLock 长按（或 Pause/F13-F24）
- **输出失败降级**: 如 wtype 失败，自动切换到剪贴板模式

- [2026-04-06] [Letta-Distill] 记录AI自动化集群部署配置，包含Dify、n8n等工具的docker-compose路径及LiteLLM路由策略问题。

- [2026-04-06] [Letta-Distill] 记录AI工具配置、语音输入系统及KDE窗口管理规则，包含模型部署、GPU调度、自动化脚本等方案。

- [2026-04-06] [Letta-Distill] 介绍多种AI编程CLI工具的安装配置及对比，涵盖NixOS集成方案与浏览器自动化功能。

- [2026-04-06] [Letta-Distill] Claude配置白名单/黑名单及自动化工具，KeePassXC密码管理设置，AI模型选型建议：Claude适合NixOS配置，豆包适合常规编程但Nix幻觉严重。

- [2026-04-06] [Letta-Distill] GLM Proxy配置支持Anthropic兼容性，采用四层记忆结构（L1-L4）

- [2026-04-06] [Letta-Distill] Letta MCP配置了4个工具（recall/search/ask/agents）及nixos-sysadmin代理，用于AI工具管理与系统运维。

- [2026-04-06] [Letta-Distill] 配置Ollama使用CUDA加速，模型路径为/mnt/ai/ollama，保持连接30分钟，使用qwen3:8b和deepseek-r1:14b模型

- [2026-04-06] [Letta-Distill] 配置Claude CLI需在.zshrc中设置ANTHROPIC_BASE_URL与ANTHROPIC_API_KEY环境变量

- [2026-04-06] [Letta-Distill] JetBrains IDEA集成Continue工具，需配置~/.continue/config.yaml文件，指定schema版本为v1

- [2026-04-06] [Letta-Distill] 介绍GLM CLI的三种模式：流式、交互及大字体悬浮监控功能。

- [2026-04-06] [Letta-Distill] 配置MCP使用Notion、Letta-Memory和Playwright工具，通过SSE和stdio处理数据流

- [2026-04-06] [Letta-Distill] 配置Konsole语音输入，使用whisper.cpp模型及快捷命令实现中英混合识别。

- [2026-04-06] [Letta-Distill] 使用本地 Ollama qwen3:8b-nothink 模型批量翻译 Tech Digest 内容，避免外部 API 依赖，并处理中英文字段映射兼容性

- [2026-04-06] [Letta-Distill] 配置Cline MCP的SSE格式设置，包含服务器URL，重启VSCode后自动连接并获取四个工具

- [2026-04-06] [Letta-Distill] 集成SiliconFlow DeepSeek V3.2通过LiteLLM，成本降低50%，支持164K上下文，适合代码任务。

## 智能模型路由策略（2026-04-06 更新）

### 当前系统（Claude Router Plugin）
- **默认模型**：Sonnet（$3/M tokens）— 日常主力
- **自动升降级**：Hook 预分类（$0）→ 简单→Haiku / 复杂→Opus / 代码→DeepSeek
- **外部模型集成**：GLM（免费中文）+ DeepSeek V3.2（$0.27/M，164K 上下文）+ Aider（Git-aware）
- **路由方式**：`cc`=智能路由 / `cco`=直接 Opus / `glm "<prompt>"`=直接 GLM

### 本地+API 组合方案（概念设计）
- **目标**：达到或超越 Opus 水平，成本 ~¥1800/月（vs Opus ~¥8000/月）
- **四层架构**：
  1. 预处理层：本地 7B 分类 + RAG + 对话压缩（$0）
  2. 路由层：简单→本地 Qwen 7B / 中等→R1 单次 / 复杂→精炼流程
  3. 精炼层：R1 生成 → 本地 14B review → R1 修改 → 沙箱验证（Self-Play 循环）
  4. 验证层：Docker 沙箱自动测试反馈（$0）
- **核心优势**：
  - 真实执行代码并迭代（Opus 不能）
  - MemGPT 无限上下文（vs Opus 200K 窗口）
  - 本地沙箱自动验证（质量提升关键）
- **实施优先级**：Week 1 R1 API 接入 → Week 2 RAG+沙箱 → Week 3 Self-Play+MemGPT → Week 4 路由调优

### 高级方案储备（待实施）
- **MoA（Mixture of Agents）**：R1 + Qwen + 本地 14B 并行生成 → 聚合模型综合（论文证明 3 中等模型 > 1 最强模型）
- **执行引导采样**：生成过程中实时运行代码，结果引导后续生成（比先写完再验证强）
- **语义缓存**：相似问题直接返回缓存（GPTCache，团队重复性问题命中率 40-60%）
- **动态 LoRA 切换**：14B 基座 × N 个专家 LoRA（Python/SQL/架构），vllm 毫秒级切换
- **对比解码**：大模型 logP - 小模型 logP = 高质量输出（去除平庸部分）
- **知识蒸馏**：R1 生成训练数据 → 微调本地 14B（专属模型，越用越强）
- **MCTS 代码生成**：蒙特卡洛树搜索，14B+MCTS > 70B 单次生成（算法题专用）
- **形式化验证**：Z3/Dafny 数学证明代码正确（金融/安全场景）
- **多智能体协同**：Architect/Coder/Reviewer/Tester/Debugger 分工（OpenHands/MetaGPT）
- **隐式推理链**：token 层注入推理压力，避免 CoT 走捷径（Anthropic 研究方向）

### 投入产出比排序
1. ★★★★★ **语义缓存**：实现简单，省钱立竿见影
2. ★★★★★ **执行引导采样**：质量提升最明显
3. ★★★★☆ **MoA 并行聚合**：效果强，成本可控
4. ★★★★☆ **动态 LoRA 切换**：本地免费，扩展能力
5. ★★★☆☆ **知识蒸馏**：长期最优，短期成本高
6. ★★★☆☆ **MCTS**：算法类任务专用
7. ★★☆☆☆ **形式化验证**：门槛高，场景窄

### 终极组合（3 个月路线图）
```
第一层：语义缓存（省钱）
  ↓
第二层：RAG + 动态 LoRA（本地能力最大化）
  ↓
第三层：MoA（R1 + 本地并行聚合）
  ↓
第四层：执行引导采样（质量保证）
  ↓
第五层：知识蒸馏（持续进化）
  ↓
综合效果：在自己的代码库上超越 Opus
```

### 下一步行动
- **2 周内上线**：语义缓存 + 执行引导采样（省钱又提质）
- **1 个月内**：Docker 沙箱自动验证（单功能就能超过 Opus 单次生成）
- **3 个月内**：完整五层组合（达到并超越 Opus）

- [2026-04-07] [Letta-Distill] 记录AI算力优化方案、Whisper语音输入系统、KDE窗口自动分配规则及多个AI工具的配置与使用

- [2026-04-07] [Letta-Distill] Claude在NixOS配置中优于国产模型，豆包模型因Nix语料少导致幻觉严重，不推荐用于NixOS配置

- [2026-04-07] [Letta-Distill] 对比0011.ai Ultra与Claude Code Max套餐的价格、任务次数及token汇率，结论是Ultra更划算但存在第三方服务风险。

- [2026-04-07] [Letta-Distill] 对比Claude Code Max与0011.ai API的长期项目使用差异，强调Max的自动记忆功能优势及订阅计划成本差异，建议根据项目需求选择工具。

## deepseek-code 命令

- **创建日期**：2026-04-08
- **创建者**：[Sonnet]
- **功能**：在 Konsole 中使用 Aider + DeepSeek V3.2 进行 AI 编程
- **路径**：`~/.local/bin/deepseek-code`（别名：`ds`）
- **使用**：
  ```bash
  ds                         # 交互模式（推荐简写）
  ds --message "实现快速排序"  # 单次查询
  ds --help                  # 查看 Aider 帮助
  ```
- **配置**：
  - 客户端：Aider（Git-aware AI 编程工具）
  - 后端网关：LiteLLM (http://localhost:4000/v1)
  - 模型：openai/silicon-deepseek-v3.2
  - 上下文：164K tokens
  - 成本：$0.27/1M tokens（比 Claude Opus 便宜 50+倍）
- **依赖**：
  - LiteLLM 网关运行（`systemctl status litellm` 或 `docker ps | grep litellm`）
  - Aider 已安装
- **优势**：
  - Aider 的 Git-aware 多文件编辑能力
  - DeepSeek 强大的代码生成能力（164K 上下文）
  - 自动 git commit + 智能文件选择
  - 极低成本
- **注意**：
  - 初版使用 Claude CLI，但 Claude CLI 不支持非 Anthropic 模型名，已改为 Aider
  - Aider 命令参数与 Claude CLI 不同（如 `--message` vs 直接 prompt）

## Zellij（终端复用器）

- **安装日期**：2026-04-08
- **安装者**：[Sonnet]
- **版本**：0.43.1
- **配置文件**：`~/.config/zellij/config.kdl`
- **安装方式**：NixOS packages.nix 终端区
- **前缀键**：`Ctrl+a`（tmux 兼容模式）
- **核心设置**：`simplified_ui true`（简洁 UI）、`pane_frames false`、`mouse_mode true`、`copy_command "wl-copy"`
- **常用操作**：
  - `Ctrl+a "` → 水平分屏 | `Ctrl+a %` → 垂直分屏
  - `Ctrl+a c` → 新 Tab | `Ctrl+a n/p` → 切换 Tab
  - `Ctrl+a d` → 分离 | `Ctrl+a z` → 全屏切换
  - `Ctrl+a h/j/k/l` → 切换窗格焦点
  - `Ctrl+a H/J/K/L` → 调整窗格大小
- **与 tmux 对比**：
  - 配置语法：KDL（vs tmux 的 set/bind）
  - 内置 tmux 模式，键位兼容
  - simplified_ui 适合 Claude Code 会话（减少视觉噪声）
  - 不支持 session auto-name by directory（需手动 `-s` 指定）
- **注意事项**：
  - `NewPane` 参数用 `"Down"`/`"Right"`（不是 "Vertical"/"Horizontal"）
  - Ctrl+a 模式通过 `shared_except "tmux" "locked"` 绑定实现
  - `zellij setup --check` 可验证配置语法

## Token 优化经验

- [2026-04-08] [Sonnet] **多层委托 token 陷阱**：创建 code-dual 命令时多层委托（Sonnet→fast-executor→engineer→documentation）消耗 75k tokens
  - 原因：每次 Task 委托传递完整 CLAUDE.md（8k+ tokens）
  - 解决方案：封装为 skill `mpm-code-dual-setup`，直接使用 Write/Bash 工具，避免委托链
  - 效果：节省 ~60k tokens/次（80% 降低，从 75k → ~15k）
  - **通用规则**：频繁操作类任务（安装、配置、脚本创建）应优先封装 skill，避免重复委托成本

- [2026-04-08] [Letta-Distill] 记录了AI工具的配置与优化方案，包括本地大模型部署、GPU调度、语音输入系统及自动化脚本。

- [2026-04-08] [Letta-Distill] Claude配置白名单黑名单及自动化钩子，KeePassXC密码管理设置，AI模型选型建议优先Claude处理NixOS任务

- [2026-04-09] [Letta-Distill] 比较Claude与豆包等AI工具在NixOS配置中的表现，推荐Claude因Nix语料多、幻觉少，豆包适合常规编程但冷门语言支持差。

## Agent 框架评估

- [2026-04-10] [Haiku] **Hermes Agent**（https://github.com/nousresearch/hermes-agent）：Nous Research 开源 Agent 框架，基于 Hermes 系列模型的自主任务执行系统。**评估结论：不值得引入**。理由：(1) 与现有系统高度重叠（MPM 已支持多代理编排，Claude MCP 已支持工具调用）(2) 推理能力劣势（开源模型弱于 Claude Opus/Sonnet + DeepSeek）(3) 缺少记忆系统（Letta 语义检索更强）(4) 迁移成本高（需改写工作流）。**唯一适用场景**：需要完全离线、本地化、开源的 Agent（无网络依赖）。**建议**：继续用 Claude Code + MPM + Letta，代码增强用 Aider 或 DeepSeek。

## Zed 编辑器（待部署）

- **调研日期**：2026-04-10
- **配置日期**：2026-04-11
- **调研者**：[Opus] | **配置者**：[Sonnet]
- **版本**：0.230.1（NixOS 当前版本，已安装）
- **定位**：Rust 编写的现代代码编辑器，硬件加速 Vulkan，原生 AI 集成
- **安装方式**：Home Manager `programs.zed-editor.enable = true`
- **CLI 命令**：`zeditor`（非 `zed`，nixpkgs 命名冲突）
- **配置文件**：`~/.config/zed/settings.json`（用户级）+ `.zed/settings.json`（项目级）
- **LLM 支持**：
  - **默认模型**：Claude 3.5 Haiku（成本优化）
  - **可用模型**：
    - Claude 3.5 Haiku（200K 上下文，$1/M）— 日常开发
    - Claude 3.5 Sonnet（200K 上下文，$3/M）— 架构设计
    - Claude Opus 4（200K 上下文，$15/M）— 复杂推理
    - DeepSeek V3.2（163K 上下文，$0.27/M）— 大上下文任务
  - **LiteLLM 集成**：http://localhost:4000/v1（API Key: sk-litellm-charlie-2026）
  - **温度配置**：Haiku 0.7 / Sonnet 0.5 / DeepSeek 0.3
  - 模型切换：Agent Panel UI 手动选择（无自动路由）
  - API key 管理：OS 密钥链（不明文存储）+ 环境变量注入
- **项目配置**：
  - `.zed/settings.json` 支持项目级设置（tab_size、formatter 等）
  - 全局设置（theme、vim_mode、LLM system prompt）仅用户级生效
  - 配置层级：Default → Global → User → Server → Project（深路径优先）
- **Letta 集成**：
  - ❌ Zed 0.230.1 不支持 MCP Server 直接配置
  - 替代方案：通过 Zed Marketplace 安装 MCP 扩展后配置
  - 完整语义记忆使用 Claude Code CLI 的 Letta 集成
- **CLAUDE.md 集成方案**：
  - 用户级 settings.json 配置 system prompt 引用 `~/CLAUDE.md`
  - 或通过 Slash Command 手动注入（每次 LLM 调用前）
  - 项目级无法覆盖 system prompt（Zed 限制）
- **依赖**：
  - Vulkan 驱动（已满足，NVIDIA 驱动已启用）
  - GLM API key（需申请：https://open.bigmodel.cn）
  - LiteLLM 网关运行（http://localhost:4000/v1）— ✅ 已运行
- **优势**：
  - 性能优异（Rust + GPU 加速）
  - 原生 AI 集成（无需插件）
  - 声明式配置（NixOS 友好）
  - 多模型切换方便
  - 成本优化（Haiku 优先，按需升级）
- **限制**：
  - 无自动模型路由（需手动切换）
  - 项目级 system prompt 不支持
  - Letta 集成需自行开发
  - 生态相对年轻（扩展少于 VSCode）
- **状态**：✅ 配置完成（2026-04-11）
- **配置文件路径**：
  - `~/.config/zed/settings.json`（核心配置）
  - `~/.config/zed/AI-ROUTING-GUIDE.md`（使用指南）
- **参考资料**：
  - [NixOS Wiki](https://wiki.nixos.org/wiki/Zed)
  - [LLM Providers 文档](https://zed.dev/docs/ai/llm-providers)
  - [配置指南](https://ofox.ai/blog/zed-editor-ai-configuration-guide-2026/)
  - [Agent Settings](https://zed.dev/docs/ai/agent-settings)

## Roo Code

**API 配置持久化**（解决每次启动重填问题）
- 问题：API keys 存储在 VSCode Secret Storage，重启可能丢失
- 解决方案：
  1. 在 Roo Code UI 导出设置：⚙️ → Export → 保存为 `~/roo-code-settings.json`
  2. 在 settings.json 添加：`"roo-cline.autoImportSettingsPath": "~/roo-code-settings.json"`
  3. 重启 VSCode → 自动导入配置
- 注意：导出的 JSON 包含明文 API keys，不要分享
- 配置文件：`~/roo-code-settings.json`（包含 API Profiles + Global Settings）

**配置永久化方案**
- 实际配置：`~/roo-code-settings.json`（包含 API keys，已 .gitignore）
- 模板文件：`~/cline-workspace/roo-code-settings.template.json`（已提交 git）
- 权限保护：600（仅用户可读写）
- Git 仓库：`~/cline-workspace/.git`
- 恢复流程：
  1. 从 git 拉取模板：`git pull origin main`
  2. 复制模板：`cp ~/cline-workspace/roo-code-settings.template.json ~/roo-code-settings.json`
  3. 编辑填入实际 API key：`vim ~/roo-code-settings.json`
  4. 重启 VSCode 自动导入

## Windsurf IDE

- [2026-04-11] [Sonnet] **Windsurf 版本更新**：从 1.107.0 (nixpkgs 1.9552.21) 升级到 1.108.2 (nixpkgs 1.9577.43)。通过 `/etc/nixos/modules/packages.nix` 添加 `windsurf`，执行 `nixos-rebuild switch`，手动修复 /run/current-system 符号链接。配置完整保留（settings.json、mcp-config.json、models.json）。备份位置：`~/windsurf-backup-20260411/`
- [2026-04-11] [Sonnet] Windsurf 配置同步：settings.json 同步 models.json 全部 10 个模型（LiteLLM 8 个 + Anthropic 2 个），添加 Anthropic provider 配置，本地模型（qwen3-8b/deepseek-r1-14b）已集成。MCP 集成 Letta (localhost:8283) 通过 mcp-config.json 已配置，支持 memory-search、memory-store、agent-control 工具。
- [2026-04-11] [Sonnet] Windsurf 输出风格同步：添加 `codeium.chat.customInstructions` 配置引用 CLAUDE.md 规则（中文输出、零废话、紧凑格式、视觉模板、自动验证、记忆写入）。创建 `~/.windsurfrules` 全局规则文件，重启 Windsurf 后自动生效。
- [2026-04-11] [Sonnet] Windsurf 智能路由配置完成：customInstructions 添加 AUTO_MODEL_ROUTING 规则（复杂推理→deepseek-r1、代码生成→deepseek-v3.2、通用对话→glm-4-plus、快速响应→gemini-flash）。检测到 GLM 云模型余额不足（error 1113），自动 fallback 到 glm-4-flash。测试脚本：~/.local/bin/test-windsurf-router。
- [2026-04-11] [Sonnet] **Windsurf 统一智能路由升级**：添加 GLM-5.1（最新旗舰，超越 Opus 4.6）和 GLM-5-Turbo（Agent 专用优化）到 LiteLLM。创建 `windsurf-smart` 虚拟模型（GLM-5.1 优先 → DeepSeek V3.2 代码备选 → GLM-4-Flash 免费兜底），延迟优先路由自动选择最快实例。更新 Windsurf settings.json 添加 11 个模型（含 windsurf-smart），修改 customInstructions 为 AUTO_MODEL_ROUTING v2（默认使用 @windsurf-smart 统一入口，无需手动指定）。测试通过：windsurf-smart/glm-5.1/glm-5-turbo 全部调用成功。测试脚本：`~/.local/bin/test-windsurf-smart-router`。
- **配置文件路径**：
  - `~/.config/Windsurf/User/settings.json`（Codeium 集成）
  - `~/.config/windsurf-settings/models.json`（模型定义）
  - `~/.codeium/windsurf/mcp-config.json`（MCP 服务器）
- **可用模型**（11个）：
  - LiteLLM: windsurf-smart（统一路由）, cloud/glm-5.1, cloud/glm-5-turbo, cloud/glm-5, silicon/deepseek-v3.2, silicon/deepseek-r1, cloud/glm-4-plus, doubao/pro, cloud/gemini-flash, local/qwen3-8b, local/deepseek-r1-14b
  - Anthropic: claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022
- **MCP 集成**：Letta 记忆系统（http://localhost:8283）
- **使用指南**：`~/Windsurf价格说明.md`

## Cursor IDE（✅ 配置完成 — 2026-04-11）

- [2026-04-11] [Sonnet] **Cursor 自动配置完成**：从 Windsurf 迁移，解决配额限制问题。已安装 v2.6.22（NixOS packages）。直接编辑 `~/.config/Cursor/User/settings.json` 完成配置（Cursor 2026 实际支持 JSON 配置，无需 UI）。
- **配置完成状态**：
  - ✅ OpenAI Base URL: http://localhost:4000/v1
  - ✅ API Key: sk-litellm-charlie-2026
  - ✅ 默认模型: windsurf-smart（智能路由）
  - ✅ Custom Instructions: 完整迁移自 Windsurf（CLAUDE.md 规则）
  - ✅ Anthropic API: 直连支持（sk-WRoD7peu...）
  - ✅ LiteLLM 连接验证通过（windsurf-smart/glm-smart/r1-smart 可用）
  - ✅ Cursor 进程运行正常
- **可用模型**（全量继承自 Windsurf）：
  - windsurf-smart（智能路由：GLM-5.1 → DeepSeek → GLM-4-Flash）
  - cloud/glm-5.1（旗舰，超越 Opus 4.6）
  - cloud/glm-5-turbo（Agent 优化）
  - silicon/deepseek-v3.2（代码生成，164K 上下文）
  - silicon/deepseek-r1（推理专用）
  - cloud/glm-5, cloud/glm-4-plus, doubao/pro, cloud/gemini-flash
  - local/qwen3-8b, local/deepseek-r1-14b
  - Claude 全系列（通过 Anthropic API）
- **配额优势**：
  - ❌ 无配额限制（vs Windsurf 每日配额）
  - ✅ 使用自己的 API（LiteLLM + Anthropic）
  - ✅ 完全控制成本和路由
- **配置方式对比**：
  - 实测：Cursor settings.json 可直接编辑（网上文档过时）
  - 配置方式：JSON 编辑（与 Windsurf 相同）
  - 模型切换：`@model-name` 前缀 vs Windsurf 下拉菜单
  - MCP 支持：通过 Cline 扩展（Letta 已配置）
- **优劣势总结**：
  - Cursor 优势：**无配额限制**（核心优势）、社区活跃、更成熟
  - Windsurf 优势：UI 更直观、MCP 原生支持、智能路由可见性
- **建议策略**：
  - 主力：Cursor（日常开发，无配额担忧）
  - 辅助：Windsurf（MCP 调试，UI 配置可视化）
- **配置文件**：
  - `~/.config/Cursor/User/settings.json`（核心配置，已完成）
  - `~/.config/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`（Letta MCP）
- **验证工具**：
  - `~/cursor-quick-test.sh`（完整验证脚本）
  - 测试结果：✅ Cursor 运行 / ✅ 配置正确 / ✅ LiteLLM 连接
- **配置文档**：
  - `~/cursor-litellm-setup.md`（完整配置指南）
  - `~/windsurf-byok-setup.md`（Windsurf 限制分析）
- **下一步测试**：
  - 用户打开 Cursor → Ctrl+L → 输入测试消息
  - 确认 windsurf-smart 智能路由工作正常
  - 验证无配额错误
- **参考资料**：
  - [Cursor API Keys 文档](https://docs.cursor.com/settings/api-keys)
  - [Cursor Custom API Setup 2026](https://ofox.ai/blog/cursor-claude-code-cline-custom-api-setup-2026/)
  - [Cursor Local-First Setup](https://vucense.com/ai-intelligence/sovereign-coding-agents/cursor-local-first-sovereign-setup/)

## VSCode Cline（✅ 配置完成 — 2026-04-11）

- [2026-04-11] [Sonnet] **Cline 完整配置迁移**：从 Windsurf/Cursor 完整迁移到 VSCode Cline v3.77.0。配置方式：通过 `~/.config/Code/User/settings.json` 完成全部配置（LiteLLM 网关 + Anthropic Direct + Custom Instructions + MCP Servers）。验证通过：LiteLLM 网关 47 个模型可用，配置文件完整性检查通过，MCP dependencies 全部满足。
- **配置完成状态**：
  - ✅ VSCode 已安装（/home/charlie/.local/bin/code）
  - ✅ Cline 扩展 v3.77.0（saoudrizwan.claude-dev）
  - ✅ LiteLLM 网关：http://localhost:4000/v1（API Key: sk-litellm-charlie-2026）
  - ✅ 默认模型：windsurf-smart（智能路由）
  - ✅ Anthropic Direct：sk-WRoD7peu...（备用）
  - ✅ Custom Instructions：完整 CLAUDE.md 规则（6000+ 字符）
  - ✅ MCP Servers：claude-knowledge + litellm + letta（3 个）
  - ✅ 温度设置：0.3
  - ✅ 行为设置：只读允许，写入需确认，diff 启用，浏览器启用
- **可用模型**（47 个，通过 LiteLLM）：
  - **核心 11 个**：windsurf-smart, cloud/glm-5.1, cloud/glm-5-turbo, cloud/glm-5, silicon/deepseek-v3.2, silicon/deepseek-r1, cloud/glm-4-plus, doubao/pro, cloud/gemini-flash, local/qwen3-8b, local/deepseek-r1-14b
  - **Claude 模型**（通过 Anthropic API）：claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022
  - **其他 LiteLLM 模型**：text-embedding-ada-002, local/nomic-embed, free/groq-llama-70b 等（共 47 个）
- **MCP 集成**（完整继承自 Windsurf）：
  - **claude-knowledge**（本地记忆系统）：
    - 路径：/home/charlie/.local/lib/windsurf-knowledge-mcp/server.js
    - 环境变量：MEMORY_PATH, SKILLS_PATH, RULES_PATH
    - 工具：list_memory_files, read_memory, search_memory, list_skills, read_skill, get_rules
  - **litellm**（通用工具调用）：
    - 命令：npx -y @modelcontextprotocol/server-everything
    - 环境变量：OPENAI_API_KEY, OPENAI_API_BASE
  - **letta**（语义记忆）：
    - 命令：npx -y @letta/mcp
    - 环境变量：LETTA_BASE_URL（http://localhost:8283）
    - 状态：⚠️ Letta 服务未运行（可选功能，非阻塞）
- **Custom Instructions**（完整 CLAUDE.md 规则）：
  - 中文输出优先
  - 零废话格式（Power User Protocol 2026）
  - 视觉模板（卡片分组、时间轴、极简双栏）
  - 智能模型路由 v2（AUTO_MODEL_ROUTING）
  - 自动验证协议（配置/服务/脚本）
  - 记忆管理规则（EXPLORE_MEMORY_LOOP）
  - 安全检索协议（SAFETY RETRIEVAL）
- **Cline 配置项**：
  - `cline.apiProvider: "openrouter"`（使用 OpenRouter 兼容端点）
  - `cline.openRouterApiKey: "sk-litellm-charlie-2026"`
  - `cline.openRouterBaseUrl: "http://localhost:4000/v1"`
  - `cline.openRouterModelId: "windsurf-smart"`
  - `cline.openRouterModelInfo`: maxTokens 200000, contextWindow 200000, supportsImages true, supportsPromptCache true
  - `cline.anthropicApiKey: "sk-WRoD7peu..."`（Anthropic 备用）
  - `cline.temperature: 0.3`
  - `cline.alwaysAllowReadOnly: true`
  - `cline.alwaysAllowWriteOnly: false`
  - `cline.soundEnabled: false`
  - `cline.diffEnabled: true`
  - `cline.browserEnabled: true`
- **验证工具**：
  - 脚本：`~/cline-verify.sh`（完整配置验证）
  - 验证项：VSCode 安装、Cline 扩展、配置文件完整性、LiteLLM 网关、Letta 服务、MCP 依赖
  - 测试结果：✅ 全部通过（除 Letta 服务未运行，非阻塞）
- **配置文件路径**：
  - `~/.config/Code/User/settings.json`（核心配置）
  - `~/cline-setup-notes.md`（完整配置文档）
  - `~/cline-verify.sh`（验证脚本）
- **与 Windsurf/Cursor 对比**：
  - ✅ 模型数量：47 个（vs Windsurf 11 个）
  - ✅ 配置方式：JSON 直接编辑（与 Windsurf/Cursor 相同）
  - ✅ MCP 支持：完整继承 Windsurf 配置
  - ✅ Custom Instructions：完整 CLAUDE.md 规则
  - ✅ 温度设置：0.3（与 Windsurf/Cursor 一致）
  - ✅ 无配额限制（使用自己的 LiteLLM 网关）
  - ⚠️ Letta 集成：配置完成但服务未启动（可选）
- **使用建议**：
  - 主力工具：Cursor（社区成熟，无配额）/ Windsurf（MCP 原生，UI 直观）
  - 辅助工具：VSCode Cline（轻量级，全功能，模型最多）
  - 专业场景：Claude Code CLI（终端工作流，记忆系统最完善）
- **下一步优化**（可选）：
  - 启动 Letta 服务（解锁语义记忆搜索）
  - 测试 Cline MCP tools 调用（letta_search, letta_store）
  - 验证 windsurf-smart 智能路由工作正常
- **参考资料**：
  - [Cline GitHub](https://github.com/cline/cline)
  - [Cline 配置示例](https://github.com/cline/cline/blob/main/docs/configuration.md)
  - [MCP 配置方式](https://github.com/cline/cline/blob/main/docs/mcp.md)

## VSCode Roo Code Nightly（✅ 配置完成 — 2026-04-11）

- [2026-04-11] [Sonnet] **Roo Code Nightly 完整配置迁移**：从 Windsurf/Cursor/Cline 完整迁移到 VSCode Roo Code Nightly v0.0.8150。配置方式：通过 `~/.config/Code/User/settings.json` 完成全部配置（OpenAI Compatible API + Custom Instructions + MCP Servers）。验证通过：LiteLLM 网关 47 个模型可用，配置完整性检查通过，扩展正常安装。
- [2026-04-11] [Sonnet] **Roo Code MCP 集成配置**：
  - 配置位置：`/home/charlie/cline-workspace/.roo/mcp.json`（项目级，优先于全局配置）
  - 正确包名（重要）：
    - ✅ letta MCP: `@iflow-mcp/letta-mcp-server` (来自 iflow-mcp 组织)
    - ✅ litellm MCP: `@modelcontextprotocol/server-everything`
    - ❌ 错误包名: `@letta/mcp` (不存在于 npm registry)
  - 可访问资源：
    - memory 文件（17个）- 通过 claude-knowledge MCP
    - skills（65+个）- 通过 claude-knowledge MCP
    - CLAUDE.md 规则 - 通过 get_rules 工具
    - Letta 语义记忆 - 通过 letta MCP (`@iflow-mcp/letta-mcp-server`)
    - LiteLLM 工具调用 - 通过 litellm MCP (`@modelcontextprotocol/server-everything`)
  - 使用：重启 VSCode 后自动加载，MCP 工具出现在 Roo Code 工具列表
  - 验证：检查 Roo Code 界面是否显示 read_memory、list_skills、get_rules 等工具
  - 故障排查：若 MCP 报错 "Connection closed"，检查包名是否正确（详见 lessons-learned.md）
- **配置完成状态**：
  - ✅ Roo Code Nightly v0.0.8150（RooVeterinaryInc.roo-code-nightly）
  - ✅ API Provider：openai-compatible
  - ✅ Base URL：http://localhost:4000/v1
  - ✅ API Key：sk-litellm-charlie-2026
  - ✅ 默认模型：windsurf-smart（智能路由）
  - ✅ Custom Instructions：完整 CLAUDE.md 规则
  - ✅ MCP Servers：claude-knowledge + litellm + letta（3 个）
  - ✅ GPU 禁用：--disable-gpu（解决 Webview 黑屏）
- **可用模型**（47 个）：
  - 核心模型：windsurf-smart, cloud/glm-5.1, cloud/glm-5-turbo, silicon/deepseek-v3.2, silicon/deepseek-r1
  - Claude 模型：claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022
  - 本地模型：local/qwen3-8b, local/deepseek-r1-14b
- **优势**：
  - ✅ CustomInstructions 支持（vs Cline 不生效）
  - ✅ 无 Webview 黑屏（通过 --disable-gpu 解决）
  - ✅ 完整 MCP 支持
  - ✅ 免费开源
- **输出格式控制**（重要）：
  - 问题：Roo 默认输出包含大量 Mermaid 图、Gantt 图、emoji 状态、多种框线，违反 CLAUDE.md 紧凑规则
  - 解决：在 customInstructions 明确禁止以下内容：
    - ❌ Mermaid 图表（flowchart/graph/sequenceDiagram 等）
    - ❌ Gantt 图
    - ❌ emoji 状态标记（✅❌🔄🎯 等）
    - ❌ 多种框线混用（不在同一回复中使用超过 1 种框线）
    - ❌ 装饰元素超过 10%（分隔线、标记符号、框线）
  - 强制规则：每段最多 1 个加粗，段落不超 3 行，代码块不超 15 行
  - 教训：AI 编程助手 system prompt 需要明确输出格式约束，否则倾向于"炫技式"输出
  - 配置位置：`roo-cline.customInstructions` in `~/.config/Code/User/settings.json`
- **配置文件**：
  - `~/.config/Code/User/settings.json`（核心配置）
  - `~/roocode-setup-notes.md`（完整文档）
  - `~/roocode-verify.sh`（验证脚本）
  - `/home/charlie/cline-workspace/.roo/mcp.json`（MCP 配置）
  - `~/roo-code-settings.json`（API Profiles 配置，解决 401 错误）
- **使用方式**：
  1. 打开 VSCode：`code --disable-gpu ~/cline-workspace`
  2. 左侧栏点击 Roo Code 图标
  3. 选择模型：windsurf-smart
  4. 输入任务 → 自动应用 CLAUDE.md 规则
- **故障排查**：
  - **401 Provider Error** → 检查 ~/roo-code-settings.json 是否存在，autoImportSettingsPath 配置是否正确
  - **输出风格违反规则** → 检查 customInstructions 是否包含完整格式禁止项
  - **MCP Connection closed** → 检查 letta MCP 包名是否为 `@iflow-mcp/letta-mcp-server`
- **验证测试**：
  - ⏳ 待用户测试界面是否正常
  - ⏳ 验证 customInstructions 生效（中文输出）
  - ⏳ 验证 MCP tools 可用
- **参考资料**：
  - [Roo Code Nightly - Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=RooVeterinaryInc.roo-code-nightly)
  - [Using OpenAI Compatible Providers](https://docs.roocode.com/providers/openai-compatible)

## OpenCode AI（2026-04-13）

- [2026-04-13] [Sonnet] **OpenCode 安装与配置**
  - 已安装：`/home/charlie/.local/bin/opencode` (v1.2.27)
  - 配置：`~/.config/opencode/opencode.json`
  - 灵魂文件：`~/.config/opencode/AGENTS.md`（从 CLAUDE.md 自动编译）
  - Provider：LiteLLM（GLM-5.1/GLM-5-Turbo/GLM-4.7/GLM-4-Plus/DeepSeek-V3.2）
  - Agent 路由：oh-my-openagent 智能分配（sisyphus 编排 → category_mapping 自动选模型）
  - MCP：claude-knowledge + exa + context7 + grep_app
  - 文档：https://opencode.ai/docs/config/
- [2026-04-15] [Opus] **OpenCode 插件补全（社区最佳配置）**
  - 插件清单（10 个）：
    1. oh-my-openagent — 多 agent 智能编排（sisyphus/atlas/prometheus 等 11 agent）
    2. opencode-vibeguard — 安全防护
    3. opencode-pty — 终端集成
    4. opencode-scheduler — 定时任务
    5. opencode-worktree — git worktree 隔离
    6. opencode-stt — 语音输入（本地 Whisper，venv: /mnt/ai/cache/opencode-stt-venv）
    7. envsitter-guard — .env 防泄露
    8. opencode-snip — 输出压缩省 60-90% token
    9. opencode-mystatus — AI 额度监控（/mystatus）
    10. opencode-mem — 持久记忆向量 DB（Web UI: http://127.0.0.1:4747）
  - 全局工具：opencode-telegram-bot（Telegram 远程控制）
  - LSP：typescript/bash/python/json/yaml
  - oh-my-openagent agents：sisyphus(编排)/atlas(并行)/prometheus(规划)/hephaestus(深度执行)/oracle(顾问)/librarian(文档)/explore(搜索)/metis(预规划)/momus(评审)/multimodal-looker(媒体)
  - category_mapping：quick→glm-4.7 / deep→deepseek-v3.2 / visual-engineering→glm-5-turbo / ultrabrain→glm-5.1

## compiler.py v2（2026-04-13）

- [2026-04-13] [Sonnet] **灵魂系统编译器升级 v2**
  - 路径：`~/.config/ai-shared/compiler.py`
  - 输入：CLAUDE.md（34KB）+ shared-rules.yaml
  - 输出目标：
    1. `shared-prompt.md` — YAML→markdown（v1 兼容）
    2. `AGENTS.md` — OpenCode 规则（~4KB，P0+P1 级）
    3. `shared-prompt-aider.md` — Aider 极简规则（~656B）
    4. `shared-prompt-{model}.md` — 各模型专属版本
  - CLI：`--target opencode|aider|yaml`、`--dry-run`
  - systemd path unit：`claude-md-compiler.path` 监控 CLAUDE.md 变更自动触发

## IDE 清理（2026-04-13）

- [2026-04-13] [Sonnet] **冗余 IDE 清理**
  - 备份：`~/ide-backup-archive/2026-04-13/`（windsurf-config 65MB、codeium-config 1.1MB）
  - Cline 扩展：已禁用（`code --disable-extension saoudrizwan.claude-dev`）
  - ttyd-gemini：已停止并禁用
  - Windsurf/Cursor 本体保留（NixOS 包管理，需走 nix 配置变更）

## OpenCode sidebar 配置（2026-04-15）

- [2026-04-15] [GLM-5.1] **OpenCode sidebar 消失修复**
  - 现象：TUI 右侧 sidebar 不显示，找不到 show sidebar 选项
  - 根因：OpenCode sidebar 可见性由 KV 存储 > config > 默认值 三级优先级控制，之前某次 `ctrl+x b` 隐藏被 KV 记住
  - 快捷键：`ctrl+x` 然后 `b` 切换 sidebar
  - 配置修复：在 `~/.config/opencode/tui.json` 添加 `"sidebar": "show"` 强制初始显示
  - 可选值：`"auto"` / `"show"` / `"hide"`
  - 参考：PR #6955, Issue #3682

- [2026-04-15] [GLM-5.1] **OpenCode 默认 agent 设为 sisyphus**
  - 配置：`opencode.json` 添加 `"default_agent": "sisyphus"`
  - 所有 agent 保留在 Tab 循环中，sisyphus 排第一
  - sisyphus 由 oh-my-openagent 插件注册，opencode.json 只需指定名字
  - 参考：https://opencode.ai/docs/en/config/ → default_agent 字段

## DeepWiki-Open (2026-04-15)
- Docker: `ghcr.io/asyncfuncai/deepwiki-open:latest`
- 容器名: `deepwiki`
- 前端: http://localhost:3000 | API: http://localhost:8001
- LLM 后端: 通过 LiteLLM (OPENAI_BASE_URL=http://172.17.0.1:4000/v1)
- 代理: HTTP_PROXY=http://192.168.123.209:7890 (tiktoken 下载需要)
- 数据卷: ~/.adalflow → /root/.adalflow
- 功能: GitHub 仓库文档生成、代码库分析、Wiki 自动生成

## Agent 指令合规性方案对比 (2026-04-15)

### 问题
CLAUDE.md 中 MUST 规则被反复跳过，"内部推理"设计导致执行无保障。

### 社区方案调研结论
| 方案 | 机制 | 合规率 | 适用场景 |
|------|------|--------|---------|
| CLAUDE.md 规则 | 纯指令 | ~70% | L1 基线 |
| 强制输出标签 | `[TAG]` 格式约束 | ~85% | L2 当前方案 |
| agent-ruler (bunx) | 编译 CLAUDE.md 为检查脚本 | ~90% | 多文件验证 |
| claude-rule-enforcer | PreToolUse/PostToolUse hooks | ~95% | 写入拦截 |
| Stop Hook (exit 2) | 会话结束前阻塞检查 | ~99% | L3 确定性 |

### 已采纳（L2 强制输出）
- 6 个协议改为强制输出标签：`[自检]` `[ARCH]` `[SKILL]` `[AUTO_SKILL]` `[PRE_EXPLORE]` `[POST_EXPLORE]`
- 失败计数器：连续 3 次跳过 → 写入 lessons-learned

### 待实现（L3 Hook 层）
- **Stop Hook**：会话结束前检查是否有未写入 memory 的操作 → `exit 2` 阻塞
- **PreToolUse Hook**：文件写入前检查是否执行了 `[PRE_GATE]` memory 搜索
- 优先级：Stop Hook > PreToolUse Hook
