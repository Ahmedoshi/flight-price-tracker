from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards import main_menu
from app.services.flight_service import FlightService
from app.services.tracking_service import TrackingService
from app.scheduler.scheduler import hourly_check

tracking = TrackingService()


async def button_click(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    # ==========================
    # Main Menu
    # ==========================

    if query.data == "menu_home":

        await query.edit_message_text(
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

    # ==========================
    # Status
    # ==========================

    elif query.data == "menu_status":

        flights = tracking.list()

        await query.edit_message_text(
            text=(
                "ℹ️ System Status\n\n"
                "🟢 Bot : Online\n"
                "🟢 Database : Ready\n"
                "🟢 Google Flights : Ready\n"
                f"📍 Saved Flights : {len(flights)}"
            ),
            reply_markup=main_menu(),
        )

    # ==========================
    # My Flights
    # ==========================

    elif query.data == "menu_list":

        flights = tracking.list()

        if not flights:

            await query.edit_message_text(
                "📋 No saved flights.",
                reply_markup=main_menu(),
            )

            return

        text = "📋 Saved Flights\n\n"

        for i, flight in enumerate(flights, start=1):

            text += (
                f"{i}. {flight.origin} ➜ {flight.destination}\n"
                f"📅 {flight.departure_date}\n"
                f"🔁 {flight.return_date}\n"
                f"🎯 {flight.max_price:.0f} SAR\n\n"
            )

        await query.edit_message_text(
            text=text,
            reply_markup=main_menu(),
        )

    # ==========================
    # Price History
    # ==========================

    elif query.data == "menu_history":

        rows = tracking.history()

        if not rows:

            await query.edit_message_text(
                "📈 No price history.",
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

        await query.edit_message_text(
            text=text,
            reply_markup=main_menu(),
        )

    # ==========================
    # Run Scheduler
    # ==========================

    elif query.data == "menu_run":

        await query.edit_message_text(
            "⏳ Running Scheduler..."
        )

        await hourly_check(context.application)

        await query.message.reply_text(
            "✅ Scheduler Finished.",
            reply_markup=main_menu(),
        )

    # ==========================
    # Check Flight
    # ==========================

    elif query.data == "menu_check":

        await query.edit_message_text(
            text=(
                "🔍 Flight Search\n\n"
                "For now use:\n\n"
                "/check RUH LIS 2026-09-01 2026-09-15"
            ),
            reply_markup=main_menu(),
        )

    # ==========================
    # Add Flight
    # ==========================

    elif query.data == "menu_add":

        await query.edit_message_text(
            text=(
                "➕ Add Flight\n\n"
                "For now use:\n\n"
                "/add RUH LIS 2026-09-01 2026-09-15 1800"
            ),
            reply_markup=main_menu(),
        )

    # ==========================
    # Delete
    # ==========================

    elif query.data == "menu_delete":

        await query.edit_message_text(
            text=(
                "🗑 Delete Flight\n\n"
                "For now use:\n\n"
                "/delete 1"
            ),
            reply_markup=main_menu(),
        )