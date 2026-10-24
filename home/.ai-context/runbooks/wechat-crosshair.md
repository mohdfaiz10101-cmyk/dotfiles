# 微信鼠标十字：2026-10-24 已确认的原因与修复

## 旧结论撤回
“微信 CSS/JS 注入 crosshair、重启不行只能等升级”没有证据，已经被本次修复推翻。只在微信或 XWayland 窗口出现十字，不能排除别的 X11 客户端抓取指针。

## 已确认的故障链
- `~/.local/bin/hermes` 是 `#!/bin/sh` 包装器。
- Studio 的 Python 自动发现读取该 shebang，误把 `/bin/sh` 当作 Python 解释器。
- `/bin/sh .../hermes_bridge.py` 执行到 `import argparse` 时，运行了 ImageMagick `import` 截图命令，等待用户选择窗口。
- `XF86LogGrabInfo` 的 Xwayland 日志确认 active grab owner 为 `import argparse`，光标为 17×17、hotspot=(8,8) 的十字。
- 重启微信无效，因为占用来自桥接进程。强改窗口光标也会被 active grab 的 cursor 覆盖。

## 默认修复路径
1. `python3 scripts/x11-grab-report.py` 获取 active grab owner；不要杀全部 import / Python / 微信进程。
2. 当前已在 `hermes-studio-8648.service.d/30-bridge-python.conf` 和 `hermes-web-ui.service.d/30-bridge-python.conf` 指定 `HERMES_AGENT_BRIDGE_PYTHON=/usr/bin/python3`。未来该服务启动直接选择 Python，不改端口绑定。
3. 当需要保留现有 Studio 进程时，`hermes-studio-agent-bridge.service` 可直接托管正确的 broker，无需重启共享 UI。它是静态按需服务，不常驻启用后台 worker。
4. 核对 `/tmp/hermes-agent-bridge.sock` 的监听者是 Python；发送 JSON line `{"action":"ping"}` 应返回 `ok:true,pong:true`。
5. 若仍有错误 `/bin/sh .../hermes_bridge.py` 及其 `import argparse` 子进程，只处理已核对归属的这对进程。可先 STOP shell、防止继续执行后续 Python import 语句，再 TERM import、结束错误 shell。broker 可用后 Node 应复用现有端点。

## 验证与取证
- `python3 scripts/x11-grab-report.py`：无 active grab；`pgrep -ax import` 不再出现桥接误启动截图进程。
- `grim -c` 拍到实际微信界面及普通箭头；输入区显示正常 I 形。
- XFIXES 的正确 python-xlib 调用：
```python
from Xlib import display
D = display.Display(':0')
D.xfixes_query_version()
v = D.xfixes_get_cursor_image(D.screen().root)
print(v.width, v.height, v.xhot, v.yhot)
```
- 修复后实测箭头 24×24/hotspot=(3,1)，输入光标 24×24/hotspot=(11,12)；XGrabPointer 测试可成功，随后立即释放。
- 每次聚焦/移动后回读指针和窗口 class，并查看截图。远程输入和并发桌面自动化会抢回焦点，单看命令返回成功不构成验证。
- 不要常驻一个不断覆盖光标的 guard 来掩盖 active grab；本次实验 guard 已删除。

本次未重启微信、未清理微信登录数据。不要把正常重启后出现“进入微信”登录确认页直接称为登录态被删除。
