from datetime import datetime, timezone

from app.bot.keyboards import (
    main_menu,
    scheduler_menu,
    flight_card,
)
from app.config.settings import settings
from app.scheduler.scheduler import get_status
from app.services import provider_health
from app.services.analytics_service import AnalyticsService, TREND_EMOJI
from app.services.tracking_service import TrackingService

tracking = TrackingService()
analytics = AnalyticsService()


def _provider_status_lines() -> str:

    providers = [
        ("Google Flights", True),
        ("Kiwi.com", bool(settings.kiwi_api_key)),
        ("Amadeus", bool(settings.amadeus_client_id and settings.amadeus_client_secret)),
        ("Duffel", bool(settings.duffel_api_key)),
        ("Skyscanner", bool(settings.skyscanner_api_key)),
    ]

    lines = []

    for name, enabled in providers:

        if not enabled:
            lines.append(f"⚪ {name} : Not configured")
            continue

        stats = provider_health.get_stats(name)

        if stats["offline"]:

            retry_mins = max(
                0,
                int((stats["disabled_until"] - datetime.now(timezone.utc)).total_seconds() // 60),
            )
            lines.append(f"🔴 {name} : Offline (retrying in ~{retry_mins}m)")
            continue

        if stats["total_checks"] == 0:
            lines.append(f"🟢 {name} : Ready")
            continue

        if stats["avg_response_seconds"] is None:
            # Has failures but hasn't tripped the auto-disable
            # threshold (or hasn't succeeded even once) yet.
            lines.append(
                f"🟡 {name} : Struggling — {stats['success_rate_pct']:.0f}% success "
                f"({stats['total_checks']} checks, {stats['consecutive_failures']} failures in a row)"
            )
            continue

        lines.append(
            f"🟢 {name} : Ready — avg {stats['avg_response_seconds']:.1f}s, "
            f"{stats['success_rate_pct']:.0f}% success ({stats['total_checks']} checks)"
        )

    return "\n".join(lines)


def home_screen():

    flights = tracking.list()
    is_running, interval_hours = get_status()

    schedule_text = (
        f"Every {interval_hours} Hour{'s' if interval_hours != 1 else ''}"
        if is_running
        else "Paused"
    )

    text = (
        "✈️ Flight Price Tracker\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👋 Welcome\n\n"
        "🟢 Bot Online\n"
        f"📍 Flights Tracked : {len(flights)}\n"
        f"⏰ Scheduler : {schedule_text}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Choose an action:"
    )

    return text, main_menu()


def status_screen():

    flights = tracking.list()
    is_running, interval_hours = get_status()

    whatsapp_ready = bool(
        settings.twilio_sid
        and settings.twilio_token
        and (settings.wa_from or settings.twilio_phone)
        and settings.whatsapp_to
    )
    whatsapp_icon = "🟢" if whatsapp_ready else "⚪"
    whatsapp_label = "Ready" if whatsapp_ready else "Not configured"

    text = (
        "ℹ️ System Status\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🟢 Bot : Online\n"
        "🟢 Database : Connected\n"
        f"{_provider_status_lines()}\n"
        f"{whatsapp_icon} WhatsApp Alerts : {whatsapp_label}\n"
        f"{'🟢' if is_running else '⏸'} Scheduler : {'Running' if is_running else 'Paused'}\n\n"
        f"📍 Saved Flights : {len(flights)}"
    )

    return text, main_menu()


def scheduler_screen():

    is_running, interval_hours = get_status()

    text = (
        "⚙️ Scheduler\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Status\n"
        f"{'🟢 Running' if is_running else '⏸ Paused'}\n\n"
        "Current Interval\n"
        f"🕑 Every {interval_hours} Hour{'s' if interval_hours != 1 else ''}"
    )

    return text, scheduler_menu()


def flights_screen():

    flights = tracking.list()

    if not flights:

        return [
            (
                "📋 My Flights\n\nNo saved flights.",
                main_menu(),
            )
        ]

    cards = []

    for position, flight in enumerate(flights, start=1):

        if flight.trip_type == "multi-city" and flight.legs:

            legs_text = "\n".join(
                f"  {i}. {leg['origin']} ➜ {leg['destination']} ({leg['date']})"
                for i, leg in enumerate(flight.legs, start=1)
            )

            filters_line = _filters_summary(flight)

            text = (
                f"✈️ Flight #{position} — 🌍 Multi-city\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{legs_text}\n\n"
                f"🎯 Target : {flight.max_price:.0f} SAR"
                f"{filters_line}"
            )

            cards.append((text, flight_card(flight.id)))
            continue

        flex_text = (
            f" (+/-{flight.date_flex_days}d)" if flight.date_flex_days else ""
        )

        return_line = (
            f"↩ Return : {flight.return_date}{flex_text}\n\n"
            if flight.trip_type == "round-trip"
            else "↩ One-way\n\n"
        )

        filters_line = _filters_summary(flight)

        text = (
            f"✈️ Flight #{position}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{flight.origin} ➜ {flight.destination}\n\n"
            f"📅 Departure : {flight.departure_date}\n"
            f"{return_line}"
            f"🎯 Target : {flight.max_price:.0f} SAR"
            f"{filters_line}"
        )

        cards.append(
            (
                text,
                flight_card(flight.id),
            )
        )

    return cards


def _filters_summary(flight) -> str:

    parts = []

    if flight.cabin_class != "economy":
        parts.append(flight.cabin_class.replace("-", " ").title())

    if flight.max_stops is not None:
        parts.append("direct only" if flight.max_stops == 0 else f"max {flight.max_stops} stop(s)")

    if not parts:
        return ""

    return "\n\n🎛 " + ", ".join(parts)


def history_screen():

    rows = tracking.history()

    if not rows:

        return (
            "📈 Price History\n\nNo price history.",
            main_menu(),
        )

    text = "📈 Price History\n\n"

    for airline, price, checked_at in rows[:10]:

        text += (
            "━━━━━━━━━━━━━━\n"
            f"{checked_at}\n\n"
            f"✈ {airline}\n"
            f"💰 {price:.0f} SAR\n\n"
        )

    return text, main_menu()


def analytics_screen():

    flights = tracking.list()

    if not flights:

        return [
            (
                "📊 Analytics\n\nNo saved flights yet.",
                main_menu(),
            )
        ]

    window_days = settings.analytics_window_days
    cards = []

    for position, flight in enumerate(flights, start=1):

        stats = analytics.compute_stats(flight, since_days=window_days)

        if stats is None:

            text = (
                f"📊 Flight #{position}\n\n"
                f"{flight.origin} ➜ {flight.destination}\n\n"
                "No price history yet — run a check first."
            )
            cards.append((text, main_menu()))
            continue

        trend_emoji = TREND_EMOJI.get(stats.trend, "➡️")
        trend_detail = f" ({abs(stats.trend_pct):.0f}%)" if stats.trend != "flat" else ""

        text = (
            f"📊 Flight #{position} — last {window_days}d\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{flight.origin} ➜ {flight.destination}\n\n"
            f"📉 Min : {stats.min_price:.0f} SAR\n"
            f"📈 Max : {stats.max_price:.0f} SAR\n"
            f"📊 Avg : {stats.avg_price:.0f} SAR\n"
            f"🎯 Median : {stats.median_price:.0f} SAR\n"
            f"📶 Volatility : {stats.volatility_pct:.0f}%\n"
            f"{trend_emoji} Trend : {stats.trend}{trend_detail}\n"
            f"🔮 Expected now : {stats.expected_price:.0f} SAR\n\n"
            f"🗓 Best day to book : {stats.best_booking_day or '—'}\n"
            f"😖 Worst day to book : {stats.worst_booking_day or '—'}\n"
            f"🛫 Best departure day : {stats.best_departure_day or '—'}\n\n"
            f"🔢 Based on {stats.count} check(s)"
        )

        if flight.last_price is not None:

            recommendation = analytics.recommendation(
                flight.last_price, stats, window_days
            )
            text += f"\n\n{recommendation}"

        cards.append((text, main_menu()))

    return cards