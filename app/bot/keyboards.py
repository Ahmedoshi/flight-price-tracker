from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup


def filters_keyboard(trip_type: str, cabin_class: str, max_stops: int | None):
    """Tap-to-cycle buttons for the Add/Check/Edit wizards' advanced
    filters step. Each button's label always shows the current value,
    so there's nothing to type or get wrong - just tap until it shows
    what you want, then Continue."""

    trip_labels = {
        "round-trip": "🔁 Round-trip",
        "one-way": "➡️ One-way",
        "multi-city": "🌍 Multi-city",
    }
    trip_label = trip_labels.get(trip_type, "🔁 Round-trip")
    cabin_label = f"💺 {cabin_class.replace('-', ' ').title()}"

    if max_stops is None:
        stops_label = "🛑 Stops: Any"
    elif max_stops == 0:
        stops_label = "🛑 Stops: Direct only"
    else:
        stops_label = f"🛑 Stops: Max {max_stops}"

    keyboard = [
        [InlineKeyboardButton(trip_label, callback_data="af_trip")],
        [InlineKeyboardButton(cabin_label, callback_data="af_cabin")],
        [InlineKeyboardButton(stops_label, callback_data="af_stops")],
        [InlineKeyboardButton("✅ Continue", callback_data="af_continue")],
    ]

    return InlineKeyboardMarkup(keyboard)


def main_menu():
    """Paired into a 2-column grid rather than one button per row -
    reads as a compact dashboard instead of a long vertical list of 7
    separate rows."""

    keyboard = [

        [
            InlineKeyboardButton("🔍 Check Flight", callback_data="menu_check"),
            InlineKeyboardButton("➕ Add Flight", callback_data="menu_add"),
        ],

        [
            InlineKeyboardButton("📋 My Flights", callback_data="menu_list"),
            InlineKeyboardButton("📈 Price History", callback_data="menu_history"),
        ],

        [
            InlineKeyboardButton("📊 Analytics", callback_data="menu_analytics"),
            InlineKeyboardButton("⚙️ Scheduler", callback_data="menu_scheduler"),
        ],

        [
            InlineKeyboardButton("ℹ️ Status", callback_data="menu_status"),
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
                "📉 Chart",
                callback_data=f"chart_{flight_id}",
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