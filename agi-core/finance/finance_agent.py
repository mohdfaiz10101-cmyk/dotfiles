"""
Finance Agent — FastAPI service on port 9811.
Why: Manage bank cards, transactions, OCR bank statements via unified API.
What: CRUD for cards/transactions, OCR via LiteLLM doubao vision, repayment reminders.
Test: curl http://localhost:9811/cards → [] on fresh start.
"""

import json
import os
import uuid
import base64
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PORT = 9811
DATA_DIR = Path(__file__).parent / "data"
CARDS_FILE = DATA_DIR / "cards.json"
TRANSACTIONS_FILE = DATA_DIR / "transactions.json"
ALERTS_FILE = DATA_DIR / "alerts.json"

LITELLM_BASE = "http://localhost:4000/v1"
LITELLM_KEY = "sk-litellm-charlie-2026"
OCR_MODEL_PRIMARY = "doubao-1-5-vision-pro-32k"
OCR_MODEL_FALLBACK = "claude-sonnet-4-6"

SMS_PARSE_PROMPT = (
    "你是银行短信解析器。从以下银行短信/通知中提取结构化信息。\n"
    "提取字段：\n"
    "- bank_name: 银行名称（如'浦发银行'，从短信来源或内容推断）\n"
    "- card_last4: 卡号后四位（如有，否则null）\n"
    "- date: 交易日期 YYYY-MM-DD（如'26.04.23'→'2026-04-23'）\n"
    "- amount: 金额数字（如有，否则0）\n"
    "- merchant: 商户/地点（如'白色刷卡机'）\n"
    "- transaction_type: '消费'|'还款'|'转账'|'风险预警'|'账单提醒'|'其他'\n"
    "- is_risk_alert: true/false（是否含风险/异常/欺诈提示）\n"
    "- risk_level: 'low'|'medium'|'high'（is_risk_alert=true时填写）\n"
    "- note: 完整原文摘要（≤100字）\n"
    "返回纯JSON，不要markdown代码块。"
)

OCR_PROMPT = (
    "请识别这张银行账单图片，提取：交易日期、金额、商户名称、"
    "交易类型（消费/还款/转账）、账户余额。"
    '以JSON格式返回：{"date": "YYYY-MM-DD", "amount": 0.0, '
    '"merchant": "商户名", "transaction_type": "消费|还款|转账", '
    '"balance": 0.0, "raw_text": "识别到的原始文本"}'
)


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def _ensure_data_dir() -> None:
    """Why: data/ may not exist on first run. What: create dir + empty JSON files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for f in (CARDS_FILE, TRANSACTIONS_FILE, ALERTS_FILE):
        if not f.exists():
            f.write_text("[]", encoding="utf-8")
    for f in (CARDS_FILE, TRANSACTIONS_FILE):
        if not f.exists():
            f.write_text("[]", encoding="utf-8")
            os.chmod(f, 0o600)


def _read_json(path: Path) -> list:
    """Read JSON list from file, return [] on error."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write_json(path: Path, data: list) -> None:
    """Write JSON list atomically."""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(path, 0o600)


_ensure_data_dir()

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class BankCard(BaseModel):
    """Bank card data model for credit/debit cards."""
    id: str = ""
    bank_name: str
    card_last4: str
    card_type: str          # "credit" or "debit"
    bound_phone: str = ""
    bound_account: str = ""
    billing_date: int = 0   # day of month, 0 for debit
    due_date: int = 0       # day of month, 0 for debit
    credit_limit: float = 0.0
    current_balance: float = 0.0
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""


class BankCardUpdate(BaseModel):
    """Partial update model — all fields optional."""
    bank_name: Optional[str] = None
    card_last4: Optional[str] = None
    card_type: Optional[str] = None
    bound_phone: Optional[str] = None
    bound_account: Optional[str] = None
    billing_date: Optional[int] = None
    due_date: Optional[int] = None
    credit_limit: Optional[float] = None
    current_balance: Optional[float] = None
    notes: Optional[str] = None


class Transaction(BaseModel):
    """Bank transaction record."""
    id: str = ""
    card_id: str
    date: str               # YYYY-MM-DD
    amount: float
    merchant: str
    transaction_type: str   # 消费 / 还款 / 转账
    note: str = ""
    created_at: str = ""


class SmsParseRequest(BaseModel):
    """Raw SMS text to parse and optionally auto-record."""
    text: str
    auto_record: bool = True   # auto write transaction if parsed successfully


class OcrRequest(BaseModel):
    """OCR request with base64-encoded image."""
    image_base64: str
    image_mime: str = "image/jpeg"


class OcrConfirmRequest(BaseModel):
    """Confirm OCR result and write as transaction."""
    card_id: str
    date: str
    amount: float
    merchant: str
    transaction_type: str
    note: str = ""


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Finance Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------

@app.get("/cards")
def list_cards() -> list:
    """List all bank cards. Test: GET /cards → []."""
    return _read_json(CARDS_FILE)


@app.post("/cards", status_code=201)
def create_card(card: BankCard) -> dict:
    """Create a new bank card with auto-generated id and timestamps."""
    cards = _read_json(CARDS_FILE)
    now = datetime.utcnow().isoformat()
    new_card = card.model_dump()
    new_card["id"] = str(uuid.uuid4())
    new_card["created_at"] = now
    new_card["updated_at"] = now
    cards.append(new_card)
    _write_json(CARDS_FILE, cards)
    return new_card


@app.put("/cards/{card_id}")
def update_card(card_id: str, update: BankCardUpdate) -> dict:
    """Update card fields by id. Test: PUT /cards/{id} with partial body."""
    cards = _read_json(CARDS_FILE)
    for i, c in enumerate(cards):
        if c["id"] == card_id:
            for field, value in update.model_dump(exclude_none=True).items():
                c[field] = value
            c["updated_at"] = datetime.utcnow().isoformat()
            cards[i] = c
            _write_json(CARDS_FILE, cards)
            return c
    raise HTTPException(status_code=404, detail="Card not found")


@app.delete("/cards/{card_id}")
def delete_card(card_id: str) -> dict:
    """Delete card by id. Also removes related transactions."""
    cards = _read_json(CARDS_FILE)
    remaining = [c for c in cards if c["id"] != card_id]
    if len(remaining) == len(cards):
        raise HTTPException(status_code=404, detail="Card not found")
    _write_json(CARDS_FILE, remaining)

    # Remove related transactions
    txns = _read_json(TRANSACTIONS_FILE)
    _write_json(TRANSACTIONS_FILE, [t for t in txns if t["card_id"] != card_id])
    return {"deleted": card_id}


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

@app.get("/transactions")
def list_transactions(
    card_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list:
    """List transactions with optional card_id filter and pagination."""
    txns = _read_json(TRANSACTIONS_FILE)
    if card_id:
        txns = [t for t in txns if t["card_id"] == card_id]
    txns.sort(key=lambda t: t.get("date", ""), reverse=True)
    return txns[offset : offset + limit]


@app.post("/transactions", status_code=201)
def create_transaction(txn: Transaction) -> dict:
    """Manually add a transaction record."""
    txns = _read_json(TRANSACTIONS_FILE)
    new_txn = txn.model_dump()
    new_txn["id"] = str(uuid.uuid4())
    new_txn["created_at"] = datetime.utcnow().isoformat()
    txns.append(new_txn)
    _write_json(TRANSACTIONS_FILE, txns)
    return new_txn


@app.post("/transactions/from-ocr", status_code=201)
def create_transaction_from_ocr(req: OcrConfirmRequest) -> dict:
    """Write confirmed OCR result as a transaction."""
    txns = _read_json(TRANSACTIONS_FILE)
    new_txn = {
        "id": str(uuid.uuid4()),
        "card_id": req.card_id,
        "date": req.date,
        "amount": req.amount,
        "merchant": req.merchant,
        "transaction_type": req.transaction_type,
        "note": req.note,
        "created_at": datetime.utcnow().isoformat(),
    }
    txns.append(new_txn)
    _write_json(TRANSACTIONS_FILE, txns)
    return new_txn


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------

async def _call_ocr_vision(image_base64: str, image_mime: str, model: str) -> dict:
    """
    Why: Abstract LiteLLM vision call for reuse and fallback.
    What: Send base64 image to vision model, parse JSON from response.
    Test: Mock httpx to return valid JSON, assert parsed dict matches.
    """
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": OCR_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{image_mime};base64,{image_base64}"},
                    },
                ],
            }
        ],
        "max_tokens": 1024,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{LITELLM_BASE}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

    # Extract JSON from response
    import re
    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    return {"raw_text": content, "date": "", "amount": 0.0, "merchant": "", "transaction_type": "消费", "balance": 0.0}


@app.post("/ocr/bank-statement")
async def ocr_bank_statement(req: OcrRequest) -> dict:
    """
    Why: Allow users to photograph bank statements for quick data entry.
    What: Send image to doubao vision model, fallback to claude-sonnet-4-6.
    Test: POST with valid base64 image → returns structured JSON with date/amount/merchant.
    """
    try:
        return await _call_ocr_vision(req.image_base64, req.image_mime, OCR_MODEL_PRIMARY)
    except Exception as primary_err:
        try:
            result = await _call_ocr_vision(req.image_base64, req.image_mime, OCR_MODEL_FALLBACK)
            result["_fallback"] = True
            result["_primary_error"] = str(primary_err)
            return result
        except Exception as fallback_err:
            raise HTTPException(
                status_code=502,
                detail=f"OCR failed. Primary: {primary_err}. Fallback: {fallback_err}",
            )


# ---------------------------------------------------------------------------
# SMS Parse
# ---------------------------------------------------------------------------

async def _call_llm_text(prompt: str, user_text: str) -> dict:
    """Call LiteLLM text model to parse structured data from SMS."""
    payload = {
        "model": "deepseek-v3.2",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_text},
        ],
        "max_tokens": 512,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{LITELLM_BASE}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    import re
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"LLM returned no JSON: {content[:200]}")


def _match_card(parsed: dict, cards: list) -> dict | None:
    """Find best matching card by bank_name + card_last4."""
    bank = (parsed.get("bank_name") or "").replace("信用卡", "").strip()
    last4 = parsed.get("card_last4") or ""
    best = None
    for c in cards:
        name_match = bank and bank in c["bank_name"]
        last4_match = last4 and last4 == c["card_last4"]
        if name_match and last4_match:
            return c
        if name_match and not best:
            best = c
        if last4_match and not best:
            best = c
    return best


@app.post("/parse-sms")
async def parse_sms(req: SmsParseRequest) -> dict:
    """
    Intelligently parse bank SMS/notification text.
    Extracts transaction info, matches card, auto-records if auto_record=True.
    Also saves risk alerts to alerts.json.
    """
    parsed = await _call_llm_text(SMS_PARSE_PROMPT, req.text)
    parsed["raw_sms"] = req.text
    parsed["parsed_at"] = datetime.utcnow().isoformat()

    cards = _read_json(CARDS_FILE)
    matched_card = _match_card(parsed, cards)
    parsed["matched_card_id"] = matched_card["id"] if matched_card else None
    parsed["matched_card"] = (
        f"{matched_card['bank_name']} *{matched_card['card_last4']}" if matched_card else None
    )

    # Save risk alert
    if parsed.get("is_risk_alert"):
        alerts = _read_json(ALERTS_FILE)
        alert = {
            "id": str(uuid.uuid4()),
            "card_id": parsed.get("matched_card_id"),
            "bank_name": parsed.get("bank_name"),
            "card_last4": parsed.get("card_last4"),
            "risk_level": parsed.get("risk_level", "medium"),
            "note": parsed.get("note", req.text[:200]),
            "raw_sms": req.text,
            "created_at": parsed["parsed_at"],
        }
        alerts.append(alert)
        _write_json(ALERTS_FILE, alerts)
        parsed["alert_saved"] = True

    # Auto-record transaction if amount > 0 and card matched
    txn_saved = None
    if req.auto_record and matched_card and (parsed.get("amount") or 0) > 0:
        txns = _read_json(TRANSACTIONS_FILE)
        txn_date = parsed.get("date") or date.today().isoformat()
        new_txn = {
            "id": str(uuid.uuid4()),
            "card_id": matched_card["id"],
            "date": txn_date,
            "amount": float(parsed.get("amount", 0)),
            "merchant": parsed.get("merchant") or "未知商户",
            "transaction_type": parsed.get("transaction_type") or "消费",
            "note": parsed.get("note") or req.text[:200],
            "is_risk": parsed.get("is_risk_alert", False),
            "created_at": parsed["parsed_at"],
        }
        txns.append(new_txn)
        _write_json(TRANSACTIONS_FILE, txns)
        txn_saved = new_txn["id"]
        parsed["txn_saved"] = txn_saved

    return parsed


@app.get("/alerts")
def list_alerts(card_id: Optional[str] = None) -> list:
    """List risk alerts, optionally filtered by card_id."""
    alerts = _read_json(ALERTS_FILE)
    if card_id:
        alerts = [a for a in alerts if a.get("card_id") == card_id]
    return sorted(alerts, key=lambda a: a.get("created_at", ""), reverse=True)


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------

@app.get("/reminders")
def get_reminders() -> list:
    """
    Why: Alert users before credit card due dates to avoid late fees.
    What: Calculate days until due_date for each credit card, sort ascending.
    Test: Card with due_date=today → days_until=0, status=today.
    """
    cards = _read_json(CARDS_FILE)
    today = date.today()
    reminders = []

    for c in cards:
        if c.get("card_type") != "credit":
            continue
        due_day = c.get("due_date", 0)
        if not due_day:
            continue

        # Next due date calculation
        try:
            next_due = date(today.year, today.month, due_day)
            if next_due < today:
                # Roll to next month
                if today.month == 12:
                    next_due = date(today.year + 1, 1, due_day)
                else:
                    next_due = date(today.year, today.month + 1, due_day)
        except ValueError:
            # Handle months without day 31 etc.
            import calendar
            last_day = calendar.monthrange(today.year, today.month)[1]
            next_due = date(today.year, today.month, min(due_day, last_day))
            if next_due < today:
                next_month = today.month + 1 if today.month < 12 else 1
                next_year = today.year if today.month < 12 else today.year + 1
                last_day = calendar.monthrange(next_year, next_month)[1]
                next_due = date(next_year, next_month, min(due_day, last_day))

        days_until = (next_due - today).days
        status = "today" if days_until == 0 else ("urgent" if days_until <= 3 else ("warning" if days_until <= 7 else "normal"))

        reminders.append({
            "card_id": c["id"],
            "bank_name": c["bank_name"],
            "card_last4": c["card_last4"],
            "due_date": due_day,
            "next_due": next_due.isoformat(),
            "days_until": days_until,
            "status": status,
            "current_balance": c.get("current_balance", 0.0),
        })

    reminders.sort(key=lambda r: r["days_until"])
    return reminders


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
