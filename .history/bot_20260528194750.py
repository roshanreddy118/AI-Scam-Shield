import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from scam_analyzer import analyze_message

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡️ *AI Scam Shield*\n\n"
        "Forward me any suspicious message — SMS, WhatsApp, email — "
        "and I'll tell you if it's a scam.\n\n"
        "Just paste or forward the text here!",
        parse_mode="Markdown",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        await update.message.reply_text("Please send me a text message to analyze.")
        return

    logger.info(f"Analyzing message from {update.message.from_user.id}: {text[:50]}...")

    # Show typing indicator
    await update.message.chat.send_action("typing")

    try:
        verdict = await analyze_message(text)
        await update.message.reply_text(verdict, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        await update.message.reply_text(
            "⚠️ Sorry, I couldn't analyze that message right now. Please try again."
        )


def main():
    if not TELEGRAM_TOKEN:
        print("ERROR: Set TELEGRAM_TOKEN in .env file")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🛡️ AI Scam Shield bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
