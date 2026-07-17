import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from loguru import logger
from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    Defaults,
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
            BotCommand("check_now", "Check All Saved Flights Now"),
            BotCommand("run_scheduler", "Run Scheduler"),
        ]
    )

    start_scheduler(application)


class _HealthHandler(BaseHTTPRequestHandler):
    """Responds 200 OK to any GET - Koyeb's free tier only supports
    Web Services (not Worker Services), so this bot - which is really
    a background Telegram-polling process with no HTTP API of its own
    - needs *something* listening on $PORT for Koyeb's health check to
    pass. An external pinger (e.g. cron-job.org) hits this on a
    schedule too, which keeps the free instance from scaling to zero
    after an hour of no traffic.
    """

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format, *args):
        # Quiet - this gets hit every few minutes by health checks and
        # the keepalive pinger, and would otherwise spam the real logs.
        pass


def _start_health_server():

    port = int(os.environ.get("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    server.serve_forever()


def main():

    initialize_database()

    # Runs in a daemon thread so it never blocks/delays shutdown of
    # the main process - it's purely there to satisfy Koyeb's Web
    # Service health check and keepalive pings. No-op on platforms
    # (like Railway) that don't need it.
    threading.Thread(target=_start_health_server, daemon=True).start()

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

    # HTML parse mode by default means every screen/message can use
    # <b>bold</b>/<i>italic</i>/<code>monospace</code> without passing
    # parse_mode= at every single call site - one flag, applies
    # everywhere (bot.send_message, message.reply_text/reply_photo,
    # query.edit_message_text, the scheduler's alert sends, etc).
    defaults = Defaults(parse_mode=ParseMode.HTML)

    application = (
        Application.builder()
        .token(settings.bot_token)
        .defaults(defaults)
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