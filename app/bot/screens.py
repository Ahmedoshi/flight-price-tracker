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
from app.services.chart_service import ascii_sparkline
from app.services.tracking_service import TrackingService
from app.utils.dates import format_checked_at
from app.utils.text import esc

tracking = TrackingService()
analytics = AnalyticsService()

# A lighter separator than a full-width solid block - bold section
# headers now carry the visual hierarchy, so the divider only needs to
# be a subtle break between sections rather than an equal-weight bar.
DIVIDER = "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈"


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
            lines.append(f"⚪ {name} : <i>Not configured</i>")
            continue

        stats = provider_health.get_stats(name)

        if stats["offline"]:

            retry_mins = max(
                0,
                int((stats["disabled_until"] - datetime.now(timezone.utc)).total_seconds() // 60),
            )
            lines.append(f"🔴 {name} : Offline <i>(retrying in ~{retry_mins}m)</i>")
            continue

        if stats["total_checks"] == 0:
            lines.append(f"🟢 {name} : Ready")
            continue

        if stats["avg_response_seconds"] is None:
            # Has failures but hasn't tripped the auto-disable
            # threshold (or hasn't succeeded even once) yet.
            lines.append(
                f"🟡 {name} : Struggling — <b>{stats['success_rate_pct']:.0f}%</b> success "
                f"<i>({stats['total_checks']} checks, {stats['consecutive_failures']} in a row)</i>"
            )
            continue

        lines.append(
            f"🟢 {name} : Ready — avg {stats['avg_response_seconds']:.1f}s, "
            f"<b>{stats['success_rate_pct']:.0f}%</b> success <i>({stats['total_checks']} checks)</i>"
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
        "<b>✈️ Flight Price Tracker</b>\n\n"
        f"{DIVIDER}\n\n"
        "👋 Welcome back\n\n"
        "🟢 Bot Online\n"
        f"📍 Flights Tracked : <b>{len(flights)}</b>\n"
        f"⏰ Scheduler : <b>{schedule_text}</b>\n\n"
        f"{DIVIDER}\n\n"
        "<i>Choose an action:</i>"
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
    whatsapp_label = "Ready" if whatsapp_ready else "<i>Not configured</i>"

    text = (
        "<b>ℹ️ System Status</b>\n\n"
        f"{DIVIDER}\n\n"
        "🟢 Bot : Online\n"
        "🟢 Database : Connected\n"
        f"{_provider_status_lines()}\n"
        f"{whatsapp_icon} WhatsApp Alerts : {whatsapp_label}\n"
        f"{'🟢' if is_running else '⏸'} Scheduler : <b>{'Running' if is_running else 'Paused'}</b>\n\n"
        f"📍 Saved Flights : <b>{len(flights)}</b>"
    )

    return text, main_menu()


def scheduler_screen():

    is_running, interval_hours = get_status()

    text = (
        "<b>⚙️ Scheduler</b>\n\n"
        f"{DIVIDER}\n\n"
        "Status\n"
        f"{'🟢 <b>Running</b>' if is_running else '⏸ <b>Paused</b>'}\n\n"
        "Current Interval\n"
        f"🕑 Every <b>{interval_hours}</b> Hour{'s' if interval_hours != 1 else ''}"
    )

    return text, scheduler_menu()


def flights_screen():

    flights = tracking.list()

    if not flights:

        return [
            (
                "<b>📋 My Flights</b>\n\n<i>No saved flights.</i>",
                main_menu(),
            )
        ]

    cards = []

    for position, flight in enumerate(flights, start=1):

        if flight.trip_type == "multi-city" and flight.legs:

            legs_text = "\n".join(
                f"  {i}. {esc(leg['origin'])} ➜ {esc(leg['destination'])} ({esc(leg['date'])})"
                for i, leg in enumerate(flight.legs, start=1)
            )

            filters_line = _filters_summary(flight)

            text = (
                f"<b>✈️ Flight #{position}</b> — 🌍 Multi-city\n\n"
                f"{DIVIDER}\n\n"
                f"{legs_text}\n\n"
                f"🎯 Target : <b>{flight.max_price:.0f} SAR</b>"
                f"{filters_line}"
            )

            cards.append((text, flight_card(flight.id)))
            continue

        flex_text = (
            f" <i>(+/-{flight.date_flex_days}d)</i>" if flight.date_flex_days else ""
        )

        return_line = (
            f"↩ Return : {esc(flight.return_date)}{flex_text}\n\n"
            if flight.trip_type == "round-trip"
            else "↩ <i>One-way</i>\n\n"
        )

        filters_line = _filters_summary(flight)

        text = (
            f"<b>✈️ Flight #{position}</b>\n\n"
            f"{DIVIDER}\n\n"
            f"<b>{esc(flight.origin)} ➜ {esc(flight.destination)}</b>\n\n"
            f"📅 Departure : {esc(flight.departure_date)}\n"
            f"{return_line}"
            f"🎯 Target : <b>{flight.max_price:.0f} SAR</b>"
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

    return "\n\n🎛 <i>" + ", ".join(parts) + "</i>"


def history_screen():

    rows = tracking.history()

    if not rows:

        return (
            "<b>📈 Price History</b>\n\n<i>No price history.</i>",
            main_menu(),
        )

    text = "<b>📈 Price History</b>\n\n"

    for airline, price, checked_at in rows[:10]:

        text += (
            f"{DIVIDER}\n"
            f"<i>{esc(format_checked_at(checked_at))}</i>\n\n"
            f"✈ {esc(airline)}\n"
            f"💰 <b>{price:.0f} SAR</b>\n\n"
        )

    return text, main_menu()


def analytics_screen():

    flights = tracking.list()

    if not flights:

        return [
            (
                "<b>📊 Analytics</b>\n\n<i>No saved flights yet.</i>",
                main_menu(),
            )
        ]

    window_days = settings.analytics_window_days
    cards = []

    for position, flight in enumerate(flights, start=1):

        stats = analytics.compute_stats(flight, since_days=window_days)

        if stats is None:

            text = (
                f"<b>📊 Flight #{position}</b>\n\n"
                f"{esc(flight.origin)} ➜ {esc(flight.destination)}\n\n"
                "<i>No price history yet — run a check first.</i>"
            )
            cards.append((text, main_menu()))
            continue

        trend_emoji = TREND_EMOJI.get(stats.trend, "➡️")
        trend_detail = f" ({abs(stats.trend_pct):.0f}%)" if stats.trend != "flat" else ""

        rows = tracking.route_history(flight, since_days=window_days)
        prices = [row[0] for row in rows]
        spark = ascii_sparkline(prices)
        spark_line = f"{spark}\n\n" if spark else ""

        text = (
            f"<b>📊 Flight #{position}</b> — <i>last {window_days}d</i>\n\n"
            f"{DIVIDER}\n\n"
            f"<b>{esc(flight.origin)} ➜ {esc(flight.destination)}</b>\n\n"
            f"{spark_line}"
            f"📉 Min : {stats.min_price:.0f} SAR\n"
            f"📈 Max : {stats.max_price:.0f} SAR\n"
            f"📊 Avg : {stats.avg_price:.0f} SAR\n"
            f"🎯 Median : {stats.median_price:.0f} SAR\n"
            f"📶 Volatility : {stats.volatility_pct:.0f}%\n"
            f"{trend_emoji} Trend : {stats.trend}{trend_detail}\n"
            f"🔮 Expected now : <b>{stats.expected_price:.0f} SAR</b>\n\n"
            f"🗓 Best day to book : {esc(stats.best_booking_day) if stats.best_booking_day else '—'}\n"
            f"😖 Worst day to book : {esc(stats.worst_booking_day) if stats.worst_booking_day else '—'}\n"
            f"🛫 Best departure day : {esc(stats.best_departure_day) if stats.best_departure_day else '—'}\n\n"
            f"<i>Based on {stats.count} check(s)</i>"
        )

        if flight.last_price is not None:

            recommendation = analytics.recommendation(
                flight.last_price, stats, window_days
            )
            text += f"\n\n<b>{recommendation}</b>"

        cards.append((text, main_menu()))

    return cards
