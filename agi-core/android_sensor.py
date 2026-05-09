"""
android_sensor.py — Android 手机传感器采集
通过 ADB 采集手机状态，注入 brain.py Sense 阶段
"""

import subprocess, json, re
from datetime import datetime
from pathlib import Path

DEVICE_ID = "89f5ae98"  # Xiaomi M2011K2G

def _adb(cmd: str, timeout: int = 5) -> str:
    try:
        r = subprocess.run(
            f"adb -s {DEVICE_ID} shell {cmd}",
            shell=True, capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except Exception as e:
        return f"error:{e}"

def sense_android() -> dict:
    """采集 Android 手机传感器数据，返回可注入 brain.py 的字典"""

    # 电量
    battery_raw = _adb("dumpsys battery | grep level")
    battery = re.search(r"level:\s*(\d+)", battery_raw)
    battery_pct = int(battery.group(1)) if battery else -1

    # 充电状态
    charging_raw = _adb("dumpsys battery | grep 'AC powered\\|USB powered\\|Wireless powered'")
    charging = "AC powered: true" in charging_raw or "USB powered: true" in charging_raw

    # 屏幕状态
    screen_raw = _adb("dumpsys power | grep 'Display Power'")
    screen_on = "state=ON" in screen_raw

    # WiFi 连接
    wifi_raw = _adb("dumpsys wifi | grep 'mWifiInfo' | head -1")
    wifi_ssid = re.search(r'SSID: ([^,]+)', wifi_raw)
    wifi = wifi_ssid.group(1).strip() if wifi_ssid else "unknown"

    # 内存
    mem_raw = _adb("cat /proc/meminfo | grep MemAvailable")
    mem_avail = re.search(r"(\d+)", mem_raw)
    mem_mb = int(mem_avail.group(1)) // 1024 if mem_avail else -1

    # 运行中的前台 App
    fg_raw = _adb("dumpsys activity activities | grep 'mResumedActivity' | head -1")
    fg_app = re.search(r"u0 ([\w.]+)/", fg_raw)
    foreground_app = fg_app.group(1) if fg_app else "unknown"

    return {
        "device": "xiaomi-m2011k2g",
        "timestamp": datetime.now().isoformat(),
        "battery_pct": battery_pct,
        "charging": charging,
        "screen_on": screen_on,
        "wifi": wifi,
        "mem_avail_mb": mem_mb,
        "foreground_app": foreground_app,
    }

def send_notification(title: str, message: str) -> bool:
    """通过 ADB 向手机发送通知（需 Termux:API 或 am broadcast）"""
    cmd = f'am broadcast -a android.intent.action.SEND --es title "{title}" --es message "{message}" 2>/dev/null || true'
    _adb(cmd)
    return True

def push_file(local_path: str, remote_path: str = "/sdcard/agi/") -> str:
    """推送文件到手机"""
    try:
        r = subprocess.run(
            f"adb -s {DEVICE_ID} push {local_path} {remote_path}",
            shell=True, capture_output=True, text=True, timeout=30
        )
        return r.stdout.strip() or r.stderr.strip()
    except Exception as e:
        return f"error:{e}"

if __name__ == "__main__":
    data = sense_android()
    print(json.dumps(data, ensure_ascii=False, indent=2))
