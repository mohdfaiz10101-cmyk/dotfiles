# 决策记忆

此文件只记录“最终采用的方案”和“以后应默认遵循的决策”。

## 2026-06-02
- `oc` 必须对齐 `19890/openclaw` 入口，不能再漂到监控窗口。
- `Claude CLI` 在本机 LiteLLM 下默认应走 `ANTHROPIC_AUTH_TOKEN`，不要再混用 `claude.ai OAuth + API key`。
- `waybar` 继续保留，但应降级为聚合后的告警出口，不能再承担分散探测核心逻辑。
- `hub:9800/dashboard` 作为统一看板页面，工作区固定到 `workspace 6`。

## 2026-06-02T00:51:03
- 任务: test only: print one line and exit
- 根因: 未解析
- 修法: 需人工补充
- 最终决策: json
{
  "root_cause": "The task was a simple test to print one line and exit, which was successfully executed.",
  "fix": "No fix required as the task completed as expected.",
  "failed_attempts": "None",
  "decision": "The task was completed successfully without any issues.",
  "score": 100
}

- 评分: 5
