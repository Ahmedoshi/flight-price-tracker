from app.bot.keyboards import (
    main_menu,
    scheduler_menu,
    flight_card,
)
from app.services.tracking_service import TrackingService

tracking = TrackingService()


def home_screen():

    flights = tracking.list()

    text = (
        "✈️ Flight Price Tracker\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👋 Welcome\n\n"
        "🟢 Bot Online\n"
        f"📍 Flights Tracked : {len(flights)}\n"
        "⏰ Scheduler : Every 2 Hours\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Choose an action:"
    )

    return text, main_menu()


def status_screen():

    flights = tracking.list()

    text = (
        "ℹ️ System Status\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🟢 Bot : Online\n"
        "🟢 Database : Connected\n"
        "🟢 Google Flights : Ready\n"
        "🟢 Scheduler : Running\n\n"
        f"📍 Saved Flights : {len(flights)}"
    )

    return text, main_menu()


def scheduler_screen():

    text = (
        "⚙️ Scheduler\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Status\n"
        "🟢 Running\n\n"
        "Current Interval\n"
        "🕑 Every 2 Hours"
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

    for index, flight in enumerate(flights, start=1):

        text = (
            "✈️ Flight\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{flight.origin} ➜ {flight.destination}\n\n"
            f"📅 Departure : {flight.departure_date}\n"
            f"↩ Return : {flight.return_date}\n\n"
            f"🎯 Target : {flight.max_price:.0f} SAR"
        )

        cards.append(
            (
                text,
                flight_card(index),
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