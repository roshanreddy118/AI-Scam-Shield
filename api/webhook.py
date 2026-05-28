import json
import os
import httpx

# Config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "https://ai-server-lime.vercel.app/api/chat")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

LANGUAGES = {
    "en": "English", "hi": "Hindi", "ta": "Tamil", "te": "Telugu",
    "bn": "Bengali", "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada",
    "ml": "Malayalam", "pa": "Punjabi", "ur": "Urdu",
}

LANGUAGE_LABELS = {
    "en": "English", "hi": "हिन्दी (Hindi)", "ta": "தமிழ் (Tamil)",
    "te": "తెలుగు (Telugu)", "bn": "বাংলা (Bengali)", "mr": "मराठी (Marathi)",
    "gu": "ગુજરાતી (Gujarati)", "kn": "ಕನ್ನಡ (Kannada)",
    "ml": "മലയാളം (Malayalam)", "pa": "ਪੰਜਾਬੀ (Punjabi)", "ur": "اردو (Urdu)",
}

# Simple in-memory store (resets on cold start, but acceptable for MVP)
user_languages = {}

SYSTEM_PROMPT = """You are an AI Scam Shield assistant. Analyze the message forwarded by the user and respond with:

1. **Verdict**: Safe / Suspicious / Dangerous
2. **Confidence**: percentage (e.g., 85%)
3. **Scam Type**: (if applicable) e.g., UPI fraud, fake KYC, job scam, phishing, OTP theft, courier scam, investment scam, impersonation
4. **Red Flags**: bullet points of why this looks suspicious
5. **Action**: what the user should do

Keep your response concise and easy to understand. Use simple language suitable for non-technical users.

IMPORTANT: Reply ENTIRELY in {language}. All headings, explanations, and action items must be in {language}."""


def analyze_scam(text: str, lang: str = "en") -> str:
    language = LANGUAGES.get(lang, "English")
    system_prompt = SYSTEM_PROMPT.format(language=language)

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this message for scam:\n\n{text}"},
        ],
        "temperature": 0.3,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}",
    }

    response = httpx.post(LLM_ENDPOINT, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    if "choices" in data:
        return data["choices"][0]["message"]["content"]
    if "message" in data:
        return data["message"].get("content", str(data))
    return str(data)


def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    httpx.post(url, json=payload, timeout=10)


def send_chat_action(chat_id, action="typing"):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction"
    httpx.post(url, json={"chat_id": chat_id, "action": action}, timeout=5)


def answer_callback(callback_query_id, text=""):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery"
    httpx.post(url, json={"callback_query_id": callback_query_id, "text": text}, timeout=5)


def edit_message(chat_id, message_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
    httpx.post(url, json={"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"}, timeout=5)


from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write("AI Scam Shield is running!".encode())

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        update = json.loads(body)
        process_update(update)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write("ok".encode())


def process_update(update):

    # Handle callback queries (language selection)
    if "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        message_id = query["message"]["message_id"]
        user_id = query["from"]["id"]
        data = query.get("data", "")

        if data.startswith("lang_"):
            lang_code = data.replace("lang_", "")
            user_languages[user_id] = lang_code
            lang_name = LANGUAGE_LABELS.get(lang_code, "English")
            answer_callback(query["id"])
            edit_message(chat_id, message_id, f"✅ Language set to *{lang_name}*")
        return "ok"

    # Handle messages
    message = update.get("message")
    if not message:
        return "ok"

    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "")

    # /start command
    if text == "/start":
        send_message(
            chat_id,
            "🛡️ *AI Scam Shield*\n\n"
            "Forward me any suspicious message — SMS, WhatsApp, email — "
            "and I'll tell you if it's a scam.\n\n"
            "Just paste or forward the text here!\n\n"
            "🌐 Use /language to change response language.",
        )
        return "ok"

    # /language command
    if text == "/language":
        keyboard = []
        row = []
        for code, name in LANGUAGE_LABELS.items():
            row.append({"text": name, "callback_data": f"lang_{code}"})
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        send_message(
            chat_id,
            "🌐 Choose your preferred language:",
            reply_markup={"inline_keyboard": keyboard},
        )
        return "ok"

    # Analyze message for scam
    if text and not text.startswith("/"):
        send_chat_action(chat_id)
        lang = user_languages.get(user_id, "en")
        try:
            verdict = analyze_scam(text, lang)
            send_message(chat_id, verdict)
        except Exception as e:
            send_message(chat_id, "⚠️ Sorry, I couldn't analyze that message right now. Please try again.")

    return "ok"
