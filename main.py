import base64
import hashlib
import hmac
import json
import logging
import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

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
        resp = await client.post(url, headers=headers, json=payload)

    if resp.status_code != 200:
        logger.error("LINE reply failed: status=%s body=%s", resp.status_code, resp.text)
    else:
        logger.info("LINE reply sent: status=%s", resp.status_code)


@app.get("/")
async def health_check():
    return {"status": "ok", "service": "webhook-translate"}


_HTML_STYLE = """
  <style>
    body {
      font-family: sans-serif; max-width: 720px;
      margin: 40px auto; padding: 0 20px;
      line-height: 1.8; color: #333;
    }
    h1 { font-size: 1.6rem; border-bottom: 2px solid #06C755; padding-bottom: 8px; }
    h2 { font-size: 1.1rem; margin-top: 2rem; }
  </style>
"""


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    line_url = "https://developers.line.biz/en/docs/line-developers-console/overview/"
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>隱私權政策</title>
  {_HTML_STYLE}
</head>
<body>
  <h1>隱私權政策</h1>
  <p>最後更新：2026 年 6 月</p>

  <h2>1. 收集的資料</h2>
  <p>本服務（中印雙向翻譯 LINE Bot）僅處理使用者透過 LINE 傳送的文字訊息，
  用於執行翻譯功能。我們不會儲存任何訊息內容或個人識別資訊。</p>

  <h2>2. 資料使用方式</h2>
  <p>使用者傳送的文字會即時轉送至 Groq API 進行翻譯，
  翻譯完成後立即回傳，不會保留於伺服器。</p>

  <h2>3. 第三方服務</h2>
  <p>本服務使用以下第三方服務：</p>
  <ul>
    <li><a href="{line_url}" target="_blank">LINE Messaging API</a></li>
    <li><a href="https://groq.com/privacy-policy/" target="_blank">Groq API</a></li>
  </ul>

  <h2>4. 聯絡方式</h2>
  <p>如有任何疑問，請透過 LINE 官方帳號與我們聯繫。</p>
</body>
</html>"""


@app.get("/terms", response_class=HTMLResponse)
async def terms_of_service():
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>服務條款</title>
  {_HTML_STYLE}
</head>
<body>
  <h1>服務條款</h1>
  <p>最後更新：2026 年 6 月</p>

  <h2>1. 服務說明</h2>
  <p>本服務提供中文與印尼文之間的雙向即時翻譯，透過 LINE 訊息平台運作，
  適合家庭照護溝通使用。</p>

  <h2>2. 使用規範</h2>
  <ul>
    <li>請勿傳送違法、歧視性或侵害他人權益的內容。</li>
    <li>本服務僅供翻譯用途，不得用於任何商業轉售行為。</li>
  </ul>

  <h2>3. 免責聲明</h2>
  <p>翻譯結果由 AI 模型產生，可能存在誤差，請勿用於醫療、法律等需要高度精確性的場合。
  本服務不對翻譯內容的準確性負擔法律責任。</p>

  <h2>4. 服務變更與終止</h2>
  <p>我們保留隨時修改或終止服務的權利，恕不另行通知。</p>

  <h2>5. 聯絡方式</h2>
  <p>如有任何疑問，請透過 LINE 官方帳號與我們聯繫。</p>
</body>
</html>"""


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

        logger.info("Translating: %r", user_text)
        translated = await call_groq_translate(user_text)
        logger.info("Translated: %r", translated)
        await reply_to_line(reply_token, translated)

    return JSONResponse(content={"status": "ok"})
