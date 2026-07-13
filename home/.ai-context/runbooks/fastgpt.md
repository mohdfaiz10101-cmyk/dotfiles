# Runbook: FastGPT

FastGPT v4.8.23 — 知识库 + 工作流问答前端（**不是**代码执行器，那是 opencode 的职责）。

## Desired State

- `fastgpt` (app) — 监听 `0.0.0.0:3000`
- `fastgpt-mongo` (mongo 5.0.18) — 数据库
- `fastgpt-pg` (pgvector 0.7.0-pg15) — 向量数据库
- Compose: `~/ai/fastgpt/docker-compose.yml`
- 配置: `/var/mnt/ai/fastgpt/config/config.json`

## 模型链路

- LLM 走 LiteLLM strip-proxy `http://host.containers.internal:4000/v1`，key `sk-litellm-charlie-2026`
- Embedding 走本地 `all-MiniLM-L6-v2`（384 dim，由 `embedding-server.service` `:8286` 提供，FastGPT 通过同一个 OpenAI-compatible endpoint 调用）
- 注册的模型见 `config.json` `llmModels[]` / `vectorModels[]`：
  - 主力问答：`glm-4.7`
  - 深度推理：`glm-5.2` / `deepseek-v4-pro`
  - 廉价：`glm-5-turbo` / `deepseek-v4-flash` / `step-3.7-flash`
  - 图像：`glm-4.6v-flash`
  - 向量：`all-MiniLM-L6-v2`（本地）

## 入口

- LAN: `http://192.168.123.71:3000`
- FRP: `http://charlie1990.duckdns.org:19894/`（frpc `fedora-fastgpt`）
- 登录：用户名 `root`，密码见 `DEFAULT_ROOT_PSW` 环境变量 / 1Password
- 自动登录：**不可行**（FastGPT 走 POST+Cookie/JWT，URL 内嵌凭据无效；已验证）

## Verify

```bash
# 容器栈
podman ps --filter name=fastgpt --format '{{.Names}} {{.Status}}'

# HTTP 活性（首页返回 Next.js HTML）
curl -s --noproxy '*' -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/

# 后台 worker 活性
podman logs --tail 5 fastgpt 2>&1 | grep -E 'Queue'

# FRP 入口
curl -s 'http://admin:frp%40charlie2026@127.0.0.1:7500/api/proxy/tcp' | jq '.proxies[] | select(.name=="fedora-fastgpt") | .status'

# 模型可达性（FastGPT → LiteLLM）
podman exec fastgpt curl -s http://host.containers.internal:4000/v1/models -H 'Authorization: Bearer sk-litellm-charlie-2026' | jq '.data | length'
```

## Restart

```bash
cd ~/ai/fastgpt
podman compose restart fastgpt        # 仅重启 app，加载新 config.json
podman compose up -d                  # 完整栈重启
podman compose pull && podman compose up -d   # 升级镜像
```

## 配置变更

1. 编辑 `/var/mnt/ai/fastgpt/config/config.json`
2. `podman restart fastgpt`（容器内 `CONFIG_FILE=/app/data/config.json` 会重新读取）
3. 新增模型需同步出现在 LiteLLM `/v1/models` 列表里，否则编排时报 `model not found`

## Known Issues

- **OOM**: v4.8.23 在大数据集导入时堆内存超 4GB，`NODE_OPTIONS=--max-old-space-size` 被忽略。compose 已设 `mem_limit: 6g`；如果仍 OOM，限制 `vectorMaxProcess`/`qaMaxProcess`（当前 5）或分批导入。
- **Plugin service**: v4.15+ 部分功能（链接抓取、外部工具）需要独立的 `fastgpt-plugin` 服务。当前栈未部署，相关功能不可用。
- **Auto-login**: FastGPT 走 POST `/api/support/user/account/login/password` + JWT，无法用 FRP/反向代理 URL 内嵌凭据自动登录（与 FRP dashboard 不同）。
- **未注册 rerank / whisper / TTS**: LiteLLM 和本地 embedding-server 都不暴露对应 OpenAI-compatible 端点，留空即可。
- **数据库卷**: `fastgpt_fastgpt-mongo-data` / `fastgpt_fastgpt-pg-data` 为 external 卷，删除 compose 文件不影响数据；`podman volume rm` 才会丢数据。

## 与其他服务的边界

- **opencode**: 写代码/执行 — FastGPT 不做代码生成
- **open-webui** (`:3001`): 通用对话前端，无知识库编排 — FastGPT 是知识库/工作流特化前端
- **TermHive** (`:3200`): 统一面板入口，FastGPT 作为外链卡片
- **LiteLLM** (`:4000`): FastGPT 不直连厂商，全部走 LiteLLM strip-proxy
