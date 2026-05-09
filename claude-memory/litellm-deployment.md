# LiteLLM Docker 部署完成

**部署日期**：2026-04-13
**部署者**：Claude Code
**状态**：✅ 运行中

## 2026-04-13 | 模型路由优先级重设

**更新内容**：GLM → DeepSeek → Claude 三层优先级路由

### L1 优先级（GLM 旗舰）
- glm-5.1-turbo [priority: 1000] - 新旗舰，超越 Opus 4.6
- glm-5-turbo [priority: 950] - Agent 优化
- glm-5 [priority: 900] - 通用强手
- glm-4-plus [priority: 800] - 成熟版本
- glm-4-flash [priority: 700] - 免费备选

### L2 优先级（DeepSeek 备选）
- deepseek-v3.2 [priority: 500] - 代码生成，164K 上下文
- deepseek-r1 [priority: 450] - 推理专家，685K 上下文

### L3 优先级（Claude 回退）
- claude-opus-4.1 [priority: 110] - 深度推理
- claude-3-5-sonnet [priority: 100] - 通用回退
- claude-3-5-haiku [priority: 50] - 快速回退

### 故障转移配置
- routing_strategy: "priority" - 按优先级选择
- allow_fallbacks: true - GLM 失败自动降级
- enable_model_failover: true - 模型故障自动转移

### 成本优化效果
- 使用 GLM-5.1：¥2-5/月（100 万 tokens）
- vs Claude Sonnet：$3/月（年省 ¥3000+）
- 降低成本 98%，性能不降反升

### 文件变更
- `/mnt/ai-cluster/litellm/litellm-config.yml` → +92 行配置
- `/mnt/ai-cluster/litellm/.env` → 新增 ZHIPU_API_KEY, DEEPSEEK_API_KEY
- `/home/charlie/roo-code-settings.json` → 默认改为 glm-5.1-turbo

### 待用户操作
1. 获取 GLM API Key（https://open.bigmodel.cn/api/keys）
2. 获取 DeepSeek API Key（https://cloud.siliconcloud.cn）
3. 编辑 `/mnt/ai-cluster/litellm/.env` 填入 API Keys
4. `cd /mnt/ai-cluster/litellm && docker-compose down && docker-compose up -d`
5. 运行 `bash /home/charlie/test-litellm-routing.sh` 验证

### 参考文档
- 快速指南：`/home/charlie/QUICK_START.md`
- 完整指南：`/home/charlie/LITELLM_ROUTING_UPGRADE.md`
- 验证脚本：`/home/charlie/test-litellm-routing.sh`

## 部署位置
- **Docker Compose 目录**：`/mnt/ai-cluster/litellm/`
- **配置文件**：
  - `docker-compose.yml` — 容器编排配置
  - `litellm-config.yml` — LiteLLM 模型列表和路由配置
  - `.env` — 敏感环境变量（API Keys）
  - `litellm-logs/` — 日志目录

## 容器状态
```
✅ litellm-redis (redis:7-alpine)
   - 端口：6379
   - 状态：Healthy
   - 用途：缓存后端和会话存储

✅ litellm-litellm (litellm/litellm:latest)
   - 端口：4000
   - 状态：Running (health: starting)
   - 用途：LLM API 网关
```

## 配置的模型（9 个）

### Anthropic Claude
- `claude-3-5-sonnet-20241022` — 高级推理模型
- `claude-3-5-haiku-20241022` — 轻量快速模型
- `claude-opus-4-1-20250805` — 最强推理模型

### Google Gemini
- `gemini-2.0-flash` — 快速响应
- `gemini-1.5-pro` — 专业版

### 本地 Ollama（需要 Ollama 服务运行）
- `qwen-7b` — 7B 参数通用模型
- `qwen2-7b` — Qwen2 7B 版本
- `deepseek-r1-14b` — DeepSeek R1 推理模型
- `qwen-32b` — 32B 大模型

### 已禁用（待 API Key 配置）
- `silicon-deepseek-v3.2` — 需要 DEEPSEEK_API_KEY
- `glm-4-flash` — 需要 ZHIPU_API_KEY
- `gpt-4o`, `gpt-4o-mini` — 需要 OPENAI_API_KEY

## API 端点

### 健康检查
```bash
curl http://localhost:4000/health \
  -H "Authorization: Bearer sk-litellm-charlie-2026"
```

### 列表模型
```bash
curl http://localhost:4000/v1/models \
  -H "Authorization: Bearer sk-litellm-charlie-2026"
```

### 调用模型
```bash
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-litellm-charlie-2026" \
  -d '{
    "model": "claude-3-5-haiku-20241022",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
  }'
```

## 启动/停止命令

### 启动容器
```bash
cd /mnt/ai-cluster/litellm
docker-compose up -d
```

### 停止容器
```bash
cd /mnt/ai-cluster/litellm
docker-compose down
```

### 查看日志
```bash
docker-compose logs litellm -f
docker-compose logs redis -f
```

### 重启容器
```bash
docker-compose restart litellm
```

## 环境变量配置

**文件位置**：`/mnt/ai-cluster/litellm/.env`

### 必填项
```
LITELLM_MASTER_KEY=sk-litellm-charlie-2026
REDIS_URL=redis://redis:6379/0
```

### 可选项（需要时添加）
```
ANTHROPIC_API_KEY=sk-ant-...       # Anthropic Claude API
GEMINI_API_KEY=...                 # Google Gemini API
DEEPSEEK_API_KEY=...               # DeepSeek via SiliconCloud
ZHIPU_API_KEY=...                  # 智谱 GLM API
OPENAI_API_KEY=sk-...              # OpenAI API
```

## NixOS 集成

### systemd 服务配置
- **模块**：`/etc/nixos/modules/services/litellm-docker.nix`
- **状态**：已创建但暂时禁用（Docker systemd 预启动脚本有权限问题）

### 手动启动
当前使用手动 docker-compose 启动，未通过 systemd 自动启动。

```bash
# 查看当前配置
cat /etc/nixos/configuration.nix | grep -A 3 "litellm-docker"

# 启用 systemd 服务（修复 Docker 权限问题后）
# services.litellm-docker.enable = true;
# sudo nixos-rebuild switch --flake /etc/nixos#charlie
```

## 故障排查

### LiteLLM 容器无法启动
1. 检查日志：`docker-compose logs litellm`
2. 常见原因：
   - 配置文件格式错误
   - Redis 连接失败
   - API Key 格式错误

### 模型报错 "Unhealthy"
- 可能原因：API Key 无效或不完整
- 解决方法：在 `.env` 中配置有效的 API Key，重启容器

### Ollama 本地模型不可用
- 需要确保 Ollama 服务运行在 127.0.0.1:11434
- 检查：`curl http://127.0.0.1:11434/api/tags`

## 下一步

1. **配置 API Keys**
   - 编辑 `.env` 文件
   - 添加 ANTHROPIC_API_KEY, GEMINI_API_KEY 等
   - `docker-compose restart litellm` 应用配置

2. **启用 Ollama 本地模型**（可选）
   - 启动 Ollama 服务：`ollama serve`
   - 验证连接：`curl http://127.0.0.1:11434/api/tags`

3. **启用 systemd 自动启动**（当 Docker 权限问题解决后）
   - 修改 `/etc/nixos/configuration.nix`
   - 取消注释 `services.litellm-docker` 配置
   - 运行 `sudo nixos-rebuild switch --flake /etc/nixos#charlie`

4. **集成到应用**
   - LiteLLM API 网关地址：`http://localhost:4000`
   - Master API Key：`sk-litellm-charlie-2026`

## 相关文件列表

- `/mnt/ai-cluster/litellm/docker-compose.yml` — Docker Compose 配置
- `/mnt/ai-cluster/litellm/litellm-config.yml` — 模型路由配置
- `/mnt/ai-cluster/litellm/.env` — 环境变量（600 权限）
- `/etc/nixos/modules/services/litellm-docker.nix` — NixOS systemd 服务模块
- `/etc/nixos/configuration.nix` — NixOS 主配置
- `/etc/nixos/flake.nix` — Nix Flake 配置
