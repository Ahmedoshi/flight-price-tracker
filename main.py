from app.bot.telegram_bot import FlightPriceBot
from app.database.database import initialize_database


def main():

    initialize_database()

    bot = FlightPriceBot()
    bot.run()


if __name__ == "__main__":
    main()