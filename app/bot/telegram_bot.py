from telegram.ext import (
    Application,
    CommandHandler,
)

from app.config.settings import settings
from app.bot.handlers import start, status, check_now


class FlightPriceBot:

    def __init__(self):

        self.app = (
            Application.builder()
            .token(settings.bot_token)
            .build()
        )

        self.app.add_handler(CommandHandler("start", start))
        self.app.add_handler(CommandHandler("status", status))
        self.app.add_handler(CommandHandler("check_now", check_now))

    def run(self):

        print("===================================")
        print(" Flight Price Tracker")
        print(" Telegram Bot Started")
        print("===================================")

        self.app.run_polling()