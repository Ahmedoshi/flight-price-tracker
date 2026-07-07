from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.bot.keyboards import filters_keyboard, main_menu
from app.services.analytics_service import AnalyticsService
from app.services.flight_service import FlightService
from app.services.tracking_service import TrackingService
from app.utils.airports import parse_codes, validate_codes
from app.utils.dates import is_valid_date
from app.utils.flight_filters import DEFAULT_FILTERS, format_filters
from app.utils.search_scope import validate_search_scope
from app.utils.text import esc

tracking = TrackingService()

KEEP = "-"

FILTERS_SCREEN_TEXT = (
    "🎛 Advanced Filters\n\n"
    "Tap a button to cycle its value, then Continue."
)

CABIN_ORDER = ["economy", "premium-economy", "business", "first"]
STOPS_ORDER = [None, 0, 1, 2]
TRIP_ORDER = ["round-trip", "one-way", "multi-city"]

MULTI_CITY_MIN_LEGS = 2
MULTI_CITY_MAX_LEGS = 5


def _flex_prompt() -> str:

    return (
        "How many days flexible (0-5)? 0 = exact dates only.\n\n"
        "e.g. \"3\" checks +/-3 days around your dates too."
    )


async def _resume_or_restart(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str, entry_label: str):
    """Guard against a lost mid-wizard state - e.g. the bot process
    restarted between steps and, for whatever reason, persistence
    didn't have this in-flight conversation saved yet. Without this,
    a stale button press would silently fall through to the generic
    menu handler and look like the bot "hung". Returns the wizard's
    data dict, or None after telling the user what happened.
    """

    data = context.user_data.get(key)

    if data is None:

        message = update.callback_query.message if update.callback_query else update.message

        await message.reply_text(
            "⚠️ This wizard's progress was lost (the bot likely restarted "
            f"mid-conversation). Please start again with {entry_label}.",
            reply_markup=main_menu(),
        )

    return data


def _apply_filter_toggle(callback_data: str, data: dict):

    if callback_data == "af_trip":

        idx = TRIP_ORDER.index(data["trip_type"])
        data["trip_type"] = TRIP_ORDER[(idx + 1) % len(TRIP_ORDER)]

    elif callback_data == "af_cabin":

        idx = CABIN_ORDER.index(data["cabin_class"])
        data["cabin_class"] = CABIN_ORDER[(idx + 1) % len(CABIN_ORDER)]

    elif callback_data == "af_stops":

        idx = STOPS_ORDER.index(data["max_stops"])
        data["max_stops"] = STOPS_ORDER[(idx + 1) % len(STOPS_ORDER)]


# ==============================
# ADD FLIGHT WIZARD
# ==============================

(
    ADD_ORIGIN,
    ADD_DESTINATION,
    ADD_FILTERS,
    ADD_DEPARTURE,
    ADD_RETURN,
    ADD_FLEX,
    ADD_TARGET,
    ADD_MULTI_COUNT,
    ADD_MULTI_LEG_DATE,
    ADD_MULTI_LEG,
) = range(10)


async def add_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    context.user_data["add"] = dict(DEFAULT_FILTERS)

    await query.message.reply_text(
        "➕ Add Flight\n\n"
        "Send the ORIGIN airport code(s), comma-separated\n"
        "(e.g. RUH or RUH,DMM).\n\n"
        "Send /cancel to stop."
    )

    return ADD_ORIGIN


async def add_origin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    codes = parse_codes(update.message.text)
    error = validate_codes(codes)

    if error or not codes:

        await update.message.reply_text(
            f"❌ {esc(error) if error else 'Send at least one airport code.'}"
        )
        return ADD_ORIGIN

    context.user_data["add"]["origin"] = codes

    await update.message.reply_text(
        "Send the DESTINATION airport code(s), comma-separated\n"
        "(e.g. LIS or LIS,OPO)."
    )

    return ADD_DESTINATION


async def add_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):

    codes = parse_codes(update.message.text)
    error = validate_codes(codes)

    if error or not codes:

        await update.message.reply_text(
            f"❌ {esc(error) if error else 'Send at least one airport code.'}"
        )
        return ADD_DESTINATION

    context.user_data["add"]["destination"] = codes

    data = context.user_data["add"]

    await update.message.reply_text(
        FILTERS_SCREEN_TEXT,
        reply_markup=filters_keyboard(
            data["trip_type"], data["cabin_class"], data["max_stops"]
        ),
    )

    return ADD_FILTERS


async def add_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = await _resume_or_restart(update, context, "add", "➕ Add Flight")

    if data is None:
        return ConversationHandler.END

    if query.data == "af_continue":

        if data["trip_type"] == "multi-city":

            await query.message.reply_text(
                "🌍 Multi-city trip\n\n"
                f"How many flights/cities in total, including "
                f"{data['origin'][0]} → {data['destination'][0]}? "
                f"({MULTI_CITY_MIN_LEGS}-{MULTI_CITY_MAX_LEGS})"
            )
            return ADD_MULTI_COUNT

        await query.message.reply_text("Send the DEPARTURE date (YYYY-MM-DD).")
        return ADD_DEPARTURE

    _apply_filter_toggle(query.data, data)

    await query.edit_message_reply_markup(
        reply_markup=filters_keyboard(
            data["trip_type"], data["cabin_class"], data["max_stops"]
        )
    )

    return ADD_FILTERS


async def add_multi_count(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    try:
        total = int(text)

    except ValueError:

        await update.message.reply_text(
            f"❌ Send a whole number between {MULTI_CITY_MIN_LEGS} and {MULTI_CITY_MAX_LEGS}."
        )
        return ADD_MULTI_COUNT

    if not (MULTI_CITY_MIN_LEGS <= total <= MULTI_CITY_MAX_LEGS):

        await update.message.reply_text(
            f"❌ Must be between {MULTI_CITY_MIN_LEGS} and {MULTI_CITY_MAX_LEGS}."
        )
        return ADD_MULTI_COUNT

    data = context.user_data["add"]
    data["multi_total"] = total
    data["legs"] = [
        {"origin": data["origin"][0], "destination": data["destination"][0]}
    ]

    await update.message.reply_text(
        f"Leg 1 of {total}: {data['legs'][0]['origin']} → {data['legs'][0]['destination']}\n\n"
        "Send its date (YYYY-MM-DD)."
    )

    return ADD_MULTI_LEG_DATE


async def add_multi_leg_date(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    if not is_valid_date(text):

        await update.message.reply_text(
            "❌ Please send a valid date as YYYY-MM-DD."
        )
        return ADD_MULTI_LEG_DATE

    data = context.user_data["add"]
    data["legs"][0]["date"] = text

    await update.message.reply_text(
        f"Leg 2 of {data['multi_total']}: send ORIGIN DESTINATION DATE\n"
        "(e.g. LIS CDG 2026-09-05)."
    )

    return ADD_MULTI_LEG


async def add_multi_leg(update: Update, context: ContextTypes.DEFAULT_TYPE):

    parts = update.message.text.strip().split()
    data = context.user_data["add"]

    if len(parts) != 3:

        await update.message.reply_text(
            "❌ Send exactly 3 values: ORIGIN DESTINATION DATE "
            "(e.g. LIS CDG 2026-09-05)."
        )
        return ADD_MULTI_LEG

    origin, destination, date_text = (p.upper() if i < 2 else p for i, p in enumerate(parts))

    code_error = validate_codes([origin]) or validate_codes([destination])

    if code_error:
        await update.message.reply_text(f"❌ {esc(code_error)}")
        return ADD_MULTI_LEG

    if not is_valid_date(date_text):
        await update.message.reply_text("❌ Please send a valid date as YYYY-MM-DD.")
        return ADD_MULTI_LEG

    data["legs"].append({"origin": origin, "destination": destination, "date": date_text})

    if len(data["legs"]) < data["multi_total"]:

        next_n = len(data["legs"]) + 1

        await update.message.reply_text(
            f"Leg {next_n} of {data['multi_total']}: send ORIGIN DESTINATION DATE."
        )
        return ADD_MULTI_LEG

    await update.message.reply_text(
        "Send your TARGET price in SAR (numbers only, e.g. 1800)."
    )

    return ADD_TARGET


async def add_departure(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    if not is_valid_date(text):

        await update.message.reply_text(
            "❌ Please send a valid date as YYYY-MM-DD."
        )
        return ADD_DEPARTURE

    data = context.user_data["add"]
    data["departure_date"] = text

    if data["trip_type"] == "one-way":

        data["return_date"] = ""
        await update.message.reply_text(_flex_prompt())
        return ADD_FLEX

    await update.message.reply_text("Send the RETURN date (YYYY-MM-DD).")

    return ADD_RETURN


async def add_return(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    if not is_valid_date(text):

        await update.message.reply_text(
            "❌ Please send a valid date as YYYY-MM-DD."
        )
        return ADD_RETURN

    context.user_data["add"]["return_date"] = text

    await update.message.reply_text(_flex_prompt())

    return ADD_FLEX


async def add_flex(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    try:
        flex_days = int(text)

    except ValueError:

        await update.message.reply_text("❌ Send a whole number, e.g. 0 or 3.")
        return ADD_FLEX

    data = context.user_data["add"]

    error = validate_search_scope(data["origin"], data["destination"], flex_days)

    if error:

        await update.message.reply_text(f"❌ {esc(error)}")
        return ADD_FLEX

    data["date_flex_days"] = flex_days

    await update.message.reply_text(
        "Send your TARGET price in SAR (numbers only, e.g. 1800)."
    )

    return ADD_TARGET


async def add_target(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        max_price = float(update.message.text.strip())

    except ValueError:

        await update.message.reply_text("❌ Target price must be numeric.")
        return ADD_TARGET

    data = context.user_data.pop("add")

    if data["trip_type"] == "multi-city":

        legs = data["legs"]

        tracking.add(
            origin=legs[0]["origin"],
            destination=legs[-1]["destination"],
            departure_date=legs[0]["date"],
            return_date="",
            max_price=max_price,
            date_flex_days=0,
            trip_type="multi-city",
            cabin_class=data["cabin_class"],
            max_stops=data["max_stops"],
            legs=legs,
        )

        legs_text = "\n".join(
            f"{i}. {esc(leg['origin'])} ➜ {esc(leg['destination'])} on {esc(leg['date'])}"
            for i, leg in enumerate(legs, start=1)
        )

        await update.message.reply_text(
            text=(
                "✅ <b>Flight Added</b> <i>(multi-city)</i>\n\n"
                f"{legs_text}\n\n"
                f"🎯 Target : <b>{max_price:.0f} SAR</b>"
            ),
            reply_markup=main_menu(),
        )

        return ConversationHandler.END

    tracking.add(
        origin=",".join(data["origin"]),
        destination=",".join(data["destination"]),
        departure_date=data["departure_date"],
        return_date=data["return_date"],
        max_price=max_price,
        date_flex_days=data["date_flex_days"],
        trip_type=data["trip_type"],
        cabin_class=data["cabin_class"],
        max_stops=data["max_stops"],
    )

    flex_text = (
        f"\n🎚 Flex : +/-{data['date_flex_days']} day(s)"
        if data["date_flex_days"]
        else ""
    )

    filters_text = format_filters(data["trip_type"], data["cabin_class"], data["max_stops"])
    filters_line = f"\n🎛 {filters_text}" if filters_text else ""

    return_line = (
        f"🔁 Return : {esc(data['return_date'])}\n"
        if data["trip_type"] == "round-trip"
        else "↩ One-way\n"
    )

    await update.message.reply_text(
        text=(
            "✅ <b>Flight Added</b>\n\n"
            f"📍 <b>{esc(','.join(data['origin']))} ➜ {esc(','.join(data['destination']))}</b>\n\n"
            f"📅 Departure : {esc(data['departure_date'])}\n"
            f"{return_line}"
            f"{flex_text}{filters_line}\n\n"
            f"🎯 Target : <b>{max_price:.0f} SAR</b>"
        ),
        reply_markup=main_menu(),
    )

    return ConversationHandler.END


# ==============================
# CHECK FLIGHT WIZARD
# ==============================

(
    CHECK_ORIGIN,
    CHECK_DESTINATION,
    CHECK_FILTERS,
    CHECK_DEPARTURE,
    CHECK_RETURN,
    CHECK_FLEX,
    CHECK_MULTI_COUNT,
    CHECK_MULTI_LEG_DATE,
    CHECK_MULTI_LEG,
) = range(10, 19)


async def check_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    context.user_data["check"] = dict(DEFAULT_FILTERS)

    await query.message.reply_text(
        "🔍 Check Flight\n\n"
        "Send the ORIGIN airport code(s), comma-separated\n"
        "(e.g. RUH or RUH,DMM).\n\n"
        "Send /cancel to stop."
    )

    return CHECK_ORIGIN


async def check_origin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    codes = parse_codes(update.message.text)
    error = validate_codes(codes)

    if error or not codes:

        await update.message.reply_text(
            f"❌ {esc(error) if error else 'Send at least one airport code.'}"
        )
        return CHECK_ORIGIN

    context.user_data["check"]["origin"] = codes

    await update.message.reply_text(
        "Send the DESTINATION airport code(s), comma-separated\n"
        "(e.g. LIS or LIS,OPO)."
    )

    return CHECK_DESTINATION


async def check_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):

    codes = parse_codes(update.message.text)
    error = validate_codes(codes)

    if error or not codes:

        await update.message.reply_text(
            f"❌ {esc(error) if error else 'Send at least one airport code.'}"
        )
        return CHECK_DESTINATION

    context.user_data["check"]["destination"] = codes

    data = context.user_data["check"]

    await update.message.reply_text(
        FILTERS_SCREEN_TEXT,
        reply_markup=filters_keyboard(
            data["trip_type"], data["cabin_class"], data["max_stops"]
        ),
    )

    return CHECK_FILTERS


async def check_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = await _resume_or_restart(update, context, "check", "🔍 Check Flight")

    if data is None:
        return ConversationHandler.END

    if query.data == "af_continue":

        if data["trip_type"] == "multi-city":

            await query.message.reply_text(
                "🌍 Multi-city trip\n\n"
                f"How many flights/cities in total, including "
                f"{data['origin'][0]} → {data['destination'][0]}? "
                f"({MULTI_CITY_MIN_LEGS}-{MULTI_CITY_MAX_LEGS})"
            )
            return CHECK_MULTI_COUNT

        await query.message.reply_text("Send the DEPARTURE date (YYYY-MM-DD).")
        return CHECK_DEPARTURE

    _apply_filter_toggle(query.data, data)

    await query.edit_message_reply_markup(
        reply_markup=filters_keyboard(
            data["trip_type"], data["cabin_class"], data["max_stops"]
        )
    )

    return CHECK_FILTERS


async def check_multi_count(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    try:
        total = int(text)

    except ValueError:

        await update.message.reply_text(
            f"❌ Send a whole number between {MULTI_CITY_MIN_LEGS} and {MULTI_CITY_MAX_LEGS}."
        )
        return CHECK_MULTI_COUNT

    if not (MULTI_CITY_MIN_LEGS <= total <= MULTI_CITY_MAX_LEGS):

        await update.message.reply_text(
            f"❌ Must be between {MULTI_CITY_MIN_LEGS} and {MULTI_CITY_MAX_LEGS}."
        )
        return CHECK_MULTI_COUNT

    data = context.user_data["check"]
    data["multi_total"] = total
    data["legs"] = [
        {"origin": data["origin"][0], "destination": data["destination"][0]}
    ]

    await update.message.reply_text(
        f"Leg 1 of {total}: {data['legs'][0]['origin']} → {data['legs'][0]['destination']}\n\n"
        "Send its date (YYYY-MM-DD)."
    )

    return CHECK_MULTI_LEG_DATE


async def check_multi_leg_date(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    if not is_valid_date(text):

        await update.message.reply_text(
            "❌ Please send a valid date as YYYY-MM-DD."
        )
        return CHECK_MULTI_LEG_DATE

    data = context.user_data["check"]
    data["legs"][0]["date"] = text

    await update.message.reply_text(
        f"Leg 2 of {data['multi_total']}: send ORIGIN DESTINATION DATE\n"
        "(e.g. LIS CDG 2026-09-05)."
    )

    return CHECK_MULTI_LEG


async def check_multi_leg(update: Update, context: ContextTypes.DEFAULT_TYPE):

    parts = update.message.text.strip().split()
    data = context.user_data["check"]

    if len(parts) != 3:

        await update.message.reply_text(
            "❌ Send exactly 3 values: ORIGIN DESTINATION DATE "
            "(e.g. LIS CDG 2026-09-05)."
        )
        return CHECK_MULTI_LEG

    origin, destination, date_text = (p.upper() if i < 2 else p for i, p in enumerate(parts))

    code_error = validate_codes([origin]) or validate_codes([destination])

    if code_error:
        await update.message.reply_text(f"❌ {esc(code_error)}")
        return CHECK_MULTI_LEG

    if not is_valid_date(date_text):
        await update.message.reply_text("❌ Please send a valid date as YYYY-MM-DD.")
        return CHECK_MULTI_LEG

    data["legs"].append({"origin": origin, "destination": destination, "date": date_text})

    if len(data["legs"]) < data["multi_total"]:

        next_n = len(data["legs"]) + 1

        await update.message.reply_text(
            f"Leg {next_n} of {data['multi_total']}: send ORIGIN DESTINATION DATE."
        )
        return CHECK_MULTI_LEG

    data = context.user_data.pop("check")

    legs_text = "\n".join(
        f"{i}. {esc(leg['origin'])} ➜ {esc(leg['destination'])} on {esc(leg['date'])}"
        for i, leg in enumerate(data["legs"], start=1)
    )

    await update.message.reply_text(f"🔍 Searching multi-city itinerary...\n\n{legs_text}")

    service = FlightService()

    try:
        result = await service.cheapest_multi_city(
            legs=data["legs"],
            cabin_class=data["cabin_class"],
            max_stops=data["max_stops"],
        )

    except ValueError as exc:

        await update.message.reply_text(f"❌ {esc(exc)}", reply_markup=main_menu())
        return ConversationHandler.END

    if result is None:

        await update.message.reply_text(
            "❌ No flights found for this itinerary (multi-city is currently "
            "only searched via Google Flights).",
            reply_markup=main_menu(),
        )
        return ConversationHandler.END

    text = (
        "<b>✈️ Cheapest Multi-city Itinerary</b>\n\n"
        f"🏢 Provider : {esc(result.provider)}\n\n"
        f"✈ Airline : {esc(result.airline)}\n\n"
        f"💰 Price : <b>{result.price:.0f} {esc(result.currency)}</b>\n\n"
        f"{legs_text}"
    )

    if result.booking_url:
        text += f'\n\n<a href="{esc(result.booking_url)}">🔗 View Flight</a>'

    await update.message.reply_text(
        text=text,
        reply_markup=main_menu(),
    )

    return ConversationHandler.END


async def check_departure(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    if not is_valid_date(text):

        await update.message.reply_text(
            "❌ Please send a valid date as YYYY-MM-DD."
        )
        return CHECK_DEPARTURE

    data = context.user_data["check"]
    data["departure_date"] = text

    if data["trip_type"] == "one-way":

        data["return_date"] = ""
        await update.message.reply_text(_flex_prompt())
        return CHECK_FLEX

    await update.message.reply_text("Send the RETURN date (YYYY-MM-DD).")

    return CHECK_RETURN


async def check_return(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    if not is_valid_date(text):

        await update.message.reply_text(
            "❌ Please send a valid date as YYYY-MM-DD."
        )
        return CHECK_RETURN

    context.user_data["check"]["return_date"] = text

    await update.message.reply_text(_flex_prompt())

    return CHECK_FLEX


async def check_flex(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    try:
        flex_days = int(text)

    except ValueError:

        await update.message.reply_text("❌ Send a whole number, e.g. 0 or 3.")
        return CHECK_FLEX

    data = context.user_data.pop("check")

    error = validate_search_scope(data["origin"], data["destination"], flex_days)

    if error:

        # Put the data back since we're not ending the conversation.
        context.user_data["check"] = data
        await update.message.reply_text(f"❌ {esc(error)}")
        return CHECK_FLEX

    combos = len(data["origin"]) * len(data["destination"]) * (2 * flex_days + 1)

    await update.message.reply_text(f"🔍 Searching {combos} combination(s)...")

    service = FlightService()

    try:
        result = await service.cheapest_flight(
            origin=",".join(data["origin"]),
            destination=",".join(data["destination"]),
            departure_date=data["departure_date"],
            return_date=data["return_date"] or None,
            date_flex_days=flex_days,
            trip_type=data["trip_type"],
            cabin_class=data["cabin_class"],
            max_stops=data["max_stops"],
        )

    except ValueError as exc:

        await update.message.reply_text(
            f"❌ {esc(exc)}",
            reply_markup=main_menu(),
        )
        return ConversationHandler.END

    if result is None:

        await update.message.reply_text(
            "❌ No flights found.",
            reply_markup=main_menu(),
        )

        return ConversationHandler.END

    text = (
        "<b>✈️ Cheapest Flight</b>\n\n"
        f"🏢 Provider : {esc(result.provider)}\n\n"
        f"✈ Airline : {esc(result.airline)}\n\n"
        f"💰 Price : <b>{result.price:.0f} {esc(result.currency)}</b>\n\n"
        f"📍 Route : <b>{esc(result.origin)} ➜ {esc(result.destination)}</b>\n\n"
        f"📅 Departure : {esc(result.departure_date)}"
    )

    if data["trip_type"] == "round-trip":
        text += f"\n\n🔁 Return : {esc(result.return_date)}"

    if result.booking_url:
        text += f'\n\n<a href="{esc(result.booking_url)}">🔗 View Flight</a>'

    recommendation = AnalyticsService().recommendation_for_route(
        result.origin, result.destination, result.price
    )

    if recommendation:
        text += f"\n\n<b>{recommendation}</b>"

    await update.message.reply_text(
        text=text,
        reply_markup=main_menu(),
    )

    return ConversationHandler.END


# ==============================
# EDIT FLIGHT WIZARD
# ==============================

(
    EDIT_ORIGIN,
    EDIT_DESTINATION,
    EDIT_FILTERS,
    EDIT_DEPARTURE,
    EDIT_RETURN,
    EDIT_FLEX,
    EDIT_TARGET,
    EDIT_MULTI_COUNT,
    EDIT_MULTI_LEG_DATE,
    EDIT_MULTI_LEG,
) = range(19, 29)


async def edit_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    flight_id = int(query.data.split("_")[1])
    flight = tracking.get_by_id(flight_id)

    if flight is None:

        await query.message.reply_text(
            "❌ That flight no longer exists.",
            reply_markup=main_menu(),
        )
        return ConversationHandler.END

    context.user_data["edit"] = {
        "id": flight.id,
        "origin": parse_codes(flight.origin),
        "destination": parse_codes(flight.destination),
        "departure_date": flight.departure_date,
        "return_date": flight.return_date,
        "date_flex_days": flight.date_flex_days,
        "max_price": flight.max_price,
        "trip_type": flight.trip_type,
        "cabin_class": flight.cabin_class,
        "max_stops": flight.max_stops,
        "legs": flight.legs,
        "multi_total": len(flight.legs) if flight.legs else None,
    }

    await query.message.reply_text(
        "✏️ Edit Flight\n\n"
        f"Current origin: {flight.origin}\n\n"
        "Send new ORIGIN airport code(s), comma-separated, "
        f"or send \"{KEEP}\" to keep it as is.\n\n"
        "Send /cancel to stop."
    )

    return EDIT_ORIGIN


async def edit_origin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()
    data = context.user_data["edit"]

    if text != KEEP:

        codes = parse_codes(text)
        error = validate_codes(codes)

        if error or not codes:

            await update.message.reply_text(
                f"❌ {error or 'Send at least one airport code.'}"
            )
            return EDIT_ORIGIN

        data["origin"] = codes

    await update.message.reply_text(
        f"Current destination: {','.join(data['destination'])}\n\n"
        "Send new DESTINATION airport code(s), comma-separated, "
        f"or send \"{KEEP}\" to keep it as is."
    )

    return EDIT_DESTINATION


async def edit_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()
    data = context.user_data["edit"]

    if text != KEEP:

        codes = parse_codes(text)
        error = validate_codes(codes)

        if error or not codes:

            await update.message.reply_text(
                f"❌ {error or 'Send at least one airport code.'}"
            )
            return EDIT_DESTINATION

        data["destination"] = codes

    await update.message.reply_text(
        FILTERS_SCREEN_TEXT,
        reply_markup=filters_keyboard(
            data["trip_type"], data["cabin_class"], data["max_stops"]
        ),
    )

    return EDIT_FILTERS


async def edit_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = await _resume_or_restart(update, context, "edit", "✏️ Edit on a flight card")

    if data is None:
        return ConversationHandler.END

    if query.data == "af_continue":

        if data["trip_type"] == "multi-city":

            existing_note = (
                "\n\n(This re-enters the full itinerary - it replaces the "
                "current legs.)"
                if data.get("legs")
                else ""
            )

            await query.message.reply_text(
                "🌍 Multi-city trip\n\n"
                f"How many flights/cities in total, including "
                f"{data['origin'][0]} → {data['destination'][0]}? "
                f"({MULTI_CITY_MIN_LEGS}-{MULTI_CITY_MAX_LEGS})"
                f"{existing_note}"
            )
            return EDIT_MULTI_COUNT

        await query.message.reply_text(
            f"Current departure: {data['departure_date']}\n\n"
            f"Send new DEPARTURE date (YYYY-MM-DD), or send \"{KEEP}\" to keep it."
        )
        return EDIT_DEPARTURE

    _apply_filter_toggle(query.data, data)

    await query.edit_message_reply_markup(
        reply_markup=filters_keyboard(
            data["trip_type"], data["cabin_class"], data["max_stops"]
        )
    )

    return EDIT_FILTERS


async def edit_multi_count(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    try:
        total = int(text)

    except ValueError:

        await update.message.reply_text(
            f"❌ Send a whole number between {MULTI_CITY_MIN_LEGS} and {MULTI_CITY_MAX_LEGS}."
        )
        return EDIT_MULTI_COUNT

    if not (MULTI_CITY_MIN_LEGS <= total <= MULTI_CITY_MAX_LEGS):

        await update.message.reply_text(
            f"❌ Must be between {MULTI_CITY_MIN_LEGS} and {MULTI_CITY_MAX_LEGS}."
        )
        return EDIT_MULTI_COUNT

    data = context.user_data["edit"]
    data["multi_total"] = total
    data["legs"] = [
        {"origin": data["origin"][0], "destination": data["destination"][0]}
    ]

    await update.message.reply_text(
        f"Leg 1 of {total}: {data['legs'][0]['origin']} → {data['legs'][0]['destination']}\n\n"
        "Send its date (YYYY-MM-DD)."
    )

    return EDIT_MULTI_LEG_DATE


async def edit_multi_leg_date(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    if not is_valid_date(text):

        await update.message.reply_text(
            "❌ Please send a valid date as YYYY-MM-DD."
        )
        return EDIT_MULTI_LEG_DATE

    data = context.user_data["edit"]
    data["legs"][0]["date"] = text

    await update.message.reply_text(
        f"Leg 2 of {data['multi_total']}: send ORIGIN DESTINATION DATE\n"
        "(e.g. LIS CDG 2026-09-05)."
    )

    return EDIT_MULTI_LEG


async def edit_multi_leg(update: Update, context: ContextTypes.DEFAULT_TYPE):

    parts = update.message.text.strip().split()
    data = context.user_data["edit"]

    if len(parts) != 3:

        await update.message.reply_text(
            "❌ Send exactly 3 values: ORIGIN DESTINATION DATE "
            "(e.g. LIS CDG 2026-09-05)."
        )
        return EDIT_MULTI_LEG

    origin, destination, date_text = (p.upper() if i < 2 else p for i, p in enumerate(parts))

    code_error = validate_codes([origin]) or validate_codes([destination])

    if code_error:
        await update.message.reply_text(f"❌ {esc(code_error)}")
        return EDIT_MULTI_LEG

    if not is_valid_date(date_text):
        await update.message.reply_text("❌ Please send a valid date as YYYY-MM-DD.")
        return EDIT_MULTI_LEG

    data["legs"].append({"origin": origin, "destination": destination, "date": date_text})

    if len(data["legs"]) < data["multi_total"]:

        next_n = len(data["legs"]) + 1

        await update.message.reply_text(
            f"Leg {next_n} of {data['multi_total']}: send ORIGIN DESTINATION DATE."
        )
        return EDIT_MULTI_LEG

    await update.message.reply_text(
        f"Current target: {data['max_price']:.0f} SAR\n\n"
        f"Send new TARGET price in SAR, or send \"{KEEP}\" to keep it."
    )

    return EDIT_TARGET


async def edit_departure(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()
    data = context.user_data["edit"]

    if text != KEEP:

        if not is_valid_date(text):

            await update.message.reply_text(
                "❌ Please send a valid date as YYYY-MM-DD."
            )
            return EDIT_DEPARTURE

        data["departure_date"] = text

    if data["trip_type"] == "one-way":

        data["return_date"] = ""

        await update.message.reply_text(
            f"Current flex: +/-{data['date_flex_days']} day(s)\n\n"
            f"{_flex_prompt()}\n\nSend \"{KEEP}\" to keep it."
        )
        return EDIT_FLEX

    await update.message.reply_text(
        f"Current return: {data['return_date']}\n\n"
        f"Send new RETURN date (YYYY-MM-DD), or send \"{KEEP}\" to keep it."
    )

    return EDIT_RETURN


async def edit_return(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()
    data = context.user_data["edit"]

    if text != KEEP:

        if not is_valid_date(text):

            await update.message.reply_text(
                "❌ Please send a valid date as YYYY-MM-DD."
            )
            return EDIT_RETURN

        data["return_date"] = text

    await update.message.reply_text(
        f"Current flex: +/-{data['date_flex_days']} day(s)\n\n"
        f"{_flex_prompt()}\n\nSend \"{KEEP}\" to keep it."
    )

    return EDIT_FLEX


async def edit_flex(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()
    data = context.user_data["edit"]

    if text != KEEP:

        try:
            flex_days = int(text)

        except ValueError:

            await update.message.reply_text("❌ Send a whole number, e.g. 0 or 3.")
            return EDIT_FLEX

        error = validate_search_scope(data["origin"], data["destination"], flex_days)

        if error:

            await update.message.reply_text(f"❌ {esc(error)}")
            return EDIT_FLEX

        data["date_flex_days"] = flex_days

    await update.message.reply_text(
        f"Current target: {data['max_price']:.0f} SAR\n\n"
        f"Send new TARGET price in SAR, or send \"{KEEP}\" to keep it."
    )

    return EDIT_TARGET


async def edit_target(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()
    data = context.user_data.pop("edit")

    if text != KEEP:

        try:
            data["max_price"] = float(text)

        except ValueError:

            context.user_data["edit"] = data
            await update.message.reply_text("❌ Target price must be numeric.")
            return EDIT_TARGET

    if data["trip_type"] == "multi-city":

        legs = data["legs"]

        tracking.update(
            flight_id=data["id"],
            origin=legs[0]["origin"],
            destination=legs[-1]["destination"],
            departure_date=legs[0]["date"],
            return_date="",
            max_price=data["max_price"],
            date_flex_days=0,
            trip_type="multi-city",
            cabin_class=data["cabin_class"],
            max_stops=data["max_stops"],
            legs=legs,
        )

        legs_text = "\n".join(
            f"{i}. {esc(leg['origin'])} ➜ {esc(leg['destination'])} on {esc(leg['date'])}"
            for i, leg in enumerate(legs, start=1)
        )

        await update.message.reply_text(
            text=(
                "✅ <b>Flight Updated</b> <i>(multi-city)</i>\n\n"
                f"{legs_text}\n\n"
                f"🎯 Target : <b>{data['max_price']:.0f} SAR</b>"
            ),
            reply_markup=main_menu(),
        )

        return ConversationHandler.END

    # Re-validate the final combination in case origin/destination/flex
    # changed independently earlier in the conversation.
    error = validate_search_scope(
        data["origin"], data["destination"], data["date_flex_days"]
    )

    if error:

        await update.message.reply_text(
            f"❌ {esc(error)}\n\nEdit cancelled — nothing was changed.",
            reply_markup=main_menu(),
        )
        return ConversationHandler.END

    tracking.update(
        flight_id=data["id"],
        origin=",".join(data["origin"]),
        destination=",".join(data["destination"]),
        departure_date=data["departure_date"],
        return_date=data["return_date"],
        max_price=data["max_price"],
        date_flex_days=data["date_flex_days"],
        trip_type=data["trip_type"],
        cabin_class=data["cabin_class"],
        max_stops=data["max_stops"],
    )

    flex_text = (
        f"\n🎚 Flex : +/-{data['date_flex_days']} day(s)"
        if data["date_flex_days"]
        else ""
    )

    filters_text = format_filters(data["trip_type"], data["cabin_class"], data["max_stops"])
    filters_line = f"\n🎛 {filters_text}" if filters_text else ""

    return_line = (
        f"🔁 Return : {esc(data['return_date'])}\n"
        if data["trip_type"] == "round-trip"
        else "↩ One-way\n"
    )

    await update.message.reply_text(
        text=(
            "✅ <b>Flight Updated</b>\n\n"
            f"📍 <b>{esc(','.join(data['origin']))} ➜ {esc(','.join(data['destination']))}</b>\n\n"
            f"📅 Departure : {esc(data['departure_date'])}\n"
            f"{return_line}"
            f"{flex_text}{filters_line}\n\n"
            f"🎯 Target : <b>{data['max_price']:.0f} SAR</b>"
        ),
        reply_markup=main_menu(),
    )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.pop("add", None)
    context.user_data.pop("check", None)
    context.user_data.pop("edit", None)

    await update.message.reply_text(
        "❌ Cancelled.",
        reply_markup=main_menu(),
    )

    return ConversationHandler.END


add_flight_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(add_entry, pattern="^menu_add$"),
    ],
    states={
        ADD_ORIGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_origin)],
        ADD_DESTINATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_destination)],
        ADD_FILTERS: [CallbackQueryHandler(add_filters, pattern="^af_")],
        ADD_DEPARTURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_departure)],
        ADD_RETURN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_return)],
        ADD_FLEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_flex)],
        ADD_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_target)],
        ADD_MULTI_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_multi_count)],
        ADD_MULTI_LEG_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_multi_leg_date)],
        ADD_MULTI_LEG: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_multi_leg)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    name="add_flight_conversation",
    persistent=True,
)


check_flight_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(check_entry, pattern="^menu_check$"),
    ],
    states={
        CHECK_ORIGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_origin)],
        CHECK_DESTINATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_destination)],
        CHECK_FILTERS: [CallbackQueryHandler(check_filters, pattern="^af_")],
        CHECK_DEPARTURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_departure)],
        CHECK_RETURN: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_return)],
        CHECK_FLEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_flex)],
        CHECK_MULTI_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_multi_count)],
        CHECK_MULTI_LEG_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_multi_leg_date)],
        CHECK_MULTI_LEG: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_multi_leg)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    name="check_flight_conversation",
    persistent=True,
)


edit_flight_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(edit_entry, pattern=r"^edit_\d+$"),
    ],
    states={
        EDIT_ORIGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_origin)],
        EDIT_DESTINATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_destination)],
        EDIT_FILTERS: [CallbackQueryHandler(edit_filters, pattern="^af_")],
        EDIT_DEPARTURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_departure)],
        EDIT_RETURN: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_return)],
        EDIT_FLEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_flex)],
        EDIT_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_target)],
        EDIT_MULTI_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_multi_count)],
        EDIT_MULTI_LEG_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_multi_leg_date)],
        EDIT_MULTI_LEG: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_multi_leg)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    name="edit_flight_conversation",
    persistent=True,
)
