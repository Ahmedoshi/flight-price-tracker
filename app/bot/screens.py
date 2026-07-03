from app.bot.keyboards import main_menu
from app.services.tracking_service import TrackingService

tracking = TrackingService()


def home_screen():

    flights = tracking.list()

    return (
        (
            "✈️ Flight Price Tracker\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🟢 Bot Online\n"
            f"📍 Saved Flights : {len(flights)}\n"
            "⏰ Scheduler : Running\n\n"
            "Choose an option."
        ),
        main_menu(),
    )


def status_screen():

    flights = tracking.list()

    return (
        (
            "ℹ️ System Status\n\n"
            "🟢 Bot : Online\n"
            "🟢 Database : Ready\n"
            "🟢 Google Flights : Ready\n"
            "🟢 Scheduler : Running\n\n"
            f"📍 Saved Flights : {len(flights)}"
        ),
        main_menu(),
    )


def flights_screen():

    flights = tracking.list()

    if not flights:

        return (
            "📋 No saved flights.",
            main_menu(),
        )

    text = "📋 Saved Flights\n\n"

    for i, flight in enumerate(flights, start=1):

        text += (
            f"{i}. {flight.origin} ➜ {flight.destination}\n"
            f"📅 {flight.departure_date}\n"
            f"🔁 {flight.return_date}\n"
            f"🎯 {flight.max_price:.0f} SAR\n\n"
        )

    return (
        text,
        main_menu(),
    )


def history_screen():

    rows = tracking.history()

    if not rows:

        return (
            "📈 No price history.",
            main_menu(),
        )

    text = "📈 Price History\n\n"

    for airline, price, checked_at in rows:

        text += (
            f"{checked_at}\n"
            f"{airline}\n"
            f"{price:.0f} SAR\n\n"
        )

    return (
        text,
        main_menu(),
    )