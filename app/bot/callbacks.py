from telegram import Update
from telegram.ext import ContextTypes

from app.bot.screens import (
    home_screen,
    status_screen,
    scheduler_screen,
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
    # CHECK FLIGHT
    # ==========================

    elif query.data == "menu_check":

        await query.message.reply_text(
            "🔍 Flight Search\n\n"
            "🚧 Interactive search wizard\n"
            "coming in the next sprint."
        )

    # ==========================
    # ADD FLIGHT
    # ==========================

    elif query.data == "menu_add":

        await query.message.reply_text(
            "➕ Add Flight\n\n"
            "🚧 Interactive add-flight wizard\n"
            "coming in the next sprint."
        )

    # ==========================
    # CHECK NOW
    # ==========================

    elif query.data.startswith("check_"):

        await query.message.reply_text(
            "🚧 Check Now will be available in the next sprint."
        )

    # ==========================
    # EDIT
    # ==========================

    elif query.data.startswith("edit_"):

        await query.message.reply_text(
            "🚧 Edit Flight will be available in the next sprint."
        )

    # ==========================
    # DELETE
    # ==========================

    elif query.data.startswith("delete_"):

        await query.message.reply_text(
            "🚧 Delete Flight will be available in the next sprint."
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