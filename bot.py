import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from scam_analyzer import analyze_message

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

# Store user language preferences {user_id: language}
user_languages = {}

LANGUAGES = {
    "en": "English",
    "hi": "हिन्दी (Hindi)",
    "ta": "தமிழ் (Tamil)",
    "te": "తెలుగు (Telugu)",
    "bn": "বাংলা (Bengali)",
    "mr": "मराठी (Marathi)",
    "gu": "ગુજરાતી (Gujarati)",
    "kn": "ಕನ್ನಡ (Kannada)",
    "ml": "മലയാളം (Malayalam)",
    "pa": "ਪੰਜਾਬੀ (Punjabi)",
    "ur": "اردو (Urdu)",
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡️ *AI Scam Shield*\n\n"
        "Forward me any suspicious message — SMS, WhatsApp, email — "
        "and I'll tell you if it's a scam.\n\n"
        "Just paste or forward the text here!\n\n"
        "🌐 Use /language to change response language.",
        parse_mode="Markdown",
    )


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show language selection keyboard."""
    keyboard = []
    row = []
    for code, name in LANGUAGES.items():
        row.append(InlineKeyboardButton(name, callback_data=f"lang_{code}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌐 Choose your preferred language:", reply_markup=reply_markup
    )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection."""
    query = update.callback_query
    await query.answer()

    lang_code = query.data.replace("lang_", "")
    user_id = query.from_user.id
    user_languages[user_id] = lang_code

    lang_name = LANGUAGES.get(lang_code, "English")
    await query.edit_message_text(f"✅ Language set to *{lang_name}*", parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        await update.message.reply_text("Please send me a text message to analyze.")
        return

    user_id = update.message.from_user.id
    lang = user_languages.get(user_id, "en")

    logger.info(f"Analyzing message from {user_id} (lang={lang}): {text[:50]}...")

    # Show typing indicator
    await update.message.chat.send_action("typing")

    try:
        verdict = await analyze_message(text, lang)
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
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🛡️ AI Scam Shield bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
