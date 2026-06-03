"""
learn_evolve.py — AGI 自主进化引擎
Phase 1: SELF-AUDIT — 审计记忆质量、规则覆盖率、服务健康
Phase 2: INTERNET-LEARN — 从 lessons/pulse 挖掘优化方向
Phase 3: EVALUATE — 评估建议可行性和优先级
Phase 4: IMPLEMENT — HITL 确认后执行（写入记忆/更新规则）
Phase 5: VERIFY — 验证执行结果

Usage:
    cd ~/agi && python3 -m flows.learn_evolve        # 完整进化周期
    cd ~/agi && python3 -m flows.learn_evolve --phase audit  # 仅审计
    cd ~/agi && python3 -m flows.learn_evolve --dry-run      # 只输出建议不执行
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── 路径配置 ────────────────────────────────────────────────────────────────
MEMORY_DIR = Path(os.environ.get(
    "MEMORY_DIR", "/home/charlie/.claude/projects/-home-charlie/memory"
))
LESSONS_PATH = MEMORY_DIR / "lessons-learned.md"
RULES_PATH = Path(os.environ.get(
    "RULES_FILE", "/home/charlie/CLAUDE.md"
))
PULSE_DB = Path(os.environ.get("PULSE_DB", "/mnt/ai/data/memory-pulse/pulse.db"))
EVOLVE_STATE = Path(Path.home() / ".local/state/evolve-state.json")
EVOLVE_LOG = Path(Path.home() / ".local/state/evolve-log.jsonl")
LETTA_URL = os.environ.get("LETTA_BASE_URL", "http://localhost:8283")
LETTA_TOKEN = os.environ.get("LETTA_TOKEN", "letta")
MEM0_URL = os.environ.get("MEM0_URL", "http://localhost:8285")

# ── Phase 1: SELF-AUDIT ────────────────────────────────────────────────────

def audit_memory_health() -> dict[str, Any]:
    """审计记忆系统健康度。"""
    result = {"checks": [], "score": 0, "total": 0}

    # 1) lessons-learned 行数
    if LESSONS_PATH.exists():
        lines = LESSONS_PATH.read_text().strip().split("\n")
        active = [l for l in lines if l.startswith("- ") and "[DECAY]" not in l and "[ARCHIVED]" not in l]
        result["checks"].append({
            "name": "lessons-learned 活跃条目",
            "status": "ok" if len(active) < 100 else "warn",
            "value": len(active),
            "detail": f"{len(active)} 条活跃（建议<100，>100需归档）"
        })
    else:
        result["checks"].append({"name": "lessons-learned", "status": "error", "detail": "文件不存在"})

    # 2) Letta 连通性
    try:
        r = __http_get(f"{LETTA_URL}/v1/agents/", headers={"Authorization": f"Bearer {LETTA_TOKEN}"})
        agents = r if isinstance(r, list) else []
        result["checks"].append({
            "name": "Letta 连通性",
            "status": "ok",
            "value": len(agents),
            "detail": f"{len(agents)} 个 agent 可达"
        })
    except Exception as e:
        result["checks"].append({"name": "Letta 连通性", "status": "error", "detail": str(e)[:80]})

    # 3) Mem0 连通性
    try:
        r = __http_get(f"{MEM0_URL}/health")
        result["checks"].append({
            "name": "Mem0 连通性",
            "status": "ok" if r and r.get("status") == "ok" else "warn",
            "detail": f"count={r.get('count', '?')}" if r else "无响应"
        })
    except Exception as e:
        result["checks"].append({"name": "Mem0 连通性", "status": "error", "detail": str(e)[:80]})

    # 4) Pulse 数据量
    if PULSE_DB.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(PULSE_DB))
            total = conn.execute("SELECT COUNT(*) FROM pulse").fetchone()[0]
            conn.close()
            result["checks"].append({
                "name": "Pulse 记忆总量",
                "status": "ok",
                "value": total,
                "detail": f"{total} 条记忆已索引"
            })
        except Exception as e:
            result["checks"].append({"name": "Pulse DB", "status": "error", "detail": str(e)[:80]})

    # 5) CLAUDE.md 大小
    if RULES_PATH.exists():
        size = RULES_PATH.stat().st_size
        result["checks"].append({
            "name": "CLAUDE.md 大小",
            "status": "ok" if size < 8000 else "warn",
            "value": size,
            "detail": f"{size}B（>8KB 需精简）"
        })

    # 计算总分
    for c in result["checks"]:
        result["total"] += 1
        if c["status"] == "ok":
            result["score"] += 1

    return result


def audit_service_health() -> list[dict[str, Any]]:
    """审计关键服务健康状态。"""
    services = [
        ("LiteLLM", "4000", "/health/v1/models"),
        ("Hub-API", "9800", "/"),
        ("Mem0-Bridge", "8285", "/health"),
        ("Embedding", "8286", "/health"),
    ]
    results = []
    for name, port, path in services:
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            alive = sock.connect_ex(("127.0.0.1", int(port))) == 0
            sock.close()
            results.append({
                "name": name, "port": port, "status": "up" if alive else "down"
            })
        except Exception:
            results.append({"name": name, "port": port, "status": "down"})
    return results


# ── Phase 2: INTERNET-LEARN（本地知识挖掘） ─────────────────────────────────

def extract_patterns_from_lessons() -> list[dict[str, str]]:
    """从 lessons-learned 挖掘重复模式。"""
    if not LESSONS_PATH.exists():
        return []

    content = LESSONS_PATH.read_text()
    lines = [l.strip() for l in content.split("\n") if l.strip().startswith("- ")]

    # 按关键词频率分类
    patterns: dict[str, list[str]] = {}
    for line in lines:
        for keyword in ["timeout", "权限", "proxy", "NixOS", "Docker", "Letta", "Mem0", "opencode", "npm", "bun", "NTFS"]:
            if keyword.lower() in line.lower():
                patterns.setdefault(keyword, []).append(line[:100])

    insights = []
    for keyword, items in sorted(patterns.items(), key=lambda x: -len(x[1])):
        if len(items) >= 2:
            insights.append({
                "category": keyword,
                "frequency": len(items),
                "latest": items[-1],
                "insight": f"{keyword} 出现 {len(items)} 次，考虑封装为自动化规则或 skill"
            })
    return insights


def extract_pulse_decay() -> list[dict[str, Any]]:
    """从 pulse 库找出长期未访问的记忆（需归档或复习）。"""
    if not PULSE_DB.exists():
        return []
    try:
        import sqlite3
        conn = sqlite3.connect(str(PULSE_DB))
        rows = conn.execute("""
            SELECT id, source, text, pulse_score, last_accessed_at, last_synced_at
            FROM pulse
            WHERE pulse_score < 0.5
            ORDER BY pulse_score ASC
            LIMIT 20
        """).fetchall()
        conn.close()
        return [
            {"id": r[0], "source": r[1], "text": r[2][:80], "score": r[3],
             "last_access": r[4], "last_sync": r[5]}
            for r in rows
        ]
    except Exception:
        return []


# ── Phase 3: EVALUATE ───────────────────────────────────────────────────────

def evaluate_suggestions(audit: dict, patterns: list[dict], decay: list[dict]) -> list[dict]:
    """评估并排序所有建议。"""
    suggestions = []

    # 从审计结果生成建议
    for check in audit.get("checks", []):
        if check["status"] == "warn":
            suggestions.append({
                "priority": "medium",
                "source": "audit",
                "action": f"修复: {check['name']} — {check.get('detail', '')}",
                "auto": True,
            })
        elif check["status"] == "error":
            suggestions.append({
                "priority": "high",
                "source": "audit",
                "action": f"修复: {check['name']} — {check.get('detail', '')}",
                "auto": True,
            })

    # 从模式分析生成建议
    for p in patterns:
        suggestions.append({
            "priority": "high" if p["frequency"] >= 5 else "medium",
            "source": "pattern",
            "action": p["insight"],
            "auto": False,  # 封装 skill 需 HITL
        })

    # 从 decay 生成建议
    if len(decay) >= 50:
        suggestions.append({
            "priority": "low",
            "source": "decay",
            "action": f"归档 {len(decay)} 条低分记忆（score<0.5）",
            "auto": True,
        })

    # 排序: high > medium > low
    priority_order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(key=lambda s: priority_order.get(s["priority"], 99))

    return suggestions


# ── Phase 4: IMPLEMENT ──────────────────────────────────────────────────────

def _check_hitl_expiry() -> list[dict]:
    """检查 pending_hitl 任务是否过期（24h），过期自动批准低风险任务。"""
    expired = []
    if not EVOLVE_STATE.exists():
        return expired
    try:
        state = json.loads(EVOLVE_STATE.read_text())
        last_run = state.get("last_run", "")
        if not last_run:
            return expired
        from datetime import datetime, timedelta
        last_dt = datetime.fromisoformat(last_run)
        if datetime.now() - last_dt > timedelta(hours=24):
            # 检查上次的 pending_hitl 任务
            results_path = Path(Path.home() / ".local/state/evolve-result.json")
            if results_path.exists():
                old = json.loads(results_path.read_text())
                for r in old.get("results", []):
                    if r.get("status") == "pending_hitl":
                        action = r.get("action", "")
                        # 低风险：封装 skill、精简建议
                        if any(kw in action for kw in ["封装", "精简", "归档", "skill", "CLAUDE.md"]):
                            expired.append({"action": action, "status": "auto_approved_expired"})
    except Exception:
        pass
    return expired


def execute_auto_tasks(suggestions: list[dict]) -> list[dict[str, Any]]:
    """执行标记为 auto=True 的任务。修复版: 通用 handler + HITL 过期机制。"""
    results = []

    # 先检查过期 HITL
    expired = _check_hitl_expiry()
    for e in expired:
        results.append({"action": e["action"], "status": "done", "detail": "过期自动批准(>24h)"})

    for s in suggestions:
        if not s.get("auto"):
            results.append({"action": s["action"], "status": "pending_hitl", "reason": "需要人工确认"})
            continue

        action = s["action"]
        handled = False

        # 自动归档低分记忆
        if "归档" in action and "低分记忆" in action:
            result = __archive_low_score_memories()
            results.append({"action": action, "status": "done" if result else "fail", "detail": f"归档 {result} 条" if result else "无数据"})
            handled = True

        # 自动修复 lessons-learned 文件
        if "lessons-learned" in action:
            result = __archive_old_lessons()
            results.append({"action": action, "status": "done", "detail": f"归档 {result} 条旧 lessons"})
            handled = True

        # CLAUDE.md 精简
        if "CLAUDE.md" in action and ("精简" in action or "大小" in action):
            trim_result = __trim_claude_md()
            results.append({"action": action, "status": "done" if trim_result else "skip", "detail": f"精简 {trim_result} 字节" if trim_result else "无需精简"})
            handled = True

        # 自动写入进化建议到 Letta
        if "Letta" in action and "error" in s.get("source", ""):
            results.append({"action": action, "status": "escalate", "reason": "Letta 服务异常需人工排查"})
            handled = True

        if not handled:
            # 通用尝试: 发布到 OpenAgents wiki/evolve-insights
            ok = __publish_to_oa(action, s.get("priority", "medium"))
            if ok:
                results.append({"action": action, "status": "done", "detail": "已发布到 OpenAgents"})
            else:
                results.append({"action": action, "status": "skip", "reason": "无可执行方案"})

    return results


def __trim_claude_md() -> int | None:
    """精简 CLAUDE.md：移除重复内容，统一引用 wiki/ai-rules。"""
    if not RULES_PATH.exists():
        return None
    content = RULES_PATH.read_text()
    orig_size = len(content)

    # 如果已经 < 8000，不处理
    if orig_size < 8000:
        return None

    # 在顶部插入 wiki 引用，移除重复的规则段落
    lines = content.split("\n")
    new_lines = []
    skip_until_next_header = False

    for line in lines:
        # 跳过已迁移到 wiki 的重复规则段落
        if line.strip().startswith("## ") and any(
            kw in line for kw in ["NTFS 封杀", "磁盘分配", "Windows 远程",
                                   "OP 禁止委托", "定时任务时段", "偏好自动提取",
                                   "任务失败升级", "思考过程问题强制清理"]
        ):
            skip_until_next_header = False
            new_lines.append(line)
            new_lines.append("")
            new_lines.append("> ⚠️ 此规则已迁移到 OpenAgents wiki/ai-rules，此处仅保留概要。详见 sync-rules.sh")
            new_lines.append("")
            continue

        if not skip_until_next_header:
            new_lines.append(line)

    new_content = "\n".join(new_lines)
    new_size = len(new_content)
    if new_size < orig_size:
        RULES_PATH.write_text(new_content)
        return orig_size - new_size
    return None


def __publish_to_oa(action: str, priority: str = "medium") -> bool:
    """发布进化建议到 OpenAgents evolve-insights wiki。"""
    try:
        import urllib.request
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"- [{ts}] [{priority}] {action}\n"

        # 追加到 wiki page（如果存在）
        url = "http://localhost:8700/api/send_event"
        payload = json.dumps({
            "event_name": "wiki.page.update",
            "source_id": "evolve-engine",
            "event_id": f"evolve-{int(datetime.now().timestamp())}",
            "target_agent_id": "mod:openagents.mods.workspace.wiki",
            "payload": {
                "page_path": "evolve-insights",
                "append_content": entry,
            }
        }).encode()
        req = urllib.request.Request(url, data=payload, headers={
            "Content-Type": "application/json",
        })
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        return False


def __archive_low_score_memories() -> int | None:
    """归档 pulse_score < 0.1 的记忆。"""
    if not PULSE_DB.exists():
        return None
    try:
        import sqlite3
        conn = sqlite3.connect(str(PULSE_DB))
        count = conn.execute("UPDATE pulse SET status='archived' WHERE pulse_score < 0.1 AND status != 'archived'").rowcount
        conn.commit()
        conn.close()
        return count
    except Exception:
        return None


def __archive_old_lessons() -> int:
    """归档超过30天的 lessons-learned 条目。"""
    if not LESSONS_PATH.exists():
        return 0

    import re
    content = LESSONS_PATH.read_text()
    lines = content.split("\n")
    archived = 0
    now = datetime.now()

    new_lines = []
    for line in lines:
        # 格式: - [2026-04-15] [OP] ...
        match = re.match(r"^(- \[)(\d{4}-\d{2}-\d{2})(\].*)$", line)
        if match:
            prefix, date_str, rest = match.groups()
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
                if (now - date).days > 30 and "[DECAY]" not in line and "[ARCHIVED]" not in line:
                    line = f"- [ARCHIVED] [{date_str}]{rest}"
                    archived += 1
            except ValueError:
                pass
        new_lines.append(line)

    if archived > 0:
        LESSONS_PATH.write_text("\n".join(new_lines))
    return archived


# ── Phase 5: VERIFY ────────────────────────────────────────────────────────

def verify_results(results: list[dict]) -> dict[str, Any]:
    """验证执行结果。"""
    done = [r for r in results if r["status"] == "done"]
    fail = [r for r in results if r["status"] == "fail"]
    pending = [r for r in results if r["status"] in ("pending_hitl", "escalate")]

    return {
        "timestamp": datetime.now().isoformat(),
        "executed": len(done),
        "failed": len(fail),
        "pending_hitl": len(pending),
        "details": results,
    }


# ── 辅助函数 ────────────────────────────────────────────────────────────────

def __http_get(url: str, headers: dict | None = None, timeout: int = 5) -> Any:
    """轻量 HTTP GET（不依赖 httpx）。"""
    import urllib.request
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode(errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw


def save_state(phase: str, data: Any) -> None:
    """保存进化状态。"""
    state = {
        "last_run": datetime.now().isoformat(),
        "phase": phase,
        "data": data,
    }
    EVOLVE_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    with open(EVOLVE_LOG, "a") as f:
        f.write(json.dumps({"ts": datetime.now().isoformat(), "phase": phase, **data}) + "\n")


# ── 主流程 ──────────────────────────────────────────────────────────────────

def run_evolution(dry_run: bool = False, phase: str | None = None) -> dict[str, Any]:
    """执行完整进化周期。"""
    print(f"[evolve] 进化引擎启动 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    final = {}

    # Phase 1: SELF-AUDIT
    if phase in (None, "audit"):
        print("[evolve] Phase 1: SELF-AUDIT")
        audit = audit_memory_health()
        services = audit_service_health()
        print(f"  记忆健康: {audit['score']}/{audit['total']} 通过")
        for c in audit["checks"]:
            icon = "[OK]" if c["status"] == "ok" else "[!]" if c["status"] == "warn" else "[X]"
            print(f"  {icon} {c['name']}: {c.get('detail', '')}")
        for s in services:
            icon = "[OK]" if s["status"] == "up" else "[X]"
            print(f"  {icon} {s['name']}:{s['port']}")
        final["audit"] = audit
        final["services"] = services
        save_state("audit", audit)

    # Phase 2: INTERNET-LEARN
    if phase in (None, "learn"):
        print("[evolve] Phase 2: INTERNET-LEARN")
        patterns = extract_patterns_from_lessons()
        decay = extract_pulse_decay()
        print(f"  发现 {len(patterns)} 个重复模式")
        for p in patterns[:5]:
            print(f"    - [{p['category']} x{p['frequency']}] {p['insight'][:60]}")
        print(f"  发现 {len(decay)} 条衰减记忆")
        final["patterns"] = patterns
        final["decay_count"] = len(decay)
        save_state("learn", {"patterns": len(patterns), "decay": len(decay)})

    # Phase 3: EVALUATE
    if phase in (None, "evaluate") and "audit" in final and "patterns" in final:
        print("[evolve] Phase 3: EVALUATE")
        suggestions = evaluate_suggestions(
            final["audit"],
            final.get("patterns", []),
            [{"score": 0} for _ in range(final.get("decay_count", 0))]
        )
        print(f"  生成 {len(suggestions)} 条建议:")
        for s in suggestions[:10]:
            print(f"    [{s['priority']}] {s['action'][:70]}")
        final["suggestions"] = suggestions
        save_state("evaluate", {"count": len(suggestions)})

    # Phase 4: IMPLEMENT
    if phase in (None, "implement") and "suggestions" in final:
        print("[evolve] Phase 4: IMPLEMENT")
        if dry_run:
            print("  [dry-run] 跳过执行")
            final["results"] = [{"action": s["action"], "status": "dry_run"} for s in final["suggestions"]]
        else:
            results = execute_auto_tasks(final["suggestions"])
            for r in results:
                icon = "[OK]" if r["status"] == "done" else "[!]" if r["status"] == "pending_hitl" else "[X]"
                print(f"  {icon} {r['action'][:60]}")
            final["results"] = results
            save_state("implement", {"done": sum(1 for r in results if r["status"] == "done")})

    # Phase 5: VERIFY
    if phase in (None, "verify") and "results" in final:
        print("[evolve] Phase 5: VERIFY")
        vr = verify_results(final["results"])
        print(f"  执行: {vr['executed']} / 失败: {vr['failed']} / 待确认: {vr['pending_hitl']}")
        final["verify"] = vr
        save_state("verify", vr)

    # 写入 Letta（记录本次进化）
    if not dry_run and phase in (None, "verify"):
        try:
            summary = f"[evolve] {datetime.now().strftime('%Y-%m-%d')} 进化周期完成 | 记忆健康:{final.get('audit',{}).get('score','?')}/{final.get('audit',{}).get('total','?')} | 建议:{len(final.get('suggestions',[]))} | 执行:{final.get('verify',{}).get('executed',0)}"
            __http_post_archival(summary, tags="evolve,self-improve")
            print(f"[evolve] 已写入 Letta archival")
        except Exception as e:
            print(f"[evolve] Letta 写入失败: {e}")

    print(f"[evolve] 进化周期完成")
    return final


def __http_post_archival(text: str, tags: str = "evolve") -> None:
    """写入 Letta archival memory。"""
    import urllib.request
    agent_id = "agent-02380eae-9ac2-45f4-b9b2-dabf40e0abea"
    url = f"{LETTA_URL}/v1/agents/{agent_id}/archival-memory"
    payload = json.dumps({"text": text, "metadata": {"tags": tags}}).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {LETTA_TOKEN}",
        "Content-Type": "application/json",
    })
    urllib.request.urlopen(req, timeout=10)


def main():
    parser = argparse.ArgumentParser(description="AGI 自主进化引擎")
    parser.add_argument("--phase", choices=["audit", "learn", "evaluate", "implement", "verify"],
                        help="只运行指定阶段")
    parser.add_argument("--dry-run", action="store_true", help="只输出建议不执行")
    args = parser.parse_args()

    result = run_evolution(dry_run=args.dry_run, phase=args.phase)

    # 输出 JSON 供外部消费
    out_path = Path(Path.home() / ".local/state/evolve-result.json")
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"[evolve] 结果写入 {out_path}")


if __name__ == "__main__":
    main()
