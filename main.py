from loguru import logger
from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    PicklePersistence,
)

from app.config.settings import settings, PROJECT_ROOT

from app.bot.handlers import (
    start,
    status,
    check,
    check_now,
    add,
    list,
    delete,
    history,
    stats,
    run_scheduler,
)

from app.bot.callbacks import button_click
from app.bot.conversations import (
    add_flight_conversation,
    check_flight_conversation,
    edit_flight_conversation,
)

from app.database.database import initialize_database
from app.scheduler.scheduler import start_scheduler

logger.add(
    PROJECT_ROOT / "logs" / "bot.log",
    rotation="1 week",
    retention="4 weeks",
    level=settings.log_level,
)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Catch-all error handler.

    Without this, python-telegram-bot falls back to dumping raw
    tracebacks (see the historical error.txt in this repo) instead of
    logging them cleanly and letting the bot keep running.
    """

    logger.opt(exception=context.error).error(
        "Unhandled exception while processing update {}", update
    )

    if isinstance(update, Update) and update.effective_message:

        try:
            await update.effective_message.reply_text(
                "⚠️ Something went wrong handling that request. Please try again."
            )
        except Exception:
            pass


async def post_init(application: Application):

    print("=" * 40)
    print("BOT TOKEN:", settings.bot_token[:15] + "...")
    print("CHAT ID:", settings.chat_id)
    print("=" * 40)

    await application.bot.set_my_commands(
        [
            BotCommand("start", "Start Flight Tracker"),
            BotCommand("status", "System Status"),
            BotCommand("check", "Check Flight Price"),
            BotCommand("add", "Add Flight"),
            BotCommand("list", "My Flights"),
            BotCommand("delete", "Delete Flight"),
            BotCommand("history", "Price History"),
            BotCommand("stats", "Price Analytics"),
            BotCommand("run_scheduler", "Run Scheduler"),
        ]
    )

    start_scheduler(application)


def main():

    initialize_database()

    print("===================================")
    print(" Flight Price Tracker")
    print(" Telegram Bot Started")
    print("===================================")

    # Without this, every Add/Check/Edit wizard's progress (and any
    # in-flight Advanced Filters selection) lives only in memory - a
    # Railway restart/redeploy mid-conversation wipes it, and the next
    # button tap silently falls through to the generic menu handler
    # instead of continuing the wizard. Persisting to disk means a
    # restart resumes exactly where the user left off.
    persistence_path = PROJECT_ROOT / "data" / "bot_persistence.pickle"
    persistence_path.parent.mkdir(parents=True, exist_ok=True)
    persistence = PicklePersistence(filepath=persistence_path)

    application = (
        Application.builder()
        .token(settings.bot_token)
        .post_init(post_init)
        .persistence(persistence)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("check", check))
    application.add_handler(CommandHandler("check_now", check_now))
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("list", list))
    application.add_handler(CommandHandler("delete", delete))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("run_scheduler", run_scheduler))

    # Conversation wizards must be registered before the catch-all
    # button_click handler so their menu_add / menu_check / edit_<id>
    # callbacks are matched first.
    application.add_handler(add_flight_conversation)
    application.add_handler(check_flight_conversation)
    application.add_handler(edit_flight_conversation)

    application.add_handler(
        CallbackQueryHandler(button_click)
    )

    application.add_error_handler(on_error)

    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()