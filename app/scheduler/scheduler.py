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

        try:
            result = await service.cheapest_flight(
                origin=flight.origin,
                destination=flight.destination,
                departure_date=flight.departure_date,
                return_date=flight.return_date,
                date_flex_days=flight.date_flex_days,
            )

        except ValueError:
            # Bad/legacy data shouldn't stop the rest of the batch.
            continue

        if result is None:
            continue

        if result.price <= flight.max_price:

            text = (
                "🔥 Price Alert\n\n"
                f"{result.origin} ➜ {result.destination}\n"
                f"📅 {result.departure_date} / 🔁 {result.return_date}\n"
                f"🏢 {result.provider}\n"
                f"Airline: {result.airline}\n"
                f"Price: {result.price:.0f} {result.currency}\n"
                f"Target: {flight.max_price:.0f} {result.currency}"
            )

            if result.booking_url:
                text += f"\n🔗 {result.booking_url}"

            await application.bot.send_message(
                chat_id=settings.chat_id,
                text=text,
            )


JOB_ID = "hourly-flight-check"


def start_scheduler(application):

    if scheduler.running:
        return

    scheduler.add_job(
        hourly_check,
        trigger="interval",
        hours=settings.check_interval,
        args=[application],
        id=JOB_ID,
        replace_existing=True,
    )

    scheduler.start()


def pause_scheduler():

    scheduler.pause_job(JOB_ID)


def resume_scheduler():

    scheduler.resume_job(JOB_ID)


def set_interval_hours(hours: int):

    scheduler.reschedule_job(
        JOB_ID,
        trigger="interval",
        hours=hours,
    )


def get_status():
    """Return (is_running, interval_hours) for the flight-check job."""

    job = scheduler.get_job(JOB_ID)

    if job is None:
        return False, settings.check_interval

    is_running = job.next_run_time is not None

    interval_hours = int(job.trigger.interval.total_seconds() // 3600)

    return is_running, interval_hours