# Runbook: AI Infrastructure

LiteLLM、Letta、Embedding Server 三大 AI 基础设施服务。

## Desired State

- `litellm.service` — Podman 容器，监听 `127.0.0.1:4002`，配置 `/var/home/charlie/ai/litellm-config.yml`
- `litellm-strip-proxy.service` — Python 代理，`:4000` → `:4002`（strip tools 模式）
- `litellm-keepalive.timer` — 每 30 秒探测 4002/4000，假死或代理断链时自动按顺序重启 LiteLLM + strip proxy
- `letta-stack.service` — Docker compose（postgres + chromadb + letta），`:8283`
- `letta-stack.service` should start with `docker compose up -d` and should not
  force `docker compose pull` on every service restart. Slow image pulls can keep
  `8283` down and make OpenHands return 500 while its UI still loads.
- `embedding-server.service` — 本地 Python 嵌入服务，`:8286`
  - Current stable fallback: `EMBEDDING_BACKEND=hash` in the user service.
    This keeps the OpenAI-compatible 384-dim embedding endpoint responsive when
    torch/sentence-transformers initialization blocks in D-state.

## Verify

```bash
# LiteLLM
systemctl --user is-active litellm litellm-strip-proxy
systemctl --user is-active litellm-keepalive.timer
curl -s --noproxy '*' -H "Authorization: Bearer sk-litellm-charlie-2026" http://127.0.0.1:4002/v1/models | jq '.data | length'
curl -s --noproxy '*' http://127.0.0.1:4000/v1/models | jq '.data | length'

# Letta
systemctl --user is-active letta-stack
curl -s --noproxy '*' http://127.0.0.1:8283/v1/agents/ | jq 'length'

# Embedding
systemctl --user is-active embedding-server
curl -s --noproxy '*' http://127.0.0.1:8286/health
```

## Restart

```bash
# LiteLLM（改配置后）
systemctl --user restart litellm && systemctl --user restart litellm-strip-proxy

# Letta 全栈重启
systemctl --user restart letta-stack
# 容器内单独重启：cd ~/ai/letta && docker compose restart letta

# Embedding
systemctl --user restart embedding-server
```

## Known Issues

- Letta 连接重置 = NLTK 数据初始化阻塞，需传 `http_proxy` 环境变量 + 等待 60s+
- Letta `/health` 返回 404 是正常的，正确端点为 `/v1/agents/`
- If OpenHands starts but conversation creation returns 500 and both `4000` and
  `8283` are closed, first start `litellm.service`,
  `litellm-strip-proxy.service`, `letta-stack.service`, and
  `letta-podman-proxy.service`; do not edit OpenHands code first.
- LiteLLM 配置修改后必须同时重启 strip-proxy
- 2026-07-04 强制保活：`~/.local/bin/litellm-keepalive` 接管 4002/4000 健康巡检。它会读取 `~/ai/litellm.env` 的 `LITELLM_MASTER_KEY` 做带鉴权探测，并用 flock 防止 timer 与人工重启并发。日志在 `~/.local/state/litellm-keepalive.log`。
- 2026-07-04 Claude Code 兼容：`claude-sonnet-4-6-20250514`、`claude-sonnet-4-5-20250514`、`claude-haiku-4-5-20251001`、`claude-opus-4-6-20250514` 已加入 LiteLLM fallback 链。若 ZAI 余额/资源包不足，应降级到 `glm-5.2`、`step-3.7-flash`、`step-3.5-flash-2603`、`deepseek-v4-*`，不要让 OpenCode 直接卡在单一 Claude 别名。
- Letta 容器重建后 PG 连接失败 → 检查 `pg_hba.conf` 网络段是否匹配新容器 IP
- Letta archival passage 的 API 响应可能长期显示 `embedding=null`；不要仅凭 `/archival-memory/search` 语义搜索判断记忆是否存在。先用 `/archival-memory?search=<term>&limit=...` 文本检索验证，再看 OpenCode 生命周期脚本是否注入。
- `embedding-server.service` may run in hash fallback mode. In that mode
  `curl http://127.0.0.1:8286/` should return
  `{"status":"ok","model":"hash-fallback-384","dim":384}` immediately.
  If using the real sentence-transformers backend, first request may trigger
  model loading and should eventually return `all-MiniLM-L6-v2`.
- 2026-06-25 修复 Letta `embedding=null`：
  - `fedora-sysadmin` agent 必须有 `embedding_config`，当前应为 OpenAI-compatible endpoint `http://10.88.0.1:8286/v1`，model `all-MiniLM-L6-v2`，dim `384`，handle `local/all-MiniLM-L6-v2`。
  - `embedding-server.service` 必须监听 `0.0.0.0:8286`，否则 Letta 容器无法连接宿主的 `127.0.0.1`。
  - Do not use `host.containers.internal:8286` for Letta embedding on this host:
    it has resolved to stale LAN IPs such as `192.168.123.157`. Letta also runs
    with `HTTP_PROXY`; keep `NO_PROXY/no_proxy` including `10.88.0.1` or
    embedding requests may be sent to the proxy and hang.
  - Persistent compose config is `/mnt/ai/ai-cluster/letta/docker-compose.yml`;
    keep `LETTA_EMBEDDING_BASE_URL=http://10.88.0.1:8286/v1` there.
  - 历史 null passage 已通过 create-then-delete backfill 重建；备份在 `~/.local/state/letta-audit/backfill-null-passages-1782394958.jsonl`。
  - 验证：`curl http://127.0.0.1:8283/v1/agents/ | jq '.[0].embedding_config'` 非空；枚举 archival memory 时 `nulls=0`；容器内 `10.88.0.1:8286/v1/embeddings` 返回 384 维。
- 2026-07-09 OpenHands/Letta write timeout diagnosis:
  - Letta archival writes timed out because the agent embedding endpoint was
    still `host.containers.internal:8286/v1`, which routed to a stale address
    and then through `HTTP_PROXY`.
  - The agent was patched via `PATCH /v1/agents/{agent_id}` to
    `http://10.88.0.1:8286/v1`; the compose file was patched to persist the same
    endpoint and proxy bypass.
  - During recreate, rootless Podman control commands started hanging because
    stale `podman healthcheck run` and another `podman rm` held the sqlite
    database while old `letta` was stuck in `Removing`. Recovery used:
    `pkill -f 'podman healthcheck run'`, wait for other podman rm operations to
    finish, then `podman container cleanup letta && podman rm -f --ignore letta`,
    followed by `cd /mnt/ai/ai-cluster/letta && docker compose up -d letta`.
  - Verified fixed state: `curl http://127.0.0.1:8283/v1/health/` returns
    version/status ok, archival write returns 200, and Letta logs show
    `POST http://10.88.0.1:8286/v1/embeddings "HTTP/1.0 200 OK"`.
