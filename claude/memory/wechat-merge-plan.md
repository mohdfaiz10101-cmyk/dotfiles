---
name: wechat-merge-plan
description: 微信聊天记录合并方案（Windows+Linux双端数据库合并）
type: project
---

**状态：已完成（2026-04-17）**

**解密合并结果**：
- 消息：10376条（去重670）
- 联系人：3269
- 数据路径：
  - Windows 解密：`/mnt/ai/data/win-wechat-decrypted`
  - UOS 解密：`/mnt/ai/data/uos-wechat-decrypted`
  - 合并结果：`/mnt/ai/data/wechat-merged`

**技术要点**：
- Windows 4.x 密钥提取用 `wechat-decrypt`（pywxdump 不支持 4.x）
- Windows DB 路径：`C:\Users\G\Documents\xwechat_files\w422417869_448e\db_storage\`
- UOS 端密钥：`~/.cache/wechat-finance/keys.json`
- 解密命令：`nix-shell -p python312Packages.pycryptodome --run 'python3 decrypt_db.py'`
- 合并脚本：`/mnt/ai/data/wechat-merge.py`，按 server_id 去重

**后续**（未完成）：
- [ ] Web UI 查询界面
- [ ] 连接 OpenCode / PostgreSQL
