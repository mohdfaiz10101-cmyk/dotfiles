#!/usr/bin/env python3
"""
虚拟人视频生成流水线
流程: 文案 → GPT-SoVITS(TTS) → MuseTalk(数字人) → FFmpeg(竖屏) → 输出

用法:
  python3 ~/agi/video_pipeline.py --text "你最大的骄傲，不是你的成就，而是你的女儿"
  python3 ~/agi/video_pipeline.py --template  # 随机取今日文案模板
"""

import httpx, json, subprocess, argparse, random
from pathlib import Path
from datetime import datetime

SOVITS_API = "http://localhost:9880"
MUSETALK_API = "http://localhost:9881"

DATA_DIR = Path.home() / "agi" / "data"
AVATAR_IMAGE = DATA_DIR / "avatar" / "niumoumou.jpg"   # 人脸参考图
AVATAR_VIDEO = DATA_DIR / "avatar" / "niuhouhuo_ref.mp4"  # 参考视频（备用）
OUTPUT_DIR = DATA_DIR / "videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_template() -> str:
    """从今日文案库随机取一条"""
    today = datetime.now().strftime("%Y-%m-%d")
    f = DATA_DIR / f"copywriting-{today}.json"
    if f.exists():
        data = json.loads(f.read_text())
        templates = data.get("ai_templates", [])
        if templates:
            return random.choice(templates)
    return "你最大的骄傲，不是你赚了多少钱，而是你的孩子为你骄傲。"


def tts(text: str, voice_model: str = "niuhouhuo") -> Path:
    """GPT-SoVITS TTS → 返回音频路径"""
    print(f"[TTS] 生成语音: {text[:30]}...")
    ts = datetime.now().strftime("%H%M%S")
    out = DATA_DIR / "voice" / f"tts_{ts}.wav"

    # 参考音频（声音克隆）
    ref_audio = DATA_DIR / "voice" / "niumoumou.wav"
    ref_text = "让我们一起加油，每一天都是新的开始。"  # 参考音频对应文字

    payload = {
        "refer_wav_path": str(ref_audio),
        "prompt_text": ref_text,
        "prompt_language": "zh",
        "text": text,
        "text_language": "zh",
    }
    r = httpx.post(f"{SOVITS_API}/", json=payload, timeout=60)
    out.write_bytes(r.content)
    print(f"[TTS] → {out} ({len(r.content)//1024}KB)")
    return out


def generate_video(audio_path: Path, avatar_video: Path) -> Path:
    """MuseTalk 数字人视频生成"""
    print(f"[MuseTalk] 生成数字人视频...")
    ts = datetime.now().strftime("%H%M%S")
    out = OUTPUT_DIR / f"video_{ts}_raw.mp4"

    # MuseTalk 接受图片+音频，生成口型同步视频
    avatar = AVATAR_IMAGE if AVATAR_IMAGE.exists() else avatar_video
    with open(audio_path, "rb") as af, open(avatar, "rb") as imgf:
        r = httpx.post(
            f"{MUSETALK_API}/inference",
            files={"audio": ("audio.wav", af, "audio/wav"),
                   "avatar": (avatar.name, imgf, "image/jpeg")},
            timeout=300,
        )
    out.write_bytes(r.content)
    print(f"[MuseTalk] → {out}")
    return out


def postprocess(video_path: Path, text: str) -> Path:
    """FFmpeg 竖屏处理 + 字幕"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUTPUT_DIR / f"final_{ts}.mp4"

    # 竖屏 1080x1920 + 字幕文字叠加
    subtitle = text.replace("，", "，\n") if len(text) > 20 else text
    filter_complex = (
        "scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"drawtext=text='{subtitle}':fontcolor=white:fontsize=40:"
        "x=(w-text_w)/2:y=h-120:box=1:boxcolor=black@0.5:boxborderw=10"
    )
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", filter_complex,
        "-c:v", "libx264", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        str(out)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"[FFmpeg] → {out}")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", help="文案内容")
    parser.add_argument("--template", action="store_true", help="随机使用今日模板")
    args = parser.parse_args()

    text = args.text or (get_template() if args.template else None)
    if not text:
        text = get_template()
    print(f"\n[流水线] 文案: {text}\n")

    # 检查服务
    for name, url in [("GPT-SoVITS", f"{SOVITS_API}/tts"), ("MuseTalk", f"{MUSETALK_API}/health")]:
        try:
            r = httpx.get(url.replace("/tts", "").replace("/health", "") + "/", timeout=3)
            print(f"[OK] {name} 在线")
        except Exception as e:
            print(f"[FAIL] {name} 不可用: {e}")
            print("→ 请先: cd ~/agi/docker/virtual-person && docker compose up -d")
            return

    audio = tts(text)
    raw_video = generate_video(audio, AVATAR_VIDEO)
    final = postprocess(raw_video, text)
    print(f"\n[完成] 视频已生成: {final}")


if __name__ == "__main__":
    main()
