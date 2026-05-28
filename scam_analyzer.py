import httpx
import os
from dotenv import load_dotenv

load_dotenv()

LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "https://ai-server-lime.vercel.app/api/chat")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

SYSTEM_PROMPT = """You are an AI Scam Shield assistant. Analyze the message forwarded by the user and respond with:

1. **Verdict**: Safe / Suspicious / Dangerous
2. **Confidence**: percentage (e.g., 85%)
3. **Scam Type**: (if applicable) e.g., UPI fraud, fake KYC, job scam, phishing, OTP theft, courier scam, investment scam, impersonation
4. **Red Flags**: bullet points of why this looks suspicious
5. **Action**: what the user should do

Keep your response concise and easy to understand. Use simple language suitable for non-technical users.

IMPORTANT: Reply ENTIRELY in {language}. All headings, explanations, and action items must be in {language}."""


LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "ur": "Urdu",
}


async def analyze_message(text: str, lang: str = "en") -> str:
    """Send message to LLM for scam analysis."""
    language = LANGUAGE_NAMES.get(lang, "English")
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

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(LLM_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    # Handle OpenAI-compatible response format
    if "choices" in data:
        return data["choices"][0]["message"]["content"]
    # Handle other formats
    if "message" in data:
        return data["message"].get("content", str(data))
    return str(data)
