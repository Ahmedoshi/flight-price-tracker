from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import ContextTypes

from app.bot.keyboards import main_menu
from app.bot.screens import (
    home_screen,
    status_screen,
    scheduler_screen,
    flights_screen,
    history_screen,
)
from app.scheduler.scheduler import (
    hourly_check,
    pause_scheduler,
    resume_scheduler,
    set_interval_hours,
)
from app.services.flight_service import FlightService
from app.services.tracking_service import TrackingService

tracking = TrackingService()


async def button_click(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    # ==========================
    # HOME
    # ==========================

    if query.data == "menu_home":

        text, keyboard = home_screen()

        await query.message.reply_text(
            text=text,
            reply_markup=keyboard,
        )

    # ==========================
    # STATUS
    # ==========================

    elif query.data == "menu_status":

        text, keyboard = status_screen()

        await query.message.reply_text(
            text=text,
            reply_markup=keyboard,
        )

    # ==========================
    # SCHEDULER
    # ==========================

    elif query.data == "menu_scheduler":

        text, keyboard = scheduler_screen()

        await query.message.reply_text(
            text=text,
            reply_markup=keyboard,
        )

    # ==========================
    # RUN SCHEDULER
    # ==========================

    elif query.data == "scheduler_run":

        await query.message.reply_text(
            "⏳ Checking all tracked flights..."
        )

        await hourly_check(context.application)

        await query.message.reply_text(
            "✅ Flight check completed."
        )

    # ==========================
    # PAUSE / RESUME SCHEDULER
    # ==========================

    elif query.data == "scheduler_pause":

        pause_scheduler()

        text, keyboard = scheduler_screen()

        await query.message.reply_text(
            text="⏸ Scheduler paused.\n\n" + text,
            reply_markup=keyboard,
        )

    elif query.data == "scheduler_resume":

        resume_scheduler()

        text, keyboard = scheduler_screen()

        await query.message.reply_text(
            text="▶ Scheduler resumed.\n\n" + text,
            reply_markup=keyboard,
        )

    # ==========================
    # SCHEDULER INTERVAL
    # ==========================

    elif query.data in ("scheduler_1", "scheduler_2", "scheduler_6"):

        hours = int(query.data.split("_")[1])

        set_interval_hours(hours)

        text, keyboard = scheduler_screen()

        await query.message.reply_text(
            text=f"🕑 Interval set to every {hours} hour(s).\n\n" + text,
            reply_markup=keyboard,
        )

    # ==========================
    # MY FLIGHTS
    # ==========================

    elif query.data == "menu_list":

        cards = flights_screen()

        if isinstance(cards, list):

            for text, keyboard in cards:

                await query.message.reply_text(
                    text=text,
                    reply_markup=keyboard,
                )

        else:

            text, keyboard = cards

            await query.message.reply_text(
                text=text,
                reply_markup=keyboard,
            )

    # ==========================
    # HISTORY
    # ==========================

    elif query.data == "menu_history":

        text, keyboard = history_screen()

        await query.message.reply_text(
            text=text,
            reply_markup=keyboard,
        )

    # ==========================
    # CHECK FLIGHT (interactive search wizard)
    # ==========================
    # menu_check / menu_add are handled by the ConversationHandlers in
    # app.bot.conversations, which are registered ahead of this generic
    # handler. They're listed in main.py's handler order, not here.

    # ==========================
    # CHECK NOW (re-check price for a saved flight)
    # ==========================

    elif query.data.startswith("check_"):

        flight_id = int(query.data.split("_")[1])
        flight = tracking.get_by_id(flight_id)

        if flight is None:

            await query.message.reply_text(
                "❌ That flight no longer exists.",
                reply_markup=main_menu(),
            )

        else:

            await query.message.reply_text("🔍 Searching...")

            service = FlightService()

            try:
                result = await service.cheapest_flight(
                    origin=flight.origin,
                    destination=flight.destination,
                    departure_date=flight.departure_date,
                    return_date=flight.return_date,
                    date_flex_days=flight.date_flex_days,
                )

            except ValueError as exc:

                await query.message.reply_text(
                    f"❌ {exc}",
                    reply_markup=main_menu(),
                )
                return

            if result is None:

                await query.message.reply_text(
                    "❌ No flights found.",
                    reply_markup=main_menu(),
                )

            else:

                text = (
                    "✈️ Cheapest Flight\n\n"
                    f"🏢 Provider : {result.provider}\n\n"
                    f"✈ Airline : {result.airline}\n\n"
                    f"💰 Price : {result.price:.0f} {result.currency}\n\n"
                    f"📍 Route : {result.origin} ➜ {result.destination}\n\n"
                    f"📅 Departure : {result.departure_date}\n\n"
                    f"🔁 Return : {result.return_date}"
                )

                if result.booking_url:
                    text += f"\n\n🔗 {result.booking_url}"

                await query.message.reply_text(
                    text=text,
                    reply_markup=main_menu(),
                )

    # ==========================
    # EDIT
    # ==========================

    elif query.data.startswith("edit_"):

        await query.message.reply_text(
            "✏️ Editing isn't available yet.\n\n"
            "For now, delete this flight and add it again with the new details."
        )

    # ==========================
    # DELETE (with confirmation)
    # ==========================

    elif query.data.startswith("delete_"):

        flight_id = int(query.data.split("_")[1])
        flight = tracking.get_by_id(flight_id)

        if flight is None:

            await query.message.reply_text(
                "❌ That flight no longer exists.",
                reply_markup=main_menu(),
            )

        else:

            confirm_keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ Yes, delete it",
                            callback_data=f"confirm_delete_{flight_id}",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "❌ Cancel",
                            callback_data="menu_list",
                        ),
                    ],
                ]
            )

            await query.message.reply_text(
                text=(
                    "🗑 Delete this flight?\n\n"
                    f"{flight.origin} ➜ {flight.destination}\n"
                    f"📅 {flight.departure_date} / 🔁 {flight.return_date}"
                ),
                reply_markup=confirm_keyboard,
            )

    elif query.data.startswith("confirm_delete_"):

        flight_id = int(query.data.split("_")[2])

        tracking.delete(flight_id)

        await query.message.reply_text(
            "✅ Flight deleted.",
            reply_markup=main_menu(),
        )

    # ==========================
    # UNKNOWN
    # ==========================

    else:

        text, keyboard = home_screen()

        await query.message.reply_text(
            text=text,
            reply_markup=keyboard,
        )