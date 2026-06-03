"""
safe_tools.py — 安全工具层
所有 flows/ 工作流必须从这里 import 工具，禁止直接用 macg.TOOLS
"""

import re, json, subprocess
from pathlib import Path
from datetime import datetime
from langchain_core.tools import tool

AUDIT_LOG = Path.home() / ".local/share/macg/audit.log"
AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

DANGEROUS_PATTERNS = [
    r"\brm\s+-rf?\b", r"\bdd\b", r"\bmkfs\b", r"\bfdisk\b",
    r"systemctl\s+(stop|disable|mask)",
    r"nixos-rebuild", r"nix-collect-garbage",
    r"docker\s+(rm|rmi|prune)",
    r">\s*/etc/", r"DROP\s+TABLE",
]

SAFE_ALLOWLIST = [
    r"systemctl\s+(status|is-active|restart|start)",
    r"journalctl", r"df\s", r"free\s", r"top\s", r"ps\s",
    r"cat\s", r"ls\s", r"echo\s", r"grep\s", r"find\s",
    r"systemctl\s+--user",
]

def _audit(flow: str, node: str, command: str, result: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    status = "BLOCKED" if result.startswith("[BLOCKED]") else "OK"
    line = f"{now} [{flow}/{node}] bash({command[:60]!r}) → {status}\n"
    with open(AUDIT_LOG, "a") as f:
        f.write(line)

def _is_dangerous(command: str) -> bool:
    # 先检查危险模式
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            # 再看是否在白名单覆盖范围内
            for safe in SAFE_ALLOWLIST:
                if re.search(safe, command):
                    return False
            return True
    return False

@tool
def bash_safe(command: str, timeout: int = 30,
              flow: str = "unknown", node: str = "unknown") -> str:
    """执行 shell 命令（带安全检查 + 审计日志）。
    危险命令自动拦截返回 BLOCKED，需要 HITL 节点确认。"""
    if _is_dangerous(command):
        result = f"[BLOCKED] 危险命令被拦截，需人工确认: {command}"
        _audit(flow, node, command, result)
        return result
    try:
        r = subprocess.run(command, shell=True, capture_output=True,
                           text=True, timeout=timeout)
        out = (r.stdout + r.stderr).strip()[:4000] or "(no output)"
        _audit(flow, node, command, out)
        return out
    except subprocess.TimeoutExpired:
        return f"[超时 {timeout}s]"
    except Exception as e:
        return f"[FAIL] {e}"

# 原始函数版本（供 LangGraph 工作流直接调用，不走 StructuredTool 包装）
bash_safe_call = bash_safe.func

def check_generated_code(filepath: str) -> tuple[bool, str]:
    """检查 L3 生成的工作流代码安全性。
    返回 (is_safe, reason)"""
    content = Path(filepath).read_text()

    # 语法检查
    r = subprocess.run(f"python3 -m py_compile {filepath}",
                       shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        return False, f"语法错误: {r.stderr[:200]}"

    # 扫描危险模式
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return False, f"检测到危险模式: {pattern}"

    # 确保使用 bash_safe 而非 bash
    if "from macg import" in content and "bash" in content:
        if "bash_safe" not in content:
            return False, "使用了不安全的 bash 工具，必须改用 bash_safe"

    return True, "安全检查通过"
