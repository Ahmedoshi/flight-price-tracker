from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)

from app.config.settings import settings

from app.bot.handlers import (
    start,
    status,
    check,
    check_now,
    add,
    list,
    delete,
    history,
    run_scheduler,
    button_click,
)

from app.database.database import initialize_database
from app.scheduler.scheduler import start_scheduler


async def post_init(application: Application):

    await application.bot.set_my_commands(
        [
            BotCommand("start", "Start Flight Tracker"),
            BotCommand("status", "System status"),
            BotCommand("check", "Check flight price"),
            BotCommand("add", "Add new flight"),
            BotCommand("list", "List saved flights"),
            BotCommand("delete", "Delete saved flight"),
            BotCommand("history", "Price history"),
            BotCommand("run_scheduler", "Run scheduler now"),
        ]
    )

    start_scheduler(application)


def main():

    initialize_database()

    print("===================================")
    print(" Flight Price Tracker")
    print(" Telegram Bot Started")
    print("===================================")

    application = (
        Application.builder()
        .token(settings.bot_token)
        .post_init(post_init)
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
    application.add_handler(CommandHandler("run_scheduler", run_scheduler))

    application.add_handler(
        CallbackQueryHandler(button_click)
    )

    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()