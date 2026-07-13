#!/bin/bash
# GLM 代理应急修复窗口 — Claude 断网时的独立诊断+修复通道
# 用法：直接运行打开新终端标签；--window 参数为内部调用

set -euo pipefail

SELF="$(readlink -f "$0")"

# ─── 内部模式：在新终端标签内执行 ───
if [[ "${1:-}" == "--window" ]]; then
    # 确保 GLM 直连
    export no_proxy="${no_proxy:-},open.bigmodel.cn"
    export NO_PROXY="${NO_PROXY:-},open.bigmodel.cn"

    echo -e "\033[1;36m╔══════════════════════════════════════╗\033[0m"
    echo -e "\033[1;36m║   GLM 代理应急修复终端              ║\033[0m"
    echo -e "\033[1;36m╚══════════════════════════════════════╝\033[0m"
    echo

    # ── 1. 快速诊断 ──
    echo -e "\033[1;33m=== 代理状态诊断 ===\033[0m"
    echo

    # 服务状态
    echo -e "\033[1m[服务状态]\033[0m"
    for svc in xray mihomo; do
        if systemctl is-active --quiet "$svc" 2>/dev/null; then
            echo -e "  $svc: \033[32m● active\033[0m"
        else
            echo -e "  $svc: \033[31m● inactive\033[0m"
        fi
    done
    echo

    # 端口连通性
    echo -e "\033[1m[端口连通性]\033[0m"
    for port in 7890 7891; do
        if timeout 2 bash -c "echo >/dev/tcp/127.0.0.1/$port" 2>/dev/null; then
            echo -e "  127.0.0.1:$port \033[32m可连\033[0m"
        else
            echo -e "  127.0.0.1:$port \033[31m不通\033[0m"
        fi
    done
    echo

    # 外部可达性（通过代理）
    echo -e "\033[1m[外部可达性]\033[0m"
    DIAG_RESULT=""
    for target in "https://www.google.com" "https://api.anthropic.com"; do
        code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 \
            --proxy "http://127.0.0.1:7890" "$target" 2>/dev/null || echo "000")
        if [[ "$code" == "000" ]]; then
            echo -e "  $target → \033[31m超时/不可达\033[0m"
            DIAG_RESULT="${DIAG_RESULT}${target} 不可达 (code=$code)\n"
        elif [[ "$code" =~ ^[23] ]]; then
            echo -e "  $target → \033[32mHTTP $code\033[0m"
            DIAG_RESULT="${DIAG_RESULT}${target} 正常 (code=$code)\n"
        else
            echo -e "  $target → \033[33mHTTP $code\033[0m"
            DIAG_RESULT="${DIAG_RESULT}${target} 异常 (code=$code)\n"
        fi
    done

    # 直连测试（不经代理）
    echo
    echo -e "\033[1m[直连测试（不走代理）]\033[0m"
    for target in "https://www.baidu.com" "https://open.bigmodel.cn"; do
        code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 \
            --noproxy '*' "$target" 2>/dev/null || echo "000")
        if [[ "$code" == "000" ]]; then
            echo -e "  $target → \033[31m超时/不可达\033[0m"
        elif [[ "$code" =~ ^[23] ]]; then
            echo -e "  $target → \033[32mHTTP $code\033[0m"
        else
            echo -e "  $target → \033[33mHTTP $code\033[0m"
        fi
    done

    # 收集完整诊断摘要
    XRAY_STATUS=$(systemctl is-active xray 2>/dev/null || echo "unknown")
    MIHOMO_STATUS=$(systemctl is-active mihomo 2>/dev/null || echo "unknown")
    PORT7890=$(timeout 2 bash -c "echo >/dev/tcp/127.0.0.1/7890" 2>/dev/null && echo "open" || echo "closed")
    PORT7891=$(timeout 2 bash -c "echo >/dev/tcp/127.0.0.1/7891" 2>/dev/null && echo "open" || echo "closed")
    XRAY_LOG=$(journalctl -u xray --no-pager -n 5 2>/dev/null || echo "无法读取")
    MIHOMO_LOG=$(journalctl -u mihomo --no-pager -n 5 2>/dev/null || echo "无法读取")

    DIAG_SUMMARY="当前诊断结果:
- xray 服务: ${XRAY_STATUS}
- mihomo 服务: ${MIHOMO_STATUS}
- 端口 7890 (HTTP): ${PORT7890}
- 端口 7891 (SOCKS5): ${PORT7891}
- 外部可达性: $(echo -e "$DIAG_RESULT" | head -c 200)
- xray 最近日志: ${XRAY_LOG}
- mihomo 最近日志: ${MIHOMO_LOG}"

    echo
    echo -e "\033[1;33m=== 进入 GLM 交互修复模式 ===\033[0m"
    echo -e "\033[90m输入问题描述或直接回车让 GLM 根据诊断结果给出修复建议\033[0m"
    echo -e "\033[90m输入 /q 退出, /d 重新诊断\033[0m"
    echo

    # ── 2. 启动 GLM 交互会话 ──
    python3 - "$DIAG_SUMMARY" <<'PYEOF'
import sys
import os
import json
import urllib.request
import urllib.error
import subprocess

# GLM 直连
os.environ['no_proxy'] = os.environ.get('no_proxy', '') + ',open.bigmodel.cn'
os.environ['NO_PROXY'] = os.environ.get('NO_PROXY', '') + ',open.bigmodel.cn'

API_KEY = "c958396d0cd542d1b4c727270e259eb7.kqPFB3oHSu5pcRZ8"
API_URL = "https://open.bigmodel.cn/api/anthropic/v1/messages"
MODEL = "glm-4.7"

SYSTEM_PROMPT = """你是代理网络应急修复助手。用户的 Claude Code 因代理故障断网，你需要帮助诊断和修复。

## 当前代理架构
- **主代理**: Xray，监听 7890(HTTP) / 7891(SOCKS5)
- **备用代理**: Mihomo，配置与 Xray 共存
- **配置文件**: /etc/nixos/modules/proxy.nix（NixOS 声明式管理）
- **Watchdog**: 自动检测主代理故障并切换到备用
- **环境变量**: http_proxy=http://0.0.0.0:7890, https_proxy=http://0.0.0.0:7890

## 常见故障和修复命令

### Xray 问题
- 查看状态: `systemctl status xray`
- 查看日志: `journalctl -u xray -n 50 --no-pager`
- 重启服务: `sudo systemctl restart xray`
- 测试连接: `curl -x http://127.0.0.1:7890 -s -o /dev/null -w '%{http_code}' https://www.google.com`

### Mihomo 问题
- 查看状态: `systemctl status mihomo`
- 查看日志: `journalctl -u mihomo -n 50 --no-pager`
- 重启服务: `sudo systemctl restart mihomo`

### 端口占用排查
- 查看 7890 占用: `ss -tlnp | grep 7890`
- 查看 7891 占用: `ss -tlnp | grep 7891`

### 切换代理
- 临时用 mihomo: `sudo systemctl stop xray && sudo systemctl start mihomo`
- 切回 xray: `sudo systemctl stop mihomo && sudo systemctl start xray`

### DNS 问题
- 测试 DNS: `nslookup google.com`
- 清 DNS 缓存: `sudo systemd-resolve --flush-caches`

### NixOS 配置修改后
- 重建: `sudo nixos-rebuild switch --flake /etc/nixos#charlie`
- 仅检查语法: `nix flake check /etc/nixos`

## 回复规则
- 用中文回复
- 给出具体可执行的命令
- 先诊断后修复，不要猜测
- 每步操作后说明如何验证效果
- 如果需要修改 NixOS 配置，给出完整修改内容和重建命令
"""

diag_summary = sys.argv[1] if len(sys.argv) > 1 else ""


def chat_stream(messages):
    """Stream GLM response via Anthropic-compatible endpoint."""
    system_text = ""
    conv_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_text += msg["content"] + "\n"
        else:
            conv_messages.append(msg)

    body = {
        "model": MODEL,
        "messages": conv_messages,
        "stream": True,
        "max_tokens": 8192,
    }
    if system_text.strip():
        body["system"] = system_text.strip()

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    full_reply = []
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                line = line.decode().strip()
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    evt = json.loads(data)
                    if evt.get("type") == "content_block_delta":
                        delta = evt.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                print(text, end="", flush=True)
                                full_reply.append(text)
                except (json.JSONDecodeError, KeyError):
                    pass
    except urllib.error.URLError as e:
        print(f"\033[31mGLM 连接失败: {e}\033[0m", file=sys.stderr)
        print("\033[33m提示: 检查 open.bigmodel.cn 是否可直连\033[0m", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"\033[31mGLM 错误: {e}\033[0m", file=sys.stderr)
        return ""
    print()
    return "".join(full_reply)


def run_diag():
    """Re-run diagnostics and return summary string."""
    parts = []
    for svc in ("xray", "mihomo"):
        r = subprocess.run(["systemctl", "is-active", svc],
                           capture_output=True, text=True)
        parts.append(f"{svc}: {r.stdout.strip()}")
    for port in (7890, 7891):
        r = subprocess.run(
            ["bash", "-c", f"echo >/dev/tcp/127.0.0.1/{port}"],
            capture_output=True, timeout=3)
        parts.append(f"port {port}: {'open' if r.returncode == 0 else 'closed'}")
    for url in ("https://www.google.com", "https://api.anthropic.com"):
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "--connect-timeout", "5", "--proxy", "http://127.0.0.1:7890", url],
            capture_output=True, text=True, timeout=10)
        parts.append(f"{url}: HTTP {r.stdout.strip()}")
    return " | ".join(parts)


# Build initial history
history = [{"role": "system", "content": SYSTEM_PROMPT}]

# Auto-send diagnosis on first message
if diag_summary:
    first_msg = f"以下是当前代理诊断结果，请分析并给出修复建议：\n\n{diag_summary}"
    history.append({"role": "user", "content": first_msg})
    print("\033[1;36mGLM:\033[0m ", end="")
    reply = chat_stream(history)
    if reply:
        history.append({"role": "assistant", "content": reply})
    print()

# Interactive loop
while True:
    try:
        user_input = input("\033[1;32m>\033[0m ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n退出修复终端。")
        break

    if not user_input:
        continue
    if user_input == "/q":
        print("退出修复终端。")
        break
    if user_input == "/d":
        print("\033[33m重新诊断中...\033[0m")
        new_diag = run_diag()
        print(f"\033[90m{new_diag}\033[0m\n")
        user_input = f"重新诊断结果: {new_diag}\n请根据最新状态给出建议。"

    history.append({"role": "user", "content": user_input})
    print("\033[1;36mGLM:\033[0m ", end="")
    reply = chat_stream(history)
    if reply:
        history.append({"role": "assistant", "content": reply})
    print()

PYEOF
    exit 0
fi

# ─── 默认模式：打开新终端标签运行自己 ───
if command -v konsole &>/dev/null; then
    konsole --new-tab -e bash "$SELF" --window
elif command -v xterm &>/dev/null; then
    xterm -e bash "$SELF" --window &
else
    echo "未找到终端模拟器，直接运行..."
    bash "$SELF" --window
fi
