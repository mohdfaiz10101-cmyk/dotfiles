# 微信聊天记录自动同步方案

## 架构

```
Windows 主机（常开）                          NixOS 主机
┌───────────────────────────┐    Syncthing    ┌─────────────────────────────┐
│ 微信 PC 版（保持登录）     │                │                             │
│          ↓                 │                │                             │
│ PyWxDump 定时解密          │   自动同步      │ ~/xwechat_files/            │
│          ↓                 │  ─────────→    │   wxid_xxx/decrypted/       │
│ C:\WeChatSync\decrypted\  │                │          ↓                   │
│                            │                │ HyperChat (localhost:9098)  │
└───────────────────────────┘                └─────────────────────────────┘
```

## Windows 端安装步骤

### 1. 安装 PyWxDump

下载 EXE 版（免 Python 环境）：
https://github.com/xaoyaoo/PyWxDump/releases

或用 pip：
```powershell
pip install pywxdump
```

### 2. 放置自动化脚本

把 `wechat-auto-decrypt.ps1` 复制到 `C:\WeChatSync\`

### 3. 设置 Windows 计划任务

以管理员身份运行 `setup-task.ps1`，会自动创建每小时执行的计划任务。

### 4. 安装 Syncthing

下载：https://syncthing.net/downloads/
共享文件夹：`C:\WeChatSync\decrypted`
对端：NixOS 主机的 Syncthing

## NixOS 端

1. 启动 Syncthing：`systemctl --user start syncthing`
2. 在 Syncthing Web UI (localhost:8384) 添加同步文件夹
3. 目标路径：`~/xwechat_files/wxid_bjo2p0swoxm822_fe61/decrypted`

## 验证

```bash
# 检查解密数据是否同步到位
ls ~/xwechat_files/wxid_bjo2p0swoxm822_fe61/decrypted/contact/contact.db

# 测试 HyperChat 能否读取
curl http://localhost:9098/api/wx/contacts | head -100
```
