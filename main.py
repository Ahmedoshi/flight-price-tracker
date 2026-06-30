from app.bot.telegram_bot import FlightPriceBot
from app.database.database import initialize_database


def main():
    # Create the database if it doesn't already exist
    initialize_database()

    # Start the Telegram bot
    bot = FlightPriceBot()
    bot.run()


if __name__ == "__main__":
    main()