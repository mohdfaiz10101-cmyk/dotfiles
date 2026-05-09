---
name: wav2lip-docker-batch
description: "Wav2Lip口型同步：用MuseTalk容器批量生成视频+ADB推送手机相册"
user-invocable: false
version: "1.0.0"
category: ai-video
tags: [wav2lip, lip-sync, docker, adb, video-generation]
effort: medium
auto-generated: true
created: 2026-04-25
---

# Wav2Lip Docker Batch

## 场景
## Wav2Lip Docker批量生成

### 前置条件
- musetalk-api:local Docker镜像（含torch 2.0+CUDA）
- /mnt/ai/apps/wav2lip/repo/ (git clone Rudrabha/Wav2Lip)
- /mnt/ai/apps/wav2lip/checkpoints/wav2lip_gan.pth (416MB)
- /mnt/ai/apps/wav2lip/checkpoints/s3fd.pth (80MB，改名为s3fd-619a316812.pth)

### 单次推理
```bash
docker run --rm --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  -v /mnt/ai/apps/wav2lip/repo:/wav2lip \
  -v /mnt/ai/apps/wav2lip/checkpoints:/wav2lip/checkpoints \
  -v /path/to/input:/input \
  -v /output:/output \
  musetalk-api:local \
  bash -c "pip install -q librosa==0.9.2 2>/dev/null && mkdir -p /root/.cache/torch/hub/checkpoints/ && cp /wav2lip/checkpoints/s3fd.pth /root/.cache/torch/hub/checkpoints/s3fd-619a316812.pth && cd /wav2lip && python3 inference.py --checkpoint_path checkpoints/wav2lip_gan.pth --face /input/avatar.jpg --audio /input/clip.mp3 --outfile /output/result.mp4 --pads 0 20 0 0 --nosmooth"
```

### ADB推送相册
```bash
adb -s 89f5ae98 push result.mp4 /sdcard/DCIM/Camera/result.mp4
adb -s 89f5ae98 shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/DCIM/Camera/result.mp4
```

### 注意
- librosa必须用0.9.2（新版API不兼容）
- s3fd.pth需手动复制到torch hub缓存（容器内无网络）
- 支持图片和视频作为face输入

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
