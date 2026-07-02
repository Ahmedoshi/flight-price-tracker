from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config.settings import settings
from app.database.database import SessionLocal
from app.database.crud import get_all_flights
from app.services.flight_service import FlightService


scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)


async def hourly_check(application):

    db = SessionLocal()

    try:
        flights = get_all_flights(db)

        if not flights:
            return

        service = FlightService()

        for flight in flights:

            result = await service.cheapest_flight(
                origin=flight.origin,
                destination=flight.destination,
                departure_date=flight.departure_date,
                return_date=flight.return_date,
            )

            if result is None:
                continue

            message = (
                "✈️ Hourly Flight Check\n\n"
                f"{flight.origin} ➜ {flight.destination}\n"
                f"Price: {result.price:.0f} {result.currency}\n"
                f"Airline: {result.airline}"
            )

            await application.bot.send_message(
                chat_id=settings.CHAT_ID,
                text=message,
            )

    finally:
        db.close()


def start_scheduler(application):

    scheduler.add_job(
        hourly_check,
        "interval",
        hours=settings.CHECK_INTERVAL,
        args=[application],
        id="hourly-flight-check",
        replace_existing=True,
    )

    scheduler.start()