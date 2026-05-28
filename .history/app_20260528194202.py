import os
import logging
from fastapi import FastAPI, Request, Query, HTTPException
from scam_analyzer import analyze_message
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Scam Shield - WhatsApp Bot")

# WhatsApp Config
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "scam-shield-verify-token")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")


@app.get("/")
def health():
    return {"status": "AI Scam Shield is running"}


@app.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Meta sends a GET request to verify your webhook URL."""
    if hub_mode == "subscribe" and hub_token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def handle_webhook(request: Request):
    """Receive incoming WhatsApp messages and respond with scam analysis."""
    body = await request.json()

    try:
        entry = body.get("entry", [])
        if not entry:
            return {"status": "no entry"}

        changes = entry[0].get("changes", [])
        if not changes:
            return {"status": "no changes"}

        value = changes[0].get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return {"status": "no messages"}

        message = messages[0]
        sender = message["from"]
        msg_type = message.get("type", "")

        # Handle text messages
        if msg_type == "text":
            text = message["text"]["body"]
            logger.info(f"Received message from {sender}: {text[:50]}...")

            # Analyze for scam
            verdict = await analyze_message(text)

            # Send reply
            await send_whatsapp_reply(sender, verdict)

        # Handle image messages (screenshots)
        elif msg_type == "image":
            await send_whatsapp_reply(
                sender,
                "📸 Screenshot analysis coming soon! For now, please type or paste the text from the message you want me to check.",
            )

        else:
            await send_whatsapp_reply(
                sender,
                "👋 Forward me any suspicious message (SMS, WhatsApp, email) and I'll tell you if it's a scam!",
            )

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")

    return {"status": "ok"}


async def send_whatsapp_reply(to: str, text: str):
    """Send a reply back via WhatsApp Cloud API."""
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to send message: {response.text}")
        else:
            logger.info(f"Reply sent to {to}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
