from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup


def main_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "🔍 Check Flight",
                callback_data="menu_check",
            ),
        ],

        [
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
        ],

        [
            InlineKeyboardButton(
                "📈 Price History",
                callback_data="menu_history",
            ),
        ],

        [
            InlineKeyboardButton(
                "⚙️ Scheduler",
                callback_data="menu_scheduler",
            ),
        ],

        [
            InlineKeyboardButton(
                "ℹ️ Status",
                callback_data="menu_status",
            ),
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


def home_button():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏠 Home",
                    callback_data="menu_home",
                )
            ]
        ]
    )


def scheduler_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "▶️ Run Now",
                callback_data="scheduler_run",
            ),
        ],

        [
            InlineKeyboardButton(
                "⏸ Pause",
                callback_data="scheduler_pause",
            ),
        ],

        [
            InlineKeyboardButton(
                "▶ Resume",
                callback_data="scheduler_resume",
            ),
        ],

        [
            InlineKeyboardButton(
                "🕐 Every 1 Hour",
                callback_data="scheduler_1",
            ),
        ],

        [
            InlineKeyboardButton(
                "🕑 Every 2 Hours",
                callback_data="scheduler_2",
            ),
        ],

        [
            InlineKeyboardButton(
                "🕕 Every 6 Hours",
                callback_data="scheduler_6",
            ),
        ],

        [
            InlineKeyboardButton(
                "🏠 Home",
                callback_data="menu_home",
            ),
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


def flight_card(flight_id: int):

    keyboard = [

        [
            InlineKeyboardButton(
                "🔍 Check Now",
                callback_data=f"check_{flight_id}",
            ),
        ],

        [
            InlineKeyboardButton(
                "✏️ Edit",
                callback_data=f"edit_{flight_id}",
            ),
        ],

        [
            InlineKeyboardButton(
                "🗑 Delete",
                callback_data=f"delete_{flight_id}",
            ),
        ],

        [
            InlineKeyboardButton(
                "🏠 Home",
                callback_data="menu_home",
            ),
        ],

    ]

    return InlineKeyboardMarkup(keyboard)