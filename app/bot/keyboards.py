from telegram import Update

from telegram.ext import ContextTypes

from app.bot.keyboards import main_menu
from app.services.flight_service import FlightService
from app.services.tracking_service import TrackingService
from app.scheduler.scheduler import hourly_check

tracking = TrackingService()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        text=(
            "✈️ Flight Price Tracker\n\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "🟢 Bot Online\n"
            "📍 Ready to Track Flights\n"
            "⏰ Scheduler Ready\n\n"
            "Choose an option below."
        ),
        reply_markup=main_menu(),
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    flights = tracking.list()

    await update.message.reply_text(
        text=(
            "ℹ️ System Status\n\n"
            f"🟢 Bot: Online\n"
            f"🟢 Database: Ready\n"
            f"🟢 Google Flights: Ready\n"
            f"📍 Saved Flights: {len(flights)}"
        ),
        reply_markup=main_menu(),
    )


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) != 4:

        await update.message.reply_text(
            "Usage:\n"
            "/check ORIGIN DESTINATION DEPARTURE RETURN\n\n"
            "Example:\n"
            "/check RUH LIS 2026-09-01 2026-09-15",
            reply_markup=main_menu(),
        )
        return

    origin = context.args[0].upper()
    destination = context.args[1].upper()
    departure_date = context.args[2]
    return_date = context.args[3]

    await update.message.reply_text("🔍 Searching Google Flights...")

    service = FlightService()

    result = await service.cheapest_flight(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
    )

    if result is None:

        await update.message.reply_text(
            "❌ No flights found.",
            reply_markup=main_menu(),
        )
        return

    await update.message.reply_text(
        f"""✈️ Cheapest Flight

🏢 Provider : {result.provider}

✈ Airline : {result.airline}

💰 Price : {result.price:.0f} {result.currency}

📍 Route : {result.origin} ➜ {result.destination}

📅 Departure : {result.departure_date}

🔁 Return : {result.return_date}
""",
        reply_markup=main_menu(),
    )


async def check_now(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Press 🔍 Check Flight from the menu.",
        reply_markup=main_menu(),
    )


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) != 5:

        await update.message.reply_text(
            "Usage:\n"
            "/add ORIGIN DESTINATION DEPARTURE RETURN TARGET\n\n"
            "Example:\n"
            "/add RUH LIS 2026-09-01 2026-09-15 1800",
            reply_markup=main_menu(),
        )
        return

    origin = context.args[0].upper()
    destination = context.args[1].upper()
    departure_date = context.args[2]
    return_date = context.args[3]

    try:
        max_price = float(context.args[4])

    except ValueError:

        await update.message.reply_text(
            "❌ Invalid target price.",
            reply_markup=main_menu(),
        )
        return

    tracking.add(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        max_price=max_price,
    )

    await update.message.reply_text(
        f"""✅ Flight Added

📍 {origin} ➜ {destination}

📅 {departure_date}

🔁 {return_date}

🎯 Target : {max_price:.0f} SAR
""",
        reply_markup=main_menu(),
    )


async def list(update: Update, context: ContextTypes.DEFAULT_TYPE):

    flights = tracking.list()

    if not flights:

        await update.message.reply_text(
            "No saved flights.",
            reply_markup=main_menu(),
        )
        return

    text = "📋 Saved Flights\n\n"

    for i, f in enumerate(flights, start=1):

        text += (
            f"{i}. {f.origin} ➜ {f.destination}\n"
            f"📅 {f.departure_date}\n"
            f"🔁 {f.return_date}\n"
            f"🎯 {f.max_price:.0f} SAR\n\n"
        )

    await update.message.reply_text(
        text,
        reply_markup=main_menu(),
    )


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) != 1:

        await update.message.reply_text(
            "Usage:\n/delete 1",
            reply_markup=main_menu(),
        )
        return

    try:
        index = int(context.args[0])

    except ValueError:

        await update.message.reply_text(
            "Invalid number.",
            reply_markup=main_menu(),
        )
        return

    tracking.delete(index)

    await update.message.reply_text(
        f"✅ Flight #{index} deleted.",
        reply_markup=main_menu(),
    )


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rows = tracking.history()

    if not rows:

        await update.message.reply_text(
            "No price history.",
            reply_markup=main_menu(),
        )
        return

    text = "📈 Price History\n\n"

    for airline, price, checked_at in rows:

        text += (
            f"{checked_at}\n"
            f"{airline}\n"
            f"{price:.0f} SAR\n\n"
        )

    await update.message.reply_text(
        text,
        reply_markup=main_menu(),
    )


async def run_scheduler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("⏳ Running Scheduler...")

    await hourly_check(context.application)

    await update.message.reply_text(
        "✅ Scheduler Finished.",
        reply_markup=main_menu(),
    )