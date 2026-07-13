#!/run/current-system/sw/bin/python3
"""memory-injector.py — 将记忆注入所有 agent 配置文件
每30分钟由 timer 触发，确保 agent 总是带着最新记忆启动
"""
import os, subprocess, re, time, glob

MEMORY_DIR = os.path.expanduser("~/.claude/projects/-home-charlie/memory")
AGENTS_DIR = os.path.expanduser("~/.config/opencode/agents")
BASELINE = os.path.expanduser("~/.claude/projects/-home-charlie/memory/baseline.toml")

def get_latest_memories():
    """提取最近关键记忆, 返回 (memories, pref_count)"""
    memories = []
    pref_count = 0
    
    # 1. 用户偏好 (从 baseline)
    if os.path.exists(BASELINE):
        with open(BASELINE) as f:
            in_prefs = False
            for line in f:
                if "[preferences]" in line:
                    in_prefs = True
                    continue
                if in_prefs and line.startswith("["):
                    break
                if in_prefs and "=" in line:
                    k, v = line.split("=", 1)
                    memories.append(f"- {k.strip()}: {v.strip().strip('\"')}")
                    pref_count += 1
    
    # 2. 最近教训 (last 5 entries)
    lessons_file = os.path.join(MEMORY_DIR, "lessons-learned.md")
    if os.path.exists(lessons_file):
        with open(lessons_file) as f:
            lines = [l for l in f if l.startswith("- [202")]
        for l in lines[-5:]:
            # 截断长行
            short = l.strip()[:150]
            if short.endswith("---"): short = short[:-3]
            memories.append(short)
    
    return memories, pref_count

def build_injection_block():
    """构建注入文本块"""
    memories, pref_count = get_latest_memories()
    if not memories:
        return ""
    
    block = "\n<!-- memory-gate-inject: {} -->\n".format(time.strftime("%H:%M"))
    block += "## 已知上下文 (gate自动注入，强制执行)\n"
    
    for i, m in enumerate(memories):
        if i < pref_count:
            block += f"**偏好**: {m}\n"
        else:
            block += f"**教训**: {m}\n"
    
    block += "\n> 以上来自记忆系统，agent不需要自己搜索记忆。违反已知偏好=严重失误。\n"
    block += "<!-- /memory-gate-inject -->\n"
    return block

MAX_AGENT_SIZE_KB = 30  # agent 文件超过此值立即报警

def inject_into_file(filepath, block):
    """注入到 agent 文件"""
    with open(filepath, 'r') as f:
        content = f.read()

    # 替换旧注入（如果有）
    content = re.sub(r'<!-- memory-gate-inject:.*?<!-- /memory-gate-inject -->', '', content, flags=re.DOTALL)

    # 验证清理是否彻底（防止正则失效重演）
    remaining = len(re.findall(r'<!-- memory-gate-inject:', content))
    if remaining > 0:
        import sys
        print(f"[ERROR] {filepath}: 清理失败，仍有 {remaining} 个旧块！停止注入", file=sys.stderr)
        return False
    
    # 找到第一个 ## 或 # 标题后注入
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('#') and i > 0:
            # 在第一个标题行后插入
            result = '\n'.join(lines[:i+1]) + '\n' + block + '\n'.join(lines[i+1:])
            with open(filepath, 'w') as f:
                f.write(result)
            return True
    
    # 否则直接追加到头部
    with open(filepath, 'w') as f:
        f.write(block + '\n' + content)
    return True

def main():
    block = build_injection_block()
    if not block:
        print("[skip] 无新记忆")
        return
    
    count = 0
    # 只注入关键 agent（不是所有25个）
    key_agents = ["sisyphus.md", "cc-autonomous.md", "service-nurse.md", 
                  "ops-dispatcher.md", "security-watchdog.md", "proxy-guardian.md",
                  "charlie-ego.md"]
    
    for fname in key_agents:
        fpath = os.path.join(AGENTS_DIR, fname)
        if os.path.exists(fpath):
            inject_into_file(fpath, block)
            count += 1
    
    # 注入后检查文件大小
    for fname in key_agents:
        fpath = os.path.join(AGENTS_DIR, fname)
        if os.path.exists(fpath):
            size_kb = os.path.getsize(fpath) // 1024
            if size_kb > MAX_AGENT_SIZE_KB:
                print(f"[WARN] {fname} 大小 {size_kb}KB 超过 {MAX_AGENT_SIZE_KB}KB 阈值！")

    print(f"[ok] memory-injector: 已注入 {count} 个 agent 配置文件")

if __name__ == "__main__":
    main()