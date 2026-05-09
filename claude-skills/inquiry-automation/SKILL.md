---
name: inquiry-automation
description: 部署询盘自动处理系统（豆包视觉OCR + 4轮自对话 + 多通道反馈）
user-invocable: true
version: "1.0.0"
category: business-automation
tags: [automation, inquiry, doubao, vision, business]
effort: medium
---

# /inquiry-automation

部署完整的询盘自动化处理系统，基于豆包视觉 OCR + 4 轮自对话引擎（识别→分析→报价→审核）+ 多通道反馈推送。

## 功能特性

- **感知层**：豆包 Vision OCR（替代 Claude Vision，成本降 50x，中文优化）
- **推理层**：4 轮自对话 pipeline（doubao/vision → deepseek-v3.2 → auto → auto）
- **记忆层**：Letta 语义搜索 + ChromaDB 产品目录 + 学习闭环
- **反馈层**：Telegram 即时推送 + Discord 日报 + Hub 弹幕

## 用法

```bash
/inquiry-automation deploy    # 完整部署（首次使用）
/inquiry-automation verify    # 验证部署状态
/inquiry-automation test      # 测试询盘处理流程
```

## 部署步骤

### Step 1: LiteLLM 新增豆包视觉模型

编辑 `/mnt/ai/ai-cluster/litellm/config.yaml`，在豆包模型区域（约第 410 行）后添加：

```yaml
  # 豆包视觉模型（询盘 OCR + 截图理解）
  - model_name: doubao/vision
    litellm_params:
      model: volcengine/Doubao-1-5-thinking-vision-pro-250428
      api_key: os.environ/ARK_API_KEY
      api_base: https://ark.cn-beijing.volces.com/api/v3
      timeout: 120
    model_info:
      supports_vision: true

  - model_name: doubao/vision-lite
    litellm_params:
      model: volcengine/Doubao-1-5-vision-lite
      api_key: os.environ/ARK_API_KEY
      api_base: https://ark.cn-beijing.volces.com/api/v3
      timeout: 60
    model_info:
      supports_vision: true
```

在 fallbacks 部分添加：

```yaml
    - doubao/vision: [cloud/glm-4v, local/minicpm-v, free/mistral-pixtral]
    - doubao/vision-lite: [doubao/vision, cloud/glm-4v, local/minicpm-v]
```

**重启 LiteLLM**：

```bash
cd /mnt/ai/ai-cluster/litellm
docker compose restart litellm
sleep 10
curl -s http://localhost:4000/health/readiness
```

### Step 2: 创建询盘引擎

**文件路径**：`/home/charlie/hub/inquiry_engine.py`（507 行）

核心组件：
- `process_inquiry(image_b64, text_input)` — 主 pipeline
- `round1_recognize()` — 豆包 Vision OCR
- `round2_analyze()` — DeepSeek V3.2 选型分析
- `round3_quote()` — GLM 生成报价单
- `round4_review()` — GLM 质量审核
- SQLite 持久化 + Letta 语义搜索集成

**初始化数据库**：

```bash
python3 -c "import sys; sys.path.insert(0, '/home/charlie/hub'); from inquiry_engine import _init_db; _init_db()"
```

### Step 3: Hub API 新增路由

在 `/home/charlie/hub/hub-api.py` 中添加询盘路由（已自动完成）：

- `GET /inquiries` — 看板页面
- `POST /api/inquiry/process` — 处理询盘
- `GET /api/inquiry/list` — 查询列表
- `GET /api/inquiry/{id}` — 获取详情
- `POST /api/inquiry/{id}/approve` — 审批

**重启 Hub 服务**：

```bash
systemctl --user restart charlie-hub
```

### Step 4: 看板前端

**文件路径**：`/home/charlie/hub/static/inquiries.html`（306 行）

4 列看板布局：待审核 | 处理中 | 已审批 | 已发送

访问：`http://localhost:9800/inquiries`

### Step 5: 反馈推送模块

**文件路径**：`/home/charlie/hub/inquiry_feedback.py`（253 行）

三个通道：
- Telegram 即时推送
- Discord 日报（每日 20:00）
- Hub 弹幕

**配置环境变量**（可选）：

创建 `/home/charlie/agi/.env`：

```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
DISCORD_WEBHOOK_URL=your_webhook_url
```

## 验证命令

```bash
# 1. 检查文件完整性
ls -la /home/charlie/hub/inquiry_engine.py \
       /home/charlie/hub/inquiry_feedback.py \
       /home/charlie/hub/static/inquiries.html

# 2. 验证数据库
python3 -c "import sqlite3; db = sqlite3.connect('/home/charlie/hub/inquiries.db'); print('Tables:', [t[0] for t in db.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall()])"

# 3. 验证 API 路由
curl -s http://localhost:9801/api/inquiry/list | python3 -m json.tool

# 4. 验证豆包视觉模型
curl -s http://localhost:4000/v1/models -H "Authorization: Bearer sk-litellm-charlie-2026" | python3 -c "import sys,json; models=[m['id'] for m in json.load(sys.stdin)['data']]; print([m for m in models if 'doubao' in m.lower()])"

# 5. 验证前端页面
curl -s -o /dev/null -w "%{http_code}" http://localhost:9800/inquiries
```

## 测试流程

### 文本询盘测试

```bash
python3 /home/charlie/hub/inquiry_engine.py --text "需要一台立式粉末包装机，规格50g-500g，数量2台，发迪拜，预算3万美元"
```

### 图片询盘测试

```bash
python3 /home/charlie/hub/inquiry_engine.py --image /path/to/screenshot.png
```

### 查看处理结果

```bash
python3 /home/charlie/hub/inquiry_engine.py --list
```

### 测试推送

```bash
python3 /home/charlie/hub/inquiry_feedback.py --test
```

## 文件清单

| 文件 | 大小 | 作用 |
|------|------|------|
| `hub/inquiry_engine.py` | 17KB | 4 轮自对话引擎 |
| `hub/inquiry_feedback.py` | 9.8KB | 3 通道推送 |
| `hub/static/inquiries.html` | 14.7KB | 任务看板 |
| `hub/inquiries.db` | SQLite | 询盘数据库 |
| `litellm/config.yaml` | — | +2 个视觉模型 |
| `hub/hub-api.py` | — | +5 个 API 端点 |

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        输入源（感知层）                          │
│  微信/邮件/手动上传 ──→ Hub /api/inquiry/process               │
│                              ↓                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              自动对话引擎（inquiry_engine.py）             │  │
│  │  ① 识别  → 豆包 Vision OCR                                │  │
│  │  ② 分析  → DeepSeek V3.2 选型                             │  │
│  │  ③ 报价  → GLM 生成报价单                                 │  │
│  │  ④ 审核  → GLM 质量检查                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              反馈整合（inquiry_feedback.py）               │  │
│  │  Telegram 即时 + Discord 日报 + Hub 弹幕                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 成本估算

| 组件 | 月成本 | 说明 |
|------|--------|------|
| 豆包 Vision | ¥5-20 | 每天 10 张图 × ¥0.003/千 token |
| DeepSeek V3.2 | ¥10-30 | 分析师角色 |
| Qwen3:8b | ¥0 | 本地免费（报价+审核） |
| **总计** | **¥15-50/月** | 节省 30+ 小时/月 |

## 注意事项

1. **ARK_API_KEY 必须已配置** — 火山引擎 API Key，环境变量或 docker-compose.yml
2. **Ollama 可选** — 如需 prompt 压缩和本地 qwen3:8b，启动 Ollama
3. **Letta 语义搜索依赖** — 确保 Letta 服务运行（:8283）
4. **数据隐私** — 所有数据本地存储，不出本地网络
5. **首次使用需投喂** — 将历史询盘案例说给系统，积累 Letta 记忆

## 故障排查

### 问题：豆包视觉模型调用失败

```bash
# 检查 ARK_API_KEY
docker exec litellm env | grep ARK_API_KEY

# 检查模型列表
curl -s http://localhost:4000/v1/models -H "Authorization: Bearer sk-litellm-charlie-2026" | grep doubao
```

### 问题：Hub 路由 404

```bash
# 检查 hub-api.py 是否导入了 inquiry_engine
grep "from inquiry_engine import" /home/charlie/hub/hub-api.py

# 重启服务
systemctl --user restart charlie-hub
```

### 问题：Letta 搜索返回空

```bash
# 检查 Letta 健康
curl -s http://localhost:8283/v1/health

# 手动测试搜索
python3 -c "import sys; sys.path.insert(0, '/home/charlie/.config/ai-shared'); from letta_search_enhanced import search; print(search('包装机', limit=3))"
```

## 扩展方向

- **定时检查**：systemd timer 每小时检查新询盘（邮件/微信同步）
- **产品目录投喂**：ChromaDB 向量化产品库，提升选型准确率
- **工作流自动化**：审批后自动发送邮件、更新 CRM
- **学习闭环**：人工修改报价后，对比差异写入 Letta 用于训练

## 相关链接

- 豆包 Vision 文档：https://docs.litellm.ai/docs/providers/volcano
- LiteLLM 配置：/mnt/ai/ai-cluster/litellm/config.yaml
- Hub 看板：http://localhost:9800/inquiries
- 设计方案：~/.claude/projects/-home-charlie/memory/ideas-roadmap.md
