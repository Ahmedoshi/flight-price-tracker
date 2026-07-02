from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config.settings import settings
from app.database.database import get_all_flights
from app.services.flight_service import FlightService


scheduler = AsyncIOScheduler(timezone=settings.timezone)


async def hourly_check(application):

    flights = get_all_flights()

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

        if result.price <= flight.max_price:

            await application.bot.send_message(
                chat_id=settings.chat_id,
                text=(
                    "🔥 Price Alert\n\n"
                    f"{flight.origin} ➜ {flight.destination}\n"
                    f"Airline: {result.airline}\n"
                    f"Price: {result.price:.0f} {result.currency}\n"
                    f"Target: {flight.max_price:.0f} {result.currency}"
                ),
            )


def start_scheduler(application):

    scheduler.add_job(
        hourly_check,
        "interval",
        hours=settings.check_interval,
        args=[application],
        id="hourly-flight-check",
        replace_existing=True,
    )

    scheduler.start()