from telegram.ext import (
    Application,
    CommandHandler,
)

from app.config.settings import settings

from app.bot.handlers import (
    start,
    status,
    check_now,
    add,
    list,
    delete,
)

from app.database.database import initialize_database


def main():

    initialize_database()

    print("===================================")
    print(" Flight Price Tracker")
    print(" Telegram Bot Started")
    print("===================================")

    application = (
        Application.builder()
        .token(settings.bot_token)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("check_now", check_now))
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("list", list))
    application.add_handler(CommandHandler("delete", delete))

    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()