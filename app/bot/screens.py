from app.bot.keyboards import (
    main_menu,
    scheduler_menu,
    flight_card,
)
from app.config.settings import settings
from app.scheduler.scheduler import get_status
from app.services.tracking_service import TrackingService

tracking = TrackingService()


def _kiwi_enabled() -> bool:

    return bool(settings.kiwi_api_key)


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

    text = (
        "ℹ️ System Status\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🟢 Bot : Online\n"
        "🟢 Database : Connected\n"
        "🟢 Google Flights : Ready\n"
        f"{'🟢 Kiwi.com : Ready' if _kiwi_enabled() else '⚪ Kiwi.com : Not configured'}\n"
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

        flex_text = (
            f" (+/-{flight.date_flex_days}d)" if flight.date_flex_days else ""
        )

        text = (
            f"✈️ Flight #{position}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{flight.origin} ➜ {flight.destination}\n\n"
            f"📅 Departure : {flight.departure_date}\n"
            f"↩ Return : {flight.return_date}{flex_text}\n\n"
            f"🎯 Target : {flight.max_price:.0f} SAR"
        )

        cards.append(
            (
                text,
                flight_card(flight.id),
            )
        )

    return cards


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