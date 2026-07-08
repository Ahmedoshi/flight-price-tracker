from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config.settings import settings
from app.database.database import get_all_flights
from app.services.analytics_service import AnalyticsService
from app.services.flight_service import FlightService
from app.services.notification_rules import evaluate_alert
from app.services.tracking_service import TrackingService
from app.services.whatsapp_service import send_whatsapp
from app.utils.airport_flags import airport_flag
from app.utils.text import esc


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

        # Look up history BEFORE this check's price is searched/saved,
        # so the "lowest this month" and "rebound" rules compare
        # against the prior baseline rather than including the very
        # price they're about to evaluate.
        monthly_stats = analytics.compute_stats(flight, since_days=30)
        monthly_low_price = monthly_stats.min_price if monthly_stats is not None else None

        recent_prices = tracking.recent_prices(flight, limit=2)
        price_before_last = recent_prices[1] if len(recent_prices) > 1 else None

        try:
            if flight.trip_type == "multi-city" and flight.legs:

                result = await service.cheapest_multi_city(
                    legs=flight.legs,
                    cabin_class=flight.cabin_class,
                    max_stops=flight.max_stops,
                )

            else:

                result = await service.cheapest_flight(
                    origin=flight.origin,
                    destination=flight.destination,
                    departure_date=flight.departure_date,
                    return_date=flight.return_date,
                    date_flex_days=flight.date_flex_days,
                    trip_type=flight.trip_type,
                    cabin_class=flight.cabin_class,
                    max_stops=flight.max_stops,
                    is_scheduled_check=True,
                )

        except ValueError:
            # Bad/legacy data shouldn't stop the rest of the batch.
            continue

        if result is None:
            continue

        stats = analytics.compute_stats(flight, since_days=settings.analytics_window_days)
        route_avg_price = stats.avg_price if stats is not None else None

        decision = evaluate_alert(
            flight,
            result.price,
            now,
            route_avg_price=route_avg_price,
            monthly_low_price=monthly_low_price,
            price_before_last=price_before_last,
        )

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

        if decision.is_flash_deal:
            header = "⚡ FLASH DEAL ⚡"
        elif decision.escalate:
            header = "🚨 EXCEPTIONAL FARE ALERT 🚨"
        elif decision.is_rebound:
            header = "↩️ Price Rebound"
        elif decision.is_monthly_low:
            header = "📅 Lowest This Month"
        else:
            header = "🔥 Price Alert"

        recommendation = analytics.recommendation(result.price, stats) if stats is not None else None

        # Telegram gets HTML formatting (bold header/price); WhatsApp
        # (via Twilio) has no idea what an HTML tag is and would show
        # literal "<b>" text to the recipient, so it gets its own plain
        # version built from the same data rather than reusing the
        # Telegram string.
        telegram_text = (
            f"<b>{header}</b>\n\n"
            f"<b>{airport_flag(result.origin)} {esc(result.origin)} ➜ "
            f"{airport_flag(result.destination)} {esc(result.destination)}</b>\n"
            f"📅 {esc(result.departure_date)} / 🔁 {esc(result.return_date)}\n"
            f"🏢 {esc(result.provider)}\n"
            f"Airline: {esc(result.airline)}\n"
            f"Price: <b>{result.price:.0f} {esc(result.currency)}</b>\n"
            f"Target: {flight.max_price:.0f} SAR\n"
            f"Why: {esc(decision.reason)}"
        )

        whatsapp_text = (
            f"{header}\n\n"
            f"{result.origin} ➜ {result.destination}\n"
            f"📅 {result.departure_date} / 🔁 {result.return_date}\n"
            f"🏢 {result.provider}\n"
            f"Airline: {result.airline}\n"
            f"Price: {result.price:.0f} {result.currency}\n"
            f"Target: {flight.max_price:.0f} SAR\n"
            f"Why: {decision.reason}"
        )

        if result.booking_url:
            telegram_text += f'\n<a href="{esc(result.booking_url)}">🔗 View Flight</a>'
            whatsapp_text += f"\n🔗 {result.booking_url}"

        if recommendation:
            telegram_text += f"\n\n<blockquote>{recommendation}</blockquote>"
            whatsapp_text += f"\n\n{recommendation}"

        await application.bot.send_message(
            chat_id=settings.chat_id,
            text=telegram_text,
        )

        # Best-effort second channel - a WhatsApp delivery problem
        # should never stop the Telegram alert above or crash the
        # scheduler, so failures here are swallowed (send_whatsapp
        # already catches and logs internally).
        await send_whatsapp(whatsapp_text)


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