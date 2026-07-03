from telegram import Update
from telegram.ext import ContextTypes

from app.bot.screens import (
    home_screen,
    status_screen,
    flights_screen,
    history_screen,
)
from app.scheduler.scheduler import hourly_check


async def button_click(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    # =========================
    # HOME
    # =========================

    if query.data == "menu_home":

        text, keyboard = home_screen()

        await query.edit_message_text(
            text=text,
            reply_markup=keyboard,
        )

    # =========================
    # STATUS
    # =========================

    elif query.data == "menu_status":

        text, keyboard = status_screen()

        await query.edit_message_text(
            text=text,
            reply_markup=keyboard,
        )

    # =========================
    # MY FLIGHTS
    # =========================

    elif query.data == "menu_list":

        text, keyboard = flights_screen()

        await query.edit_message_text(
            text=text,
            reply_markup=keyboard,
        )

    # =========================
    # HISTORY
    # =========================

    elif query.data == "menu_history":

        text, keyboard = history_screen()

        await query.edit_message_text(
            text=text,
            reply_markup=keyboard,
        )

    # =========================
    # RUN SCHEDULER
    # =========================

    elif query.data == "menu_run":

        await query.edit_message_text(
            "⏳ Checking saved flights..."
        )

        await hourly_check(context.application)

        text, keyboard = home_screen()

        await query.message.reply_text(
            "✅ Check completed.",
        )

        await query.message.reply_text(
            text=text,
            reply_markup=keyboard,
        )

    # =========================
    # CHECK FLIGHT
    # =========================

    elif query.data == "menu_check":

        await query.edit_message_text(
            text=(
                "🔍 Flight Search\n\n"
                "🚧 Interactive search wizard\n"
                "coming in the next sprint."
            ),
            reply_markup=home_screen()[1],
        )

    # =========================
    # ADD FLIGHT
    # =========================

    elif query.data == "menu_add":

        await query.edit_message_text(
            text=(
                "➕ Add Flight\n\n"
                "🚧 Interactive add-flight wizard\n"
                "coming in the next sprint."
            ),
            reply_markup=home_screen()[1],
        )

    # =========================
    # DELETE
    # =========================

    elif query.data == "menu_delete":

        await query.edit_message_text(
            text=(
                "🗑 Delete Flight\n\n"
                "🚧 Select a saved flight to delete\n"
                "in the next sprint."
            ),
            reply_markup=home_screen()[1],
        )

    else:

        text, keyboard = home_screen()

        await query.edit_message_text(
            text=text,
            reply_markup=keyboard,
        )