# 虚拟人 & 视频营销方案
> 创建日期：2026-04-21 | 状态：规划中

## 目标
复刻抖音爆款情感内容创作者（牛哞哞风格）的声音和形象，
打造外贸/电商场景的亲情/正能量短视频流水线，实现批量生产。

---

## 技术架构

```
文案生成(DeepSeek)
      ↓
TTS语音合成(GPT-SoVITS)
      ↓
数字人视频(MuseTalk)
      ↓
后期处理(FFmpeg 添加字幕/BGM)
      ↓
自动发布(抖音/视频号 API)
```

---

## 组件选型

### 1. 声音克隆 — GPT-SoVITS
- **仓库**: https://github.com/RVC-Boss/GPT-SoVITS
- **VRAM**: 6-8GB（RTX 3060 Ti 可用）
- **训练数据**: 5-10 分钟中文音频 + 文字标注
- **中文支持**: 原生支持普通话，方言需额外训练
- **接口**: HTTP API（/tts endpoint）
- **Docker**: `docker run -p 9880:9880 gptsovits/gptsovits`
- **训练步骤**:
  1. 从抖音下载目标视频，提取音频 `ffmpeg -i input.mp4 -vn voice.wav`
  2. 切片标注（可用 WhisperX 自动打标）
  3. 训练 1-2 小时（3060 Ti）
  4. 导出模型到 `~/agi/models/voice/`

### 2. 数字人视频 — MuseTalk
- **仓库**: https://github.com/TMElyralab/MuseTalk
- **VRAM**: 8GB（刚好能跑）
- **输入**: 参考人物视频/照片 + 音频
- **输出**: 实时口型同步视频（25fps）
- **API**: FastAPI 包装后 POST /generate
- **备选**: SadTalker（更多表情，内存稍高）

### 3. 文案生成 — 已有 DeepSeek v3.2
- 接入 `localhost:4000` LiteLLM
- 模板：`~/agi/copywriting_collector.py` 的 GOLDEN_PATTERNS
- Prompt 模板见下方

### 4. 字幕/后期 — FFmpeg
```bash
# 烧录字幕（竖屏 1080x1920）
ffmpeg -i input.mp4 -vf "subtitles=subs.srt:force_style='Fontsize=28'" -s 1080x1920 output.mp4
```

---

## 文案 Prompt 模板（爆款情感）

```
你是一位专业的短视频文案创作者，风格参考抖音爆款情感视频。
请生成一条适合外贸/电商老板分享的亲情/正能量短视频口播文案。

要求：
- 30-60字，适合30秒短视频
- 开头用金句抓人（你最大的骄傲/最好的选择/有一个...）
- 中间有反转（不是...，而是...）
- 结尾有号召力或情感共鸣
- 不提具体产品，突出人物气质和价值观

输出一条，直接给文案内容。
```

---

## 部署方案

### Docker Compose
```yaml
# ~/agi/docker/virtual-person/docker-compose.yml
version: '3.8'
services:
  gptsovits:
    image: breakstring/gpt-sovits
    ports:
      - "9880:9880"
    volumes:
      - ~/agi/models/voice:/app/GPT_weights
      - ~/agi/models/sovits:/app/SoVITS_weights
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]

  musetalk:
    build: ./musetalk
    ports:
      - "9881:8000"
    volumes:
      - ~/agi/models/musetalk:/app/models
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
```

### 统一 API（已有 FastAPI 9900）
```python
# /v1/video/generate
# Input: {text: str, voice_model: str, avatar_video: str}
# Output: {video_url: str, duration: float}
```

---

## 内容策略

### 目标人群
- 外贸/电商从业者（25-45岁）
- 情感触发点：家庭、成功、骄傲、孝顺

### 发布节奏
- 每日 2-3 条（早9点、中午12点、晚8点）
- 批量生成（每周一次，生成7天内容）

### 形象设计
- 主角：职业装中年女性 or 自信创业者
- 背景：简洁办公室或温馨家庭
- 字体：黑体大字 + 暖色调

---

## 实施路线图

| 阶段 | 内容 | 预计时间 |
|------|------|---------|
| P0 | 采集目标人物音视频素材 | 1天 |
| P1 | GPT-SoVITS 声音克隆训练 | 2天 |
| P2 | MuseTalk 数字人部署 | 1天 |
| P3 | FastAPI 整合 + 3000面板 | 1天 |
| P4 | 首批10条视频生成测试 | 1天 |
| P5 | 自动发布（抖音开放平台） | 3天 |

---

## 素材采集命令

```bash
# 下载抖音视频（需 yt-dlp）
yt-dlp -x --audio-format wav "https://v.douyin.com/xxx" -o ~/agi/data/voice/source.%(ext)s

# 提取人脸参考帧
ffmpeg -i source.mp4 -vf "select=eq(n\,0)" -q:v 1 avatar.jpg

# 音频预处理（降噪+标准化）
ffmpeg -i voice.wav -af "afftdn,loudnorm" voice_clean.wav
```

---

## 归档位置
- 方案文档: `~/agi/virtual-person-plan.md`
- 模型存储: `~/agi/models/`
- 视频输出: `~/agi/data/videos/`
- 脚本: `~/agi/video_pipeline.py`（待创建）
- 3000面板: VideoMarketingPanel
