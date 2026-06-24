import hashlib
import hmac
import base64
import json
import os

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

app = FastAPI(title="webhook-translate", version="0.1.0")


def verify_line_signature(body: bytes, signature: str) -> bool:
    """驗證 LINE Webhook 簽章，防止非法請求。"""
    if not LINE_CHANNEL_SECRET:
        return True  # 開發環境可略過
    digest = hmac.new(LINE_CHANNEL_SECRET.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


async def call_groq_translate(text: str) -> str:
    """呼叫 Groq API 進行中文 ↔ 印尼文雙向翻譯。"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.3,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一位專業的中印雙向翻譯助手。\n"
                    "1. 如果輸入是中文，請翻譯成印尼文 (Indonesian)。\n"
                    "2. 如果輸入是印尼文，請翻譯成繁體中文。\n"
                    "3. 翻譯風格要親切、易懂，適合家人與看護溝通。\n"
                    "4. 輸出只需包含翻譯後的文字，不要有任何解釋或標點符號。"
                ),
            },
            {"role": "user", "content": text},
        ],
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=headers, json=payload)

    data = resp.json()

    if resp.status_code != 200 or "choices" not in data:
        error = data.get("error", {})
        code = error.get("code", "unknown")
        msg = error.get("message", "")
        if code == "model_not_found":
            return "【錯誤】模型名稱已過期，請更新 GROQ_MODEL 環境變數。"
        if code == "invalid_api_key" or resp.status_code == 401:
            return "【錯誤】API Key 無效，請檢查 GROQ_API_KEY。"
        return f"Groq 報錯: {msg or resp.text[:100]}"

    return data["choices"][0]["message"]["content"].strip()


async def reply_to_line(reply_token: str, text: str) -> None:
    """透過 LINE Messaging API 回覆使用者。"""
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}],
    }
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, headers=headers, json=payload)


@app.get("/")
async def health_check():
    return {"status": "ok", "service": "webhook-translate"}


@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    if not verify_line_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    events = data.get("events", [])

    for event in events:
        if event.get("type") != "message":
            continue
        message = event.get("message", {})
        if message.get("type") != "text":
            continue

        user_text = message.get("text", "").strip()
        reply_token = event.get("replyToken", "")

        if not user_text or not reply_token:
            continue

        translated = await call_groq_translate(user_text)
        await reply_to_line(reply_token, translated)

    return JSONResponse(content={"status": "ok"})
