from telegram import Update
from telegram.ext import ContextTypes

from app.services.flight_service import FlightService
from app.services.tracking_service import TrackingService
from app.scheduler.scheduler import hourly_check

tracking = TrackingService()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "✈️ Flight Price Tracker\n\n"
        "Commands:\n"
        "/check_now\n"
        "/add\n"
        "/list\n"
        "/delete\n"
        "/history\n"
        "/run_scheduler"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "✅ System Status\n\n"
        "Bot: Online\n"
        "Google Flights: Ready\n"
        "Database: Ready"
    )


async def check_now(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("🔍 Checking Google Flights...")

    service = FlightService()

    result = await service.cheapest_flight(
        origin="RUH",
        destination="LIS",
        departure_date="2026-09-01",
        return_date="2026-09-15",
    )

    if result is None:
        await update.message.reply_text("❌ No flights found.")
        return

    await update.message.reply_text(
        f"""✈️ Cheapest Flight

Provider: {result.provider}
Airline: {result.airline}
Price: {result.price:.0f} {result.currency}
Route: {result.origin} ➜ {result.destination}
Departure: {result.departure_date}
Return: {result.return_date}
"""
    )


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):

    tracking.add(
        origin="RUH",
        destination="LIS",
        departure_date="2026-09-01",
        return_date="2026-09-15",
        max_price=1800,
    )

    await update.message.reply_text("✅ Flight saved.")


async def list(update: Update, context: ContextTypes.DEFAULT_TYPE):

    flights = tracking.list()

    if not flights:
        await update.message.reply_text("No saved flights.")
        return

    text = ""

    for i, f in enumerate(flights, start=1):

        text += (
            f"{i}. "
            f"{f.origin} ➜ {f.destination} | "
            f"{f.departure_date} | "
            f"Target {f.max_price:.0f} SAR\n"
        )

    await update.message.reply_text(text)


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):

    tracking.delete(1)

    await update.message.reply_text("✅ First flight deleted.")


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rows = tracking.history()

    if not rows:
        await update.message.reply_text("No price history.")
        return

    text = "📈 Price History\n\n"

    for airline, price, checked_at in rows:

        text += (
            f"{checked_at}\n"
            f"{airline}\n"
            f"{price:.0f} SAR\n\n"
        )

    await update.message.reply_text(text)


async def run_scheduler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("⏳ Running scheduler...")

    await hourly_check(context.application)

    await update.message.reply_text("✅ Scheduler finished.")