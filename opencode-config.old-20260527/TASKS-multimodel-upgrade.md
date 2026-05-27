# 任务：OpenCode 多模型零成本升级

## 系统实际路径（已探测）

```
LiteLLM 配置：/mnt/ai-cluster/litellm/litellm-config.yml（挂载到容器 /app/config.yml）
LiteLLM compose：/mnt/ai-cluster/litellm/docker-compose.yml
LiteLLM .env：/mnt/ai-cluster/litellm/.env
LiteLLM 容器名：litellm-litellm
LiteLLM API key：sk-litellm-charlie-2026
OpenCode 配置：~/.config/opencode/opencode.json
OMO 配置：~/.config/opencode/oh-my-openagent.jsonc
Ollama 端口：11434（容器内用 host.docker.internal:11434）
代理：mihomo 7890（Docker 网桥用 172.17.0.1:7890）
```

## 已有 Key（在 /mnt/ai-cluster/litellm/.env 中）

```
ZAI_API_KEY=已填 ✓
SILICONFLOW_API_KEY=已填 ✓
GEMINI_API_KEY=已填 ✓（来源：~/.config/api-keys/env）
GITHUB_TOKEN=已填 ✓（来源：~/.git-credentials）
```

> ✅ 所有 Key 已由 Opus 自动填入，无需用户操作

---

## P0 — LiteLLM 加模型（优先级最高）

### 任务 1：用户填入 API Key

编辑 `/mnt/ai-cluster/litellm/.env`，填入：

```bash
# 找到 GEMINI_API_KEY= 那行，填入 key
GEMINI_API_KEY=用户提供的key

# 在文件末尾新增 GITHUB_TOKEN
GITHUB_TOKEN=用户提供的token
```

### 任务 2：向 LiteLLM config 追加新模型

编辑 `/mnt/ai-cluster/litellm/litellm-config.yml`（这是宿主机文件，直接编辑，重启后自动生效），在 `model_list:` 末尾、`router_settings:` 之前追加：

```yaml
  # === Google Gemini（免费，AI Studio） ===
  - model_name: gemini-2.5-pro
    litellm_params:
      model: gemini/gemini-2.5-pro-preview-05-06
      api_key: os.environ/GEMINI_API_KEY
      timeout: 120

  - model_name: gemini-2.5-flash
    litellm_params:
      model: gemini/gemini-2.5-flash-preview-04-17
      api_key: os.environ/GEMINI_API_KEY
      timeout: 60

  # === GitHub Models（免费） ===
  - model_name: gpt-4.1
    litellm_params:
      model: openai/gpt-4.1
      api_base: https://models.github.ai/inference
      api_key: os.environ/GITHUB_TOKEN
      timeout: 60

  # === SiliconFlow Qwen3（免费额度） ===
  - model_name: qwen3-235b
    litellm_params:
      model: openai/Qwen/Qwen3-235B-A22B
      api_base: https://api.siliconflow.cn/v1
      api_key: os.environ/SILICONFLOW_API_KEY
      timeout: 60

  # === 本地 Ollama ===
  - model_name: qwen3-8b-local
    litellm_params:
      model: ollama/qwen3:8b
      api_base: http://host.docker.internal:11434
      timeout: 120
```

### 任务 3：确保 Docker 代理配置

检查 `/mnt/ai-cluster/litellm/docker-compose.yml`，确认 litellm 服务的 environment 段有代理配置（Gemini 和 GitHub 需要翻墙）：

```yaml
environment:
  - HTTPS_PROXY=http://172.17.0.1:7890
  - HTTP_PROXY=http://172.17.0.1:7890
  - NO_PROXY=localhost,127.0.0.1,host.docker.internal,open.bigmodel.cn,api.z.ai,api.siliconflow.cn
```

如果没有，追加到 environment 段。

然后重启：
```bash
cd /mnt/ai-cluster/litellm
docker compose up -d
```

### 任务 4：验证新模型可用

```bash
# 验证 Gemini
curl -s http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-charlie-2026" \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini-2.5-flash","messages":[{"role":"user","content":"say hi"}]}' | head -100

# 验证 GitHub GPT-4.1
curl -s http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-charlie-2026" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4.1","messages":[{"role":"user","content":"say hi"}]}' | head -100

# 验证 Qwen3
curl -s http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-charlie-2026" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-235b","messages":[{"role":"user","content":"say hi"}]}' | head -100

# 验证本地 Ollama（需先 pull 模型）
curl -s http://localhost:11434/api/pull -d '{"name":"qwen3:8b"}' | tail -1
curl -s http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-charlie-2026" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-8b-local","messages":[{"role":"user","content":"say hi"}]}' | head -100
```

每个都要确认返回正常 JSON 响应，不是 error。

---

## P0 — OpenCode 配置更新

### 任务 5：更新 opencode.json models

编辑 `~/.config/opencode/opencode.json`，在 `provider.openai-compatible.models` 段追加新模型：

```jsonc
"models": {
  // ... 已有的 glm-5.1, glm-5-turbo, glm-4.7, glm-4-plus, deepseek-v3.2 ...
  "gemini-2.5-pro": {
    "name": "Gemini 2.5 Pro (Google 免费)",
    "limit": { "context": 1048576, "output": 65536 }
  },
  "gemini-2.5-flash": {
    "name": "Gemini 2.5 Flash (Google 免费)",
    "limit": { "context": 1048576, "output": 65536 }
  },
  "gpt-4.1": {
    "name": "GPT-4.1 (GitHub 免费)",
    "limit": { "context": 1047576, "output": 32768 }
  },
  "qwen3-235b": {
    "name": "Qwen3-235B (SiliconFlow 免费)",
    "limit": { "context": 131072, "output": 8192 }
  },
  "qwen3-8b-local": {
    "name": "Qwen3-8B 本地 (Ollama)",
    "limit": { "context": 32768, "output": 8192 }
  }
}
```

### 任务 6：更新 opencode.json agents 路由

更新 `agent` 段，利用新模型：

```jsonc
"agent": {
  "build": {
    "model": "openai-compatible/glm-5.1",
    "prompt_append": "MUST 始终使用中文回复用户。代码注释可用英文。"
  },
  "plan": {
    "model": "openai-compatible/glm-5.1",
    "prompt_append": "MUST 始终使用中文回复用户。代码注释可用英文。"
  },
  "explore": {
    "model": "openai-compatible/qwen3-8b-local",
    "prompt_append": "MUST 始终使用中文回复用户。代码注释可用英文。"
  },
  "chat": {
    "model": "openai-compatible/gemini-2.5-flash",
    "prompt_append": "MUST 始终使用中文回复用户。代码注释可用英文。"
  },
  "refactor": {
    "model": "openai-compatible/deepseek-v3.2",
    "prompt_append": "MUST 始终使用中文回复用户。代码注释可用英文。"
  },
  "arch": {
    "model": "openai-compatible/gpt-4.1",
    "prompt_append": "MUST 始终使用中文回复用户。代码注释可用英文。"
  }
}
```

### 任务 7：更新 oh-my-openagent.jsonc

编辑 `~/.config/opencode/oh-my-openagent.jsonc`：

**agents 段更新**（保留已有 agent，更新模型分配）：

```jsonc
"agents": {
  "sisyphus": {
    "description": "主编排器 — 任务分解、委派子 agent、验证结果闭环",
    "model": "openai-compatible/glm-5.1",
    "temperature": 0.1,
    "fallback_models": ["openai-compatible/glm-5-turbo", "openai-compatible/glm-4-plus"],
    "prompt_append": "MUST 始终使用中文回复用户。代码注释可用英文。"
  },
  "atlas": {
    "description": "大师编排器 — 多 agent 并行协调",
    "model": "openai-compatible/glm-5-turbo",
    "temperature": 0.1,
    "prompt_append": "MUST 始终使用中文回复用户。代码注释可用英文。"
  },
  "prometheus": {
    "description": "规划器 — 分析需求、生成可执行计划",
    "model": "openai-compatible/glm-5.1",
    "temperature": 0.3,
    "prompt_append": "MUST 始终使用中文回复用户。代码注释可用英文。"
  },
  "hephaestus": {
    "description": "深度执行器 — 长上下文代码生成、复杂重构",
    "model": "openai-compatible/deepseek-v3.2",
    "temperature": 0.2,
    "prompt_append": "MUST 始终使用中文回复用户。代码注释可用英文。"
  },
  "oracle": {
    "description": "只读顾问 — 架构决策、疑难 bug 诊断（GPT-4.1）",
    "model": "openai-compatible/gpt-4.1",
    "temperature": 0.2,
    "tools": { "edit": false, "bash": false },
    "prompt_append": "MUST 始终使用中文回复用户。代码注释可用英文。"
  },
  "librarian": {
    "description": "文档研究员 — 多仓库分析、官方文档检索",
    "model": "openai-compatible/gemini-2.5-flash",
    "temperature": 0.1,
    "prompt_append": "MUST 始终使用中文回复用户。代码注释可用英文。"
  },
  "explore": {
    "description": "代码搜索员 — 定位文件、函数（本地模型零成本）",
    "model": "openai-compatible/qwen3-8b-local",
    "temperature": 0.1,
    "prompt_append": "MUST 始终使用中文回复用户。代码注释可用英文。"
  },
  "metis": {
    "description": "预规划顾问 — 识别隐含意图、歧义",
    "model": "openai-compatible/glm-5-turbo",
    "temperature": 0.2,
    "prompt_append": "MUST 始终使用中文回复用户。代码注释可用英文。"
  },
  "momus": {
    "description": "评审员 — 代码审查（Qwen3-235B）",
    "model": "openai-compatible/qwen3-235b",
    "temperature": 0.1,
    "tools": { "edit": false, "bash": false },
    "prompt_append": "MUST 始终使用中文回复用户。代码注释可用英文。"
  },
  "multimodal-looker": {
    "description": "媒体分析员 — PDF/图片/图表深度解读",
    "model": "openai-compatible/gemini-2.5-pro",
    "temperature": 0.1,
    "prompt_append": "MUST 始终使用中文回复用户。代码注释可用英文。"
  }
}
```

**category_mapping 段更新**（三层路由）：

```jsonc
"category_mapping": {
  "quick":              "openai-compatible/qwen3-8b-local",
  "unspecified-low":    "openai-compatible/glm-5-turbo",
  "unspecified-high":   "openai-compatible/glm-5.1",
  "deep":               "openai-compatible/gpt-4.1",
  "visual-engineering": "openai-compatible/gemini-2.5-pro",
  "ultrabrain":         "openai-compatible/glm-5.1",
  "writing":            "openai-compatible/gemini-2.5-flash",
  "artistry":           "openai-compatible/gemini-2.5-pro"
}
```

---

## P1 — 工程补偿

### 任务 8：创建 planner agent

创建文件 `~/.config/opencode/agents/planner.md`：

```markdown
---
description: 复杂任务分解，输出 TASKS.md，不写任何代码
tools:
  edit: false
  bash: false
temperature: 0.2
---

你是任务规划专家。收到需求后：

1. 分析需求，识别所有涉及的文件和模块
2. 把任务拆解成原子级子任务（每个子任务 < 50行代码改动）
3. 标注每个子任务的：依赖关系、风险点、验证方式
4. 输出到项目根目录的 TASKS.md

TASKS.md 格式：
## 任务：[需求描述]
- [ ] 1. [子任务] — 验证：[如何确认完成]
- [ ] 2. [子任务] — 验证：[如何确认完成]

不要开始写代码。输出 TASKS.md 后停止。
MUST 始终使用中文。
```

### 任务 9：创建 reviewer agent

创建文件 `~/.config/opencode/agents/reviewer.md`：

```markdown
---
description: 代码审查，只读不写，输出问题报告
tools:
  edit: false
  bash: false
temperature: 0.1
---

审查维度（按优先级）：
1. CRITICAL：会导致 bug 或安全问题的代码
2. WARNING：性能问题、不符合项目规范
3. SUGGESTION：可以更好但不紧急

输出格式：
[CRITICAL] 文件:行号 — 问题描述
[WARNING]  文件:行号 — 问题描述
[SUGGESTION] 文件:行号 — 改进建议

没有问题时只输出：LGTM
MUST 始终使用中文。
```

### 任务 10：创建 .env 文件

创建 `~/.config/opencode/.env`：

```bash
# OpenCode 环境变量（API Key 从 LiteLLM 容器共享，此处仅供本地工具用）
HTTPS_PROXY=http://127.0.0.1:7890
HTTP_PROXY=http://127.0.0.1:7890
NO_PROXY=localhost,127.0.0.1,open.bigmodel.cn,api.z.ai,api.siliconflow.cn
```

### 任务 11：验证 context7 MCP

在 OpenCode TUI 中测试：
```
> use context7 to find the latest FastAPI route decorator syntax
```
如果返回实时文档 → context7 正常。如果报错 → 检查 oh-my-openagent.jsonc 中 context7 配置。

---

## 验证清单

全部完成后逐项验证：

```bash
# 1. LiteLLM 模型列表应包含 10 个模型
curl -s -H "Authorization: Bearer sk-litellm-charlie-2026" \
  http://localhost:4000/v1/models | python3 -c \
  "import sys,json; [print(m['id']) for m in json.loads(sys.stdin.read())['data']]"
# 期望：glm-5.1, glm-5-turbo, glm-4.7, glm-4-plus, deepseek-v3.2,
#        gemini-2.5-pro, gemini-2.5-flash, gpt-4.1, qwen3-235b, qwen3-8b-local

# 2. OpenCode 重启后检查插件加载
opencode --version

# 3. 在 OpenCode TUI 中测试各 agent
# > @oracle 分析这个项目的架构  （应走 GPT-4.1）
# > @explore 找到 main 函数      （应走本地 qwen3:8b）
# > @librarian 查 FastAPI 文档    （应走 Gemini Flash）
```

---

## 最终模型分配总览

| Agent | 模型 | 成本 | 用途 |
|-------|------|------|------|
| sisyphus | glm-5.1 | 订阅 | 编排决策 |
| prometheus | glm-5.1 | 订阅 | 规划 |
| atlas | glm-5-turbo | 订阅 | 并行协调 |
| hephaestus | deepseek-v3.2 | 免费额度 | 深度代码生成 |
| oracle | gpt-4.1 | 免费 | 架构顾问（只读） |
| librarian | gemini-2.5-flash | 免费 | 文档检索 |
| explore | qwen3-8b 本地 | $0 | 代码搜索 |
| metis | glm-5-turbo | 订阅 | 预规划 |
| momus | qwen3-235b | 免费额度 | 代码审查（只读） |
| multimodal-looker | gemini-2.5-pro | 免费 | 视觉分析 |
| planner | glm-5.1 | 订阅 | 任务拆解（只读） |
| reviewer | qwen3-235b | 免费额度 | 代码审查（只读） |

**额外月成本：¥0**（全部走免费渠道 + 已有 GLM 订阅）
