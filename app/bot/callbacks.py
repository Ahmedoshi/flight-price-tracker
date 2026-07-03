from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards import main_menu


async def button_click(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    if query.data == "menu_check":

        await query.message.reply_text(
            "Use:\n"
            "/check RUH LIS 2026-09-01 2026-09-15"
        )

    elif query.data == "menu_add":

        await query.message.reply_text(
            "Use:\n"
            "/add RUH LIS 2026-09-01 2026-09-15 1800"
        )

    elif query.data == "menu_list":

        await query.message.reply_text(
            "Use:\n"
            "/list"
        )

    elif query.data == "menu_history":

        await query.message.reply_text(
            "Use:\n"
            "/history"
        )

    elif query.data == "menu_run":

        await query.message.reply_text(
            "Use:\n"
            "/run_scheduler"
        )

    elif query.data == "menu_status":

        await query.message.reply_text(
            "Use:\n"
            "/status"
        )

    elif query.data == "menu_delete":

        await query.message.reply_text(
            "Use:\n"
            "/delete 1"
        )

    else:

        await query.edit_message_reply_markup(
            reply_markup=main_menu()
        )