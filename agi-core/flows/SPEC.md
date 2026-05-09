# LangGraph 工作流体系规范

## ⚠️ 安全层（所有工作流强制遵守，最高优先级）

### 危险命令拦截（HITL 强制介入）
以下命令模式 **必须** 暂停等待用户确认，禁止自动执行：
```python
DANGEROUS_PATTERNS = [
    r"\brm\s+-rf?\b",          # 删除文件
    r"\bdd\b",                  # 磁盘写入
    r"\bmkfs\b",                # 格式化
    r"\bfdisk\b",               # 分区
    r"systemctl\s+(stop|disable|mask)",  # 停服务
    r"nixos-rebuild",           # 系统重建
    r"nix-collect-garbage",     # 垃圾回收
    r"docker\s+(rm|rmi|prune)", # 删容器/镜像
    r"\bchmod\s+777\b",         # 危险权限
    r">\s*/etc/",               # 覆盖系统文件
    r"DROP\s+TABLE",            # 删数据库
]
```

### bash 工具安全包装（所有工作流必须用这个版本）
```python
import re, json, subprocess
from langchain_core.tools import tool

DANGEROUS_PATTERNS = [
    r"\brm\s+-rf?\b", r"\bdd\b", r"\bmkfs\b", r"\bfdisk\b",
    r"systemctl\s+(stop|disable|mask)", r"nixos-rebuild",
    r"nix-collect-garbage", r"docker\s+(rm|rmi|prune)",
    r">\s*/etc/", r"DROP\s+TABLE",
]

SAFE_ALLOWLIST = [
    r"systemctl\s+(status|is-active|restart|start)",  # 启动/重启 OK
    r"journalctl", r"df\s", r"free\s", r"top\s", r"ps\s",
]

@tool
def bash_safe(command: str, timeout: int = 30) -> str:
    """执行 shell 命令（带安全检查）。危险命令会被拦截并返回 BLOCKED。"""
    # 白名单直接通过
    for safe in SAFE_ALLOWLIST:
        if re.search(safe, command): break
    else:
        # 检查危险模式
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return f"[BLOCKED] 危险命令被拦截: {command}\n需要人工确认后才能执行。"
    try:
        r = subprocess.run(command, shell=True, capture_output=True,
                           text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip()[:4000] or "(no output)"
    except subprocess.TimeoutExpired:
        return f"[超时 {timeout}s]"
```

### L3 生成工作流安全门
自动生成的工作流 **禁止直接注册运行**，必须经过：
1. `bash -n {file}` 语法检查
2. 扫描生成代码中的危险模式
3. 写入 `flows/pending/{name}.py`（不是 flows/ 根目录）
4. 发 Telegram 通知用户审核
5. 用户回复确认 → 移动到 `flows/{name}.py` → 注册 index.json

### 操作审计日志
所有工作流执行必须记录到 `~/.local/share/macg/audit.log`：
```
2026-04-18 00:30 [self_heal] DiskFix bash("df -h /mnt/ai") → OK
2026-04-18 00:30 [self_heal] ServiceFix bash("systemctl restart litellm") → OK
2026-04-18 00:31 [self_heal] BLOCKED bash("rm -rf /tmp/cache") → 等待确认
```

---

## 目录结构
```
~/agi/flows/
├── SPEC.md          # 本文件，OP 必读
├── index.json       # 工作流注册表（自动维护）
├── self_heal.py     # ① 自愈巡检
├── task_decompose.py # ② 任务分解器
├── code_loop.py     # ③ 代码变更闭环
├── evolve.py        # L2 自动优化层
└── workflow_gen.py  # L3 工作流生成器
```

## 公共依赖
```bash
cd ~/agi && source .venv/bin/activate
pip install langgraph langgraph-checkpoint-sqlite langchain-anthropic langchain-openai
```

## 工具复用（macg.py 已定义，直接 import）
```python
from macg import bash, read_file, write_file, glob_files, grep_files, \
                 op_delegate, memory_read, memory_write, web_search, TOOLS
```

## 模型配置
```python
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

claude = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=4096)
glm = ChatOpenAI(model="glm-5-turbo", base_url="http://localhost:4000/v1",
                 api_key="sk-litellm-charlie-2026", max_tokens=2000)
```

## 持久化（统一用同一个 DB）
```python
from langgraph.checkpoint.sqlite import SqliteSaver
DB = "/home/charlie/.local/share/macg/state.db"
# with SqliteSaver.from_conn_string(DB) as cp: ...
```

## ① self_heal.py 规范
节点：Sense → Classify → 并行(DiskFix | ServiceFix | ProxyFix) → Verify → 重试最多2次 → HITL(interrupt_before) → Merge → Report
- Sense：复用 brain.py 的 sense() 函数
- Fix 节点：用 bash 工具执行修复命令
- Verify：bash 验证修复结果
- HITL：`interrupt_before=["human_review"]`，等用户确认
- Report：写 Telegram（复用 brain.py _send_telegram）

## ② task_decompose.py 规范
节点：ParseIntent(GLM) → Decompose(GLM,输出子任务列表) → Send()并行 → 各自ReAct → Aggregate → Verify(Claude) → END或Retry
- 用 LangGraph Send() API 实现动态并行
- 每个子任务独立 ReAct agent
- 汇聚后 Claude 验证完整性

## ③ code_loop.py 规范
节点：Spec → CodeGen(Claude) → RunTests(bash pytest) → FixLoop(最多3次) → HumanReview(HITL) → Deploy(op_delegate)
- 失败自动提取错误信息传给下一次 CodeGen
- 超过3次写入 lessons-learned.md 并停止

## L2 evolve.py 规范
- 每个工作流节点执行后记录到 ~/.local/share/macg/metrics.json
- 格式：{flow_name, node_name, success, duration, error, timestamp}
- 每天检查：节点成功率 < 60% → 触发优化
- 优化：把失败样本给 Claude → 生成新节点代码 → 写回对应 .py 文件

## L3 workflow_gen.py 规范
- 监听 ~/agi/flows/requests/ 目录
- 新建 request.json → 读取用户需求
- Claude 生成 LangGraph 图代码 → 写入 flows/auto_{name}.py
- bash 运行语法检查 → 通过则注册到 index.json
- 失败写 lessons-learned.md

## index.json 格式
```json
{
  "flows": [
    {
      "name": "self_heal",
      "file": "self_heal.py",
      "trigger": ["disk", "service", "proxy", "巡检", "修复"],
      "created": "2026-04-18",
      "success_rate": 0.0,
      "runs": 0
    }
  ]
}
```

## orchestrator.py 路由规则
```python
ROUTES = {
    "op":    r"nixos|systemctl|docker|磁盘|服务|重启|运维|定时",
    "cc":    r"代码|函数|bug|重构|架构|nix配置|复杂",
    "flows": r"巡检|修复|自愈|分解任务|代码变更|部署",
    "macg":  r".*"  # 兜底
}
```

## OP 自主检测规则（死规则）
1. 每次完成一个 flow 实现 → 更新 index.json
2. 每次运行 flow → 记录到 metrics.json
3. 每天检查 metrics → 触发 L2 优化
4. 发现新的重复任务模式 → 触发 L3 生成新工作流
5. 所有生成的代码 → bash -n 语法检查后才注册
