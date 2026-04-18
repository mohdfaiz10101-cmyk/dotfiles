# 踩坑日志

- [2026-04-18] [GLM-5.1] **微信聊天记录→Letta 学习管道创建**
  - 场景：用户要求手动备份微信聊天→Letta 学习→定期提醒
  - 发现：Wine 微信 ChatMsg.db 也是加密的（不是明文 SQLite），UOS DB 自定义 AES 解密失败（格式可能已变）
  - 方案：以文件导入为主（用户手动导出 TXT/CSV/HTML），DB 直读作为可选功能
  - 创建：`/home/charlie/agi/wechat-learn.py`（685 行），`/home/charlie/agi/wechat-learn.sh`（nix-shell wrapper）
  - 备份提醒：`wechat-backup-reminder.timer`（systemd，每天10:00检查，3天间隔）
  - Letta API：POST `/v1/agents/{id}/archival-memory` body=`{"text":"..."}`（单条写入，不是批量）
  - 踩坑：Letta 批量写入导致 embedding API 413 过载→event loop hang→服务重启
- [2026-04-18] [Sonnet] **voxtype 语音输入 KDE Wayland 粘贴不上屏修复**
  - 场景：voxtype paste 模式日志显示 `Text pasted via clipboard + ctrl+v` 成功，但用户看不到文字出现
  - 根因分析链：(1) wtype 在 KDE Plasma Wayland 不可用（`Compositor does not support the virtual keyboard protocol`）(2) dotool 不支持 CJK 字符 (3) ydotool 通过 uinput 可发送按键但 Ctrl+V 在终端中无效
  - **核心问题**：Ctrl+V 在 Konsole 等终端中不是粘贴快捷键（终端用 Ctrl+Shift+V），所以 ydotool 模拟的 Ctrl+V 在终端中无效
  - **修复**：config.toml `paste_keys = "shift+insert"` — Shift+Insert 在所有 Linux 应用中（含终端、浏览器、编辑器）都是粘贴快捷键
  - 完整 paste 链路：whisper 转写 → wl-copy 写入剪贴板 → wtype Shift+Insert（失败）→ ydotool Shift+Insert（成功，通过 uinput 模拟物理按键）
  - 其他配置：`pre_type_delay_ms = 150`（粘贴前等待剪贴板就绪）、`driver_order = ["ydotool", "dotool"]`（跳过不可用的 wtype）
  - systemd 服务添加 `-v` 调试日志级别便于排查
  - 教训：(1) KDE Plasma Wayland 不支持 wtype 的 virtual keyboard protocol (2) Ctrl+V 在终端中无效，Shift+Insert 是更通用的粘贴方案 (3) voxtype paste 模式内部会先尝试 wtype 再降级 ydotool，日志需要 -vv 级别才能看到降级过程
