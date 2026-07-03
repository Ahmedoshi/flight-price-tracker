from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup


def main_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "🔍 Check Flight",
                callback_data="menu_check",
            ),
            InlineKeyboardButton(
                "➕ Add Flight",
                callback_data="menu_add",
            ),
        ],

        [
            InlineKeyboardButton(
                "📋 My Flights",
                callback_data="menu_list",
            ),
            InlineKeyboardButton(
                "📈 History",
                callback_data="menu_history",
            ),
        ],

        [
            InlineKeyboardButton(
                "⏰ Run Now",
                callback_data="menu_run",
            ),
            InlineKeyboardButton(
                "ℹ️ Status",
                callback_data="menu_status",
            ),
        ],

        [
            InlineKeyboardButton(
                "🗑 Delete",
                callback_data="menu_delete",
            ),
        ],

    ]

    return InlineKeyboardMarkup(keyboard)