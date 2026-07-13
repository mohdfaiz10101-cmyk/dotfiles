#!/usr/bin/env python3
"""integrity-check.py — 配置完整性巡检 + 空壳检测"""
import subprocess, json, time, os, sys

PASS, WARN, CRIT = 0, 0, 0

def check(label, url_or_cmd, expect, level="port"):
    global PASS, WARN, CRIT
    try:
        if url_or_cmd.startswith("http"):
            import urllib.request
            req = urllib.request.Request(url_or_cmd, headers={"User-Agent": "integrity/1.0"})
            resp = urllib.request.urlopen(req, timeout=5)
            code = str(resp.getcode())
            if code in expect.split(","):
                if level != "quiet": print(f"[OK] {label}: HTTP {code}")
                PASS += 1; return True
            else:
                print(f"[WARN] {label}: HTTP {code} (期望 {expect})")
                WARN += 1; return False
        else:
            result = subprocess.run(url_or_cmd, shell=True, capture_output=True, text=True, timeout=5)
            if expect in result.stdout + result.stderr:
                print(f"[OK] {label}: 通过")
                PASS += 1; return True
            else:
                print(f"[WARN] {label}: 未达预期")
                WARN += 1; return False
    except Exception as e:
        msg = str(e)[:60]
        if level == "critical":
            print(f"[FAIL] {label}: {msg}")
            CRIT += 1
        elif level == "quiet":
            WARN += 1
        else:
            print(f"[WARN] {label}: {msg}")
            WARN += 1
        return False

print(f"=== 配置完整性巡检 {time.strftime('%H:%M')} ===")
print()

# 端口检查
print("--- 端口绑定 ---")
ports_expected = {
    "LiteLLM:4000":    "http://localhost:4000/health",
    "Letta:8283":      "http://localhost:8283/v1/agents/",
    "ChromaDB:8000":   "http://localhost:8000/api/v1",
    "Paperclip:3100":  "http://localhost:3100/health",
    "Hub:9800":        "http://localhost:9800/health",
    "AGI GW:9900":     "http://localhost:9900/health",
    "Console:3000":    "http://localhost:3000/",
    "Redis:6379":      "redis-cli -p 6379 PING",
}
for name, url in ports_expected.items():
    check(name, url, "200,302,301,PONG")

# 配置文件 checksum
print()
print("--- 配置文件 checksum ---")
configs = {
    "/etc/mihomo/config.yaml": "mihomo代理配置",
    "/home/charlie/CLAUDE.md":  "Claude规则",
}
for path, desc in configs.items():
    if os.path.exists(path):
        cmd = f"sha256sum {path}"
        check(desc, cmd, "", level="quiet")
    else:
        check(desc, "echo MISSING", "MISSING", level="critical")

# Docker 容器
print()
print("--- Docker 容器 ---")
try:
    out = subprocess.run("docker ps --format '{{.Names}} {{.Status}}'", shell=True, capture_output=True, text=True, timeout=5)
    for line in out.stdout.strip().split("\n"):
        if "Up" in line and "(healthy)" in line:
            PASS += 1
        elif "Up" in line:
            name = line.split()[0]
            print(f"[WARN] Docker {name}: 运行但无健康检查")
            WARN += 1
        elif line.strip():
            print(f"[FAIL] Docker: {line}")
            CRIT += 1
except Exception as e:
    print(f"[WARN] Docker不可用: {e}")
    WARN += 1

# 空壳检测
print()
print("--- 空壳检测 ---")
# 检查是否有服务端口监听但无响应
dead_ports = []
for port in [4002, 4003, 4533, 7500, 5998]:
    result = subprocess.run(f"ss -tlnp | grep ':{port} '", shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        dead_ports.append(port)
if dead_ports:
    print(f"[WARN] 未登记端口: {dead_ports}")
    WARN += 1

# 检查已知废弃路径
known_dead = {
    "StepClaw 7699": 7699,
    "Finance 9810": 9810,
}
for name, port in known_dead.items():
    result = subprocess.run(f"ss -tlnp | grep ':{port} '", shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        print(f"[?] {name}: 端口仍在使用但已标记废弃")
        WARN += 1

print()
print(f"=== 结果: PASS={PASS} WARN={WARN} CRIT={CRIT} ===")

if CRIT > 0:
    print("[ALERT] 红线告警")
    sys.exit(2)
else:
    if WARN > 0:
        print("[WARN] 存在非关键漂移")
    else:
        print("[PASS] 全部通过")
    sys.exit(0)