# Hermes StepFun 双 Key 与模型分工

更新时间：2026-10-22。用户要求两个 key 都参与日常任务，避免长期仅消耗一份套餐。

## 当前配置

- 主入口：`~/.hermes/config.yaml` 的 `model.provider: stepfun`，默认 `step-5-preview`。
- `providers.stepfun` 使用 `https://api.stepfun.com/step_plan/v1`；`discover_models: false`，聊天列表仅 `step-router-v1`、`step-3.7-flash`、`step-5-preview`。语音/图片生成模型不放进通用聊天列表。
- `auth.json` 的 `credential_pool.stepfun` 仅两条手工凭据：`official5`（A 官方）、`50df07`（B 年包）。`credential_pool_strategies.stepfun: round_robin`。
- `suppressed_sources.stepfun: [env:STEPFUN_API_KEY]` 防止环境 key 自动注册成第三条重复凭据，使 A 获得双倍权重。保留 `.env` key 供兼容调用，不把 secret 写入文档。
- 常规任务轮换 A/B；原生轮换发生在凭据选择/新任务运行时，不承诺每个工具轮次或 token 用量严格 50/50。
- 当前安装版本 `agent/auxiliary_client.py::resolve_provider_client` 的显式通用 API-key 分支不使用轮换池，因此辅助任务显式配置 `key_env: STEPFUN_AUX_API_KEY`（B）和中国站 base URL。不要仅改 auxiliary.provider 后声称辅助任务已入池。
- B 辅助任务：标题/skills_hub/approval/mcp/curator 用 `step-3.7-flash`，压缩/网页提取/视觉用 `step-5-preview`。后两者及压缩 context_length 为 1024000。
- 七个私有 profiles（coding/research/monitor/creative/dispatcher/ops/secondary）默认均为 `step-5-preview`。每个 profile 独立持有同样两条凭据并轮换；不是跨进程全局严格排队。访客 profiles 未改。
- 别名：`daily`、`fast`、`deep`、`vision`。
- 旧 `providers.stepfun-router` / `stepfun-new` 和同名 custom provider 已移除；委派/fallback 改用原生 `stepfun`。旧会话若持久化旧 provider，需在模型选择器重新选择当前 StepFun 模型。

## 验证与陷阱

1. 两枚 key 分别直连三档模型均返回 HTTP 200；模型目录 200 不等于推理成功。
2. `resolve_runtime_provider(requested="stepfun")` 连续四次验证 B/A/B/A，池大小必须为 2。
3. 七个私有 profile 分别调用 `load_pool("stepfun").select()` 四次，均 A/B/A/B。
4. `_resolve_task_provider_model(task=...)` + `resolve_provider_client(...)` 验证 title_generation/compression/vision 使用 B 和中国站；标题真实推理成功。
5. `GET http://127.0.0.1:8787/api/models` 应为 active_provider=stepfun、default_model=step-5-preview，只出现一个 StepFun 分组、三个模型。此检查仅证明本机模型目录，不证明手机网络可用。
6. WebUI 重启后复核；网关使用 `systemctl --user reload hermes-gateway.service` 安全重载。配置变更不用改监听端口。

备份：`~/.hermes/backups/stepfun-balanced-20261022-174427/`，包含修改前 config/auth/.env。

不要重新引入单 key custom provider、环境重复池项，或用 `least_used` 替代当前持久化 round_robin；当前版本 least_used 计数只在内存递增。

运维记录：本次 WebUI 重启曾卡在 final-watchdog，主进程已退出，遗留 Notion MCP 子进程 PPID=systemd、阻塞 anon_pipe_write。确认仅残留子进程后用 `systemctl --user kill --kill-whom=all --signal=SIGKILL hermes-webui.service` 结束退出阶段，原重启作业继续，WebUI 恢复 active 且 /api/models=200。不要在主进程仍服务任务时照搬强杀。

用户明确修订：默认模型用 `step-5-preview`，两枚 key 继续 round_robin。`daily` 别名同步指向 step-5-preview；轻量辅助任务及 fallback 仍保留 step-3.7-flash。此偏好取代历史“主入口保持 router 默认”的建议。配置热重载后核验 /api/models 的 default_model；无需重启 WebUI 打断会话。

## 可见名称与真实账户归因（2026-10-22）

- 两枚凭据显示名改为 `A·官方` / `B·年包`；模型列表显示 `Step 5 Preview · A官方/B年包自动轮换`，仍用真正 model id 请求上游。
- WebUI `api/streaming.py::_extract_gateway_routing_metadata` 在本地 StepFun 回复完成后匹配 `agent.api_key` 与该 agent 自己的 `_credential_pool.entries()`，只保存非 secret 的 `credential_label`。不读取磁盘池的下一位来猜本次key。无匹配不归因，外部Gateway元数据保持原逻辑。
- 复用现有 `gateway_routing`、assistant `_gatewayRouting` 和 SSE usage 持久化/回放路径，`static/ui.js::_formatGatewayModelLabel` 将真实账户标签放在模型名之前；回复脚注、会话模型摘要、模型chip复用这一显示。历史没有记录的回复不伪造账户；一轮内发生故障转移时记录最终账户。
- `api/routes.py::_handle_live_models` 在TTL缓存和上游发现前尊重 `providers.<id>.discover_models: false` 的非空固定列表和label，防止后台enrichment冲掉名称并重新塞回语音模型。
- 验证：42项相关测试、JS运行时lint和Python编译通过；真实WebUI Step5 smoke会话已记录 B·年包，浏览器窄屏截图显示相同标签。证据目录 `~/.local/state/hermes-stepfun-labels/`。
- CodeGraph查询当前因Kuzu shadow文件缺失不可用；不要全home刷新。此次是在既有函数内添加显示归因和固定目录守卫，没有调整生产符号结构。

实测边界：测试会话首轮成功回复已持久化 `B·年包`；同会话后续探针触发了现有 `No response from provider` 终态，无账户元数据。不把错误回复或缺失历史归因为某枚key，也不把上一轮已知标签当作该失败请求的证据。命名任务未改动上游推理/错误恢复逻辑。

## 单账户显示纠正（2026-10-22）

用户再次指出不能始终并列显示两个账户。静态模型名统一为 `Step 5 Preview · 自动轮换`（其他两档同样仅保留自动轮换说明），provider名为 `StepFun · 自动轮换`。实际账户显示由运行时元数据单独提供；formatter在已知单个账户时移除模型标签末尾的“· 自动轮换”，显示 `A·官方 · Step 5 Preview` 或 `B·年包 · Step 5 Preview`。

`_live_usage_snapshot` 从当前agent凭据生成单个 `gateway_routing.credential_label` 随现有metering事件送出；前端只更新匹配会话的模型chip，并拒绝旧stream重放。完成后的持久化归因逻辑保持不变。不再等到回复完成才显示新任务当前选中的key。24项标签/回放/usage测试、JS runtime lint与Python编译通过；WebUI已重启。

上线实测：新建Step5验证会话的SSE metering在完成前给出 `A·官方`，done事件同样为 `A·官方`；历史成功回复仍为 `B·年包`。两者来自各自agent的真实凭据，不从配置顺序推断。测试会话完成后归档。
