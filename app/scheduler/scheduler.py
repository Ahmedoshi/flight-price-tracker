from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config.settings import settings
from app.database.database import get_all_flights
from app.services.analytics_service import AnalyticsService
from app.services.flight_service import FlightService
from app.services.notification_rules import evaluate_alert
from app.services.tracking_service import TrackingService


scheduler = AsyncIOScheduler(timezone=settings.timezone)


async def hourly_check(application):

    flights = get_all_flights()

    if not flights:
        return

    service = FlightService()
    tracking = TrackingService()
    analytics = AnalyticsService()

    now = datetime.now(ZoneInfo(settings.timezone))

    for flight in flights:

        try:
            result = await service.cheapest_flight(
                origin=flight.origin,
                destination=flight.destination,
                departure_date=flight.departure_date,
                return_date=flight.return_date,
                date_flex_days=flight.date_flex_days,
                trip_type=flight.trip_type,
                cabin_class=flight.cabin_class,
                max_stops=flight.max_stops,
            )

        except ValueError:
            # Bad/legacy data shouldn't stop the rest of the batch.
            continue

        if result is None:
            continue

        decision = evaluate_alert(flight, result.price, now)

        tracking.update_tracking(
            flight_id=flight.id,
            last_price=result.price,
            last_airline=result.airline,
            lowest_price_seen=decision.lowest_price_seen,
            last_notified_price=(
                result.price if decision.should_notify else flight.last_notified_price
            ),
            last_checked_at=now.isoformat(),
        )

        if not decision.should_notify:
            continue

        header = "🚨 EXCEPTIONAL FARE ALERT 🚨" if decision.escalate else "🔥 Price Alert"

        text = (
            f"{header}\n\n"
            f"{result.origin} ➜ {result.destination}\n"
            f"📅 {result.departure_date} / 🔁 {result.return_date}\n"
            f"🏢 {result.provider}\n"
            f"Airline: {result.airline}\n"
            f"Price: {result.price:.0f} {result.currency}\n"
            f"Target: {flight.max_price:.0f} {result.currency}\n"
            f"Why: {decision.reason}"
        )

        if result.booking_url:
            text += f"\n🔗 {result.booking_url}"

        stats = analytics.compute_stats(flight, since_days=settings.analytics_window_days)

        if stats is not None:
            recommendation = analytics.recommendation(result.price, stats)
            text += f"\n\n{recommendation}"

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