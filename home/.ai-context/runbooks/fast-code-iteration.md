# Runbook: Fast Code Iteration

目标：用最少代码量、最小 diff、最快验证完成日常代码迭代。

## 默认自动入口

以后默认只用：

```bash
fast-code auto '<任务>'
# 等价短命令
fast-code go '<任务>'
```

自动决策会写备注：

```text
~/.local/state/fast-code/last-auto-decision.md
~/.local/state/fast-code/auto-decisions.jsonl
```

只看自动选择、不执行：

```bash
FAST_CODE_AUTO_DRY_RUN=1 fast-code auto '<任务>'
```

强制路由：

```bash
FAST_CODE_AUTO_ROUTE=aider fast-code auto '<任务>'
FAST_CODE_AUTO_ROUTE=goose fast-code auto '<任务>'
FAST_CODE_AUTO_ROUTE=op fast-code auto '<任务>'
FAST_CODE_AUTO_ROUTE=evolve-run fast-code auto '<任务>'
```

## 自动路由规则

`fast-code auto` 自动选择：

1. 若设置 `FAST_CODE_AUTO_ROUTE`，使用指定路由。
2. 当前目录存在 `initial_program.py` + `evaluator.py`，且任务像性能/算法/benchmark/evolve：走 `OpenEvolve`。
3. 任务像检查、复核、验证、审查、备注、小脚本：走 `Goose`。
4. 任务像部署、服务、端口、浏览器、系统、容器、数据库、跨服务、多步骤、安装：走 `OpenCode`。
5. 在 git 仓库内的普通代码修改：走 `Aider`，追求最小 diff。
6. 不在 git 仓库且无法判断：走 `OpenCode`。

## 手动入口

```bash
fast-code doctor
fast-code plan '<任务>'
fast-code aider '<小/中型明确代码修改>'
fast-code goose '<轻量自动执行/验证/第二助手任务>'
fast-code op '<复杂、多步骤、需要系统/浏览器验证的任务>'
fast-code evolve '<算法优化任务说明>'
fast-code evolve-run <initial_program.py> <evaluator.py> --iterations 20
```

## 选择规则补充

- 日常项目改代码：优先 `fast-code auto`；它通常会在 git 仓库里选 `Aider`。
- 轻量自动执行、复核、生成小脚本、独立验证：自动选 `Goose`。不要用 `goose doctor` 做轻量 smoke；用 `fast-code goose-smoke`。
- 长任务、跨服务、需要本机验证/浏览器/端口/系统状态：自动选 `OpenCode`。
- AlphaEvolve/OpenEvolve 类搜索优化：只有当任务有明确 evaluator/benchmark 时才用 `OpenEvolve`；否则先让 OP/Codex/Goose 写 evaluator。
- 不要为了“先进”而上重平台；先小 diff、先验证、再扩大范围。

## Goose 接入

本机 Goose 已配置在 `~/.config/goose/config.yaml`，默认走 LiteLLM provider。常用命令：

```bash
fast-code goose-smoke
fast-code goose '<让 Goose 做的轻量任务>'
```

`fast-code goose` 使用 `goose run --no-session --max-turns ${FAST_CODE_GOOSE_TURNS:-6}`，适合短执行和验证，不适合长期服务部署。

## OpenEvolve 接入

本机 OpenEvolve 安装在：

- repo: `~/ai/openevolve-lab/openevolve`
- venv: `~/ai/openevolve-lab/openevolve/.venv`
- wrapper: `~/.local/bin/openevolve-local`
- LiteLLM config: `~/.config/ai-code-loop/openevolve-litellm.yaml`

常用命令：

```bash
fast-code openevolve-doctor
openevolve-local help
openevolve-local example-smoke
fast-code evolve-run initial_program.py evaluator.py --iterations 20
```

默认 OpenEvolve 模型路径：

- API base: `http://127.0.0.1:4000/v1`
- primary: `glm-5.2`
- secondary: `step-3.5-flash-2603`

OpenEvolve 必须有 `initial_program.py` 和包含 `evaluate` 函数的 evaluator。没有 evaluator 时，先用：

```bash
fast-code auto '为当前仓库的目标函数设计最小 evaluator/benchmark，不改业务逻辑'
```

## 本机模型路径

`fast-code aider` 默认走本机 LiteLLM strip proxy：

- API base: `http://127.0.0.1:4000/v1`
- 默认主模型：`openai/glm-5.2`
- 默认弱模型：`openai/step-3.5-flash-2603`
- API key 从环境变量或 `~/ai/litellm.env` 读取；不要在文档/回答里暴露密钥。

## 验证

```bash
fast-code doctor
FAST_CODE_AUTO_DRY_RUN=1 fast-code auto '普通代码修改'
fast-code prompt '修一个小 bug' | head -40
fast-code goose-smoke
fast-code openevolve-doctor
```
