---
name: opencode-autofix
description: "opencode 连接/启动失败后自动诊断修复：JSON格式、循环软链接、LiteLLM连通性、instructions格式"
user-invocable: true
version: "1.0.0"
category: opencode
tags: [opencode, autofix, litellm, json, symlink, connection]
effort: low
auto-generated: false
created: 2026-04-22
---

# Opencode Autofix

## 触发场景
- opencode 启动报错：`JSON invalid` / `expected array, received string`
- opencode 连接 LiteLLM 失败（模型列表空 / timeout）
- opencode 进程起不来（循环软链接）
- OP 任务调用 opencode 失败

## 诊断 + 修复流程

### Step 1 — 检查 opencode.json 完整性
```bash
OCJSON=~/.config/opencode/opencode.json

# 检测循环软链接
if [ -L "$OCJSON" ] && [ ! -e "$OCJSON" ]; then
  echo "[修复提示] opencode.json 是悬空软链接"
  echo "执行: rm $OCJSON && cp ~/dotfiles/opencode/opencode.json $OCJSON"
fi

# 检测 JSON 格式
python3 -m json.tool "$OCJSON" > /dev/null 2>&1 || echo "[修复提示] JSON 格式错误，用备份恢复"

# 检测 instructions 是否为数组
python3 -c "
import json
d = json.load(open('$OCJSON'))
inst = d.get('instructions', None)
if isinstance(inst, str):
    print('[自动修复] instructions 是字符串，转为数组')
    d['instructions'] = [inst]
    json.dump(d, open('$OCJSON', 'w'), ensure_ascii=False, indent=2)
    print('[OK] 已修复')
elif isinstance(inst, list):
    print('[OK] instructions 格式正确')
"
```

### Step 2 — 检查 LiteLLM 连通性
```bash
STATUS=$(curl -s --connect-timeout 3 http://localhost:4000/health -o /dev/null -w "%{http_code}")
if [ "$STATUS" != "200" ]; then
  echo "[修复提示] LiteLLM 不可达 (status=$STATUS)"
  echo "检查: systemctl status litellm-docker / docker ps | grep litellm"
  echo "修复: sudo systemctl restart litellm-docker"
else
  echo "[OK] LiteLLM 连通 (localhost:4000)"
fi
```

### Step 3 — 验证 opencode 可启动
```bash
opencode --version 2>&1 | head -3
# 有输出 = 正常，报错 = 继续排查
```

## 修复提示速查表

| 症状 | 原因 | 修复 |
|------|------|------|
| `JSON invalid` | opencode.json 格式破坏 | 从 dotfiles 恢复或 python json.tool 检查 |
| `expected array, received string` | instructions 字段非数组 | Step 1 python 脚本自动修复 |
| 循环软链接 | stow/rsync 写错目标路径 | `rm` 软链接 + `cp` 真实文件 |
| 模型列表空白 | LiteLLM 服务未起 | `sudo systemctl restart litellm-docker` |
| 连接 timeout | mihomo 代理未就绪 | `systemctl --user status mihomo` |

## 历史根因（来自 lessons-learned）
- 2026-04-20: `dotfiles/opencode/opencode.json` 自指向自身循环链接，opencode 启动报 JSON invalid
- 2026-04-21: instructions 字段被写成字符串，需包成数组 `["..."]`
- 预防：`opencode-config-guard.sh` 已加入 CC Stop hook + OP heartbeat 前置检查

## 封装调用示例
```
# CC 中触发
/opencode-autofix
```
