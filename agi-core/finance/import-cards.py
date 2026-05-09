#!/usr/bin/env python3
"""批量从图片目录识别银行账单，写入 finance-agent.
用法:
  python3 import-cards.py                    # 扫描 ~/Desktop 所有图片
  python3 import-cards.py /path/to/dir       # 指定目录
  python3 import-cards.py img1.jpg img2.png  # 指定文件
"""
import base64, json, sys
from pathlib import Path
import httpx

API = "http://localhost:9811"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

def get_mime(path: Path) -> str:
    return {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png",
            "webp":"image/webp","bmp":"image/bmp"}.get(path.suffix.lstrip(".").lower(),"image/jpeg")

def list_cards() -> list:
    return httpx.get(f"{API}/cards", timeout=5).json()

def ocr_image(path: Path) -> dict | None:
    b64 = base64.b64encode(path.read_bytes()).decode()
    r = httpx.post(f"{API}/ocr/bank-statement",
        json={"image_base64": b64, "image_mime": get_mime(path)},
        timeout=30)
    if r.status_code == 200:
        return r.json()
    print(f"  [FAIL] OCR 失败: {r.status_code} {r.text[:100]}")
    return None

def choose_card(cards: list) -> str | None:
    if not cards:
        print("[ERROR] 无银行卡，请先 POST /cards 添加")
        return None
    print("\n可用银行卡:")
    for i, c in enumerate(cards):
        print(f"  {i+1}. {c['bank_name']} *{c['card_last4']} ({c['card_type']})")
    print("  0. 跳过本张图片")
    try:
        n = int(input("选择卡片编号: ").strip())
    except (ValueError, KeyboardInterrupt):
        return None
    if n == 0:
        return None
    if 1 <= n <= len(cards):
        return cards[n-1]["id"]
    return None

def confirm_and_import(card_id: str, ocr: dict) -> bool:
    print(f"\n  OCR结果:")
    print(f"    日期: {ocr.get('date','?')}  金额: {ocr.get('amount','?')}  类型: {ocr.get('transaction_type','?')}")
    print(f"    商户: {ocr.get('merchant','?')}  余额: {ocr.get('balance','?')}")
    print(f"    原文: {str(ocr.get('raw_text',''))[:80]}")
    ans = input("  确认写入? [y/N]: ").strip().lower()
    if ans != "y":
        return False
    r = httpx.post(f"{API}/transactions/from-ocr", json={
        "card_id": card_id,
        "date": ocr.get("date", ""),
        "amount": ocr.get("amount", 0.0),
        "merchant": ocr.get("merchant", ""),
        "transaction_type": ocr.get("transaction_type", "消费"),
        "note": ocr.get("raw_text", "")[:200],
    }, timeout=10)
    if r.status_code == 200:
        print("  [OK] 已写入")
        return True
    print(f"  [FAIL] 写入失败: {r.text[:100]}")
    return False

def collect_images(args: list[str]) -> list[Path]:
    paths: list[Path] = []
    if not args:
        src = Path.home() / "Desktop"
        paths = [p for p in sorted(src.iterdir()) if p.is_file() and p.suffix.lower() in EXTS]
    else:
        for a in args:
            p = Path(a)
            if p.is_dir():
                paths += [f for f in sorted(p.iterdir()) if f.is_file() and f.suffix.lower() in EXTS]
            elif p.is_file():
                paths.append(p)
            else:
                print(f"[SKIP] 不存在: {a}")
    return paths

def main():
    images = collect_images(sys.argv[1:])
    if not images:
        print("[SKIP] 未找到图片文件")
        return

    print(f"找到 {len(images)} 张图片:")
    for p in images:
        print(f"  {p.name}")

    cards = list_cards()
    total_ok = 0

    for img in images:
        print(f"\n── {img.name} ──")
        ocr = ocr_image(img)
        if ocr is None:
            continue
        card_id = choose_card(cards)
        if card_id is None:
            print("  [SKIP]")
            continue
        if confirm_and_import(card_id, ocr):
            total_ok += 1

    print(f"\n[完成] 成功导入 {total_ok}/{len(images)} 张")

if __name__ == "__main__":
    main()
