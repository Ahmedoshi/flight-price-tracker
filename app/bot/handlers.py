from telegram import Update
from telegram.ext import ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "✈️ Flight Price Tracker Bot\n\n"
        "Bot is online."
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "✅ System Status\n\n"
        "Bot: Online\n"
        "Scheduler: Ready\n"
        "Database: Ready"
    )


async def check_now(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🔍 Checking flight prices...\n\n"
        "This feature will be implemented in the next step."
    )