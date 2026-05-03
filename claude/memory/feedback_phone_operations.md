---
name: 手机操作自动执行
description: 涉及手机操作时直接用 ADB/Chrome CDP 执行，不让用户手动操作
type: feedback
---

手机上的所有操作 MUST 通过 ADB 直接执行，不要让用户手动操作。

**Why:** 用户明确说过"让 AI 全都记住手机上的操作"，不希望每次被要求手动操作手机。

**How to apply:**
- 网页测试 → `adb -s {phone_id} shell "curl ..."` 或 ADB intent 打开 Chrome
- 截图查看 → `adb exec-out screencap -p > /tmp/xxx.png` + Read 读取
- Chrome 控制 → ADB intent: `am start -a android.intent.action.VIEW -d '{url}' com.android.chrome`
- Chrome CDP → `adb forward tcp:9222 localabstract:chrome_devtools_remote`
- 安装 APK → `adb -s {phone_id} install {apk}`
- 手机 IP: ace-5-pro Tailscale `100.64.206.110:5555`，平板 `100.104.211.70:5555`
- 不在同一局域网时用 Tailscale IP（手机当前 wlan2=10.104.223.x，不是家庭网络）

禁止：说"请在手机上打开浏览器" | 说"请手动访问" | 让用户操作手机
