from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.bot.keyboards import main_menu
from app.services.flight_service import FlightService
from app.services.tracking_service import TrackingService
from app.utils.airports import parse_codes, validate_codes
from app.utils.dates import is_valid_date
from app.utils.search_scope import validate_search_scope

tracking = TrackingService()


def _format_flex_prompt(step: str, total: str) -> str:

    return (
        f"Step {step}/{total}\n"
        "Send how many days flexible (0-5). 0 = exact dates only.\n\n"
        "e.g. \"3\" checks +/-3 days around your dates too."
    )


# ==============================
# ADD FLIGHT WIZARD
# ==============================

(
    ADD_ORIGIN,
    ADD_DESTINATION,
    ADD_DEPARTURE,
    ADD_RETURN,
    ADD_FLEX,
    ADD_TARGET,
) = range(6)


async def add_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    context.user_data.pop("add", None)

    await query.message.reply_text(
        "➕ Add Flight\n\n"
        "Step 1/6\n"
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
            f"❌ {error or 'Send at least one airport code.'}"
        )
        return ADD_ORIGIN

    context.user_data.setdefault("add", {})["origin"] = codes

    await update.message.reply_text(
        "Step 2/6\n"
        "Send the DESTINATION airport code(s), comma-separated\n"
        "(e.g. LIS or LIS,OPO)."
    )

    return ADD_DESTINATION


async def add_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):

    codes = parse_codes(update.message.text)
    error = validate_codes(codes)

    if error or not codes:

        await update.message.reply_text(
            f"❌ {error or 'Send at least one airport code.'}"
        )
        return ADD_DESTINATION

    context.user_data["add"]["destination"] = codes

    await update.message.reply_text(
        "Step 3/6\nSend the DEPARTURE date (YYYY-MM-DD)."
    )

    return ADD_DEPARTURE


async def add_departure(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    if not is_valid_date(text):

        await update.message.reply_text(
            "❌ Please send a valid date as YYYY-MM-DD."
        )
        return ADD_DEPARTURE

    context.user_data["add"]["departure_date"] = text

    await update.message.reply_text(
        "Step 4/6\nSend the RETURN date (YYYY-MM-DD)."
    )

    return ADD_RETURN


async def add_return(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    if not is_valid_date(text):

        await update.message.reply_text(
            "❌ Please send a valid date as YYYY-MM-DD."
        )
        return ADD_RETURN

    context.user_data["add"]["return_date"] = text

    await update.message.reply_text(_format_flex_prompt("5", "6"))

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

        await update.message.reply_text(f"❌ {error}")
        return ADD_FLEX

    data["date_flex_days"] = flex_days

    await update.message.reply_text(
        "Step 6/6\nSend your TARGET price in SAR (numbers only, e.g. 1800)."
    )

    return ADD_TARGET


async def add_target(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        max_price = float(update.message.text.strip())

    except ValueError:

        await update.message.reply_text("❌ Target price must be numeric.")
        return ADD_TARGET

    data = context.user_data.pop("add")

    tracking.add(
        origin=",".join(data["origin"]),
        destination=",".join(data["destination"]),
        departure_date=data["departure_date"],
        return_date=data["return_date"],
        max_price=max_price,
        date_flex_days=data["date_flex_days"],
    )

    flex_text = (
        f"\n🎚 Flex : +/-{data['date_flex_days']} day(s)"
        if data["date_flex_days"]
        else ""
    )

    await update.message.reply_text(
        text=(
            "✅ Flight Added\n\n"
            f"📍 {','.join(data['origin'])} ➜ {','.join(data['destination'])}\n\n"
            f"📅 Departure : {data['departure_date']}\n"
            f"🔁 Return : {data['return_date']}"
            f"{flex_text}\n\n"
            f"🎯 Target : {max_price:.0f} SAR"
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
    CHECK_DEPARTURE,
    CHECK_RETURN,
    CHECK_FLEX,
) = range(6, 11)


async def check_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    context.user_data.pop("check", None)

    await query.message.reply_text(
        "🔍 Check Flight\n\n"
        "Step 1/5\n"
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
            f"❌ {error or 'Send at least one airport code.'}"
        )
        return CHECK_ORIGIN

    context.user_data.setdefault("check", {})["origin"] = codes

    await update.message.reply_text(
        "Step 2/5\n"
        "Send the DESTINATION airport code(s), comma-separated\n"
        "(e.g. LIS or LIS,OPO)."
    )

    return CHECK_DESTINATION


async def check_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):

    codes = parse_codes(update.message.text)
    error = validate_codes(codes)

    if error or not codes:

        await update.message.reply_text(
            f"❌ {error or 'Send at least one airport code.'}"
        )
        return CHECK_DESTINATION

    context.user_data["check"]["destination"] = codes

    await update.message.reply_text(
        "Step 3/5\nSend the DEPARTURE date (YYYY-MM-DD)."
    )

    return CHECK_DEPARTURE


async def check_departure(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    if not is_valid_date(text):

        await update.message.reply_text(
            "❌ Please send a valid date as YYYY-MM-DD."
        )
        return CHECK_DEPARTURE

    context.user_data["check"]["departure_date"] = text

    await update.message.reply_text(
        "Step 4/5\nSend the RETURN date (YYYY-MM-DD)."
    )

    return CHECK_RETURN


async def check_return(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    if not is_valid_date(text):

        await update.message.reply_text(
            "❌ Please send a valid date as YYYY-MM-DD."
        )
        return CHECK_RETURN

    context.user_data["check"]["return_date"] = text

    await update.message.reply_text(_format_flex_prompt("5", "5"))

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
        await update.message.reply_text(f"❌ {error}")
        return CHECK_FLEX

    combos = len(data["origin"]) * len(data["destination"]) * (2 * flex_days + 1)

    await update.message.reply_text(f"🔍 Searching {combos} combination(s)...")

    service = FlightService()

    try:
        result = await service.cheapest_flight(
            origin=",".join(data["origin"]),
            destination=",".join(data["destination"]),
            departure_date=data["departure_date"],
            return_date=data["return_date"],
            date_flex_days=flex_days,
        )

    except ValueError as exc:

        await update.message.reply_text(
            f"❌ {exc}",
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
    EDIT_DEPARTURE,
    EDIT_RETURN,
    EDIT_FLEX,
    EDIT_TARGET,
) = range(11, 17)

KEEP = "-"


async def edit_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    context.user_data.pop("edit", None)

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
    }

    await query.message.reply_text(
        "✏️ Edit Flight\n\n"
        f"Current origin: {flight.origin}\n\n"
        "Step 1/6\n"
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
        "Step 2/6\n"
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
        f"Current departure: {data['departure_date']}\n\n"
        "Step 3/6\n"
        f"Send new DEPARTURE date (YYYY-MM-DD), or send \"{KEEP}\" to keep it."
    )

    return EDIT_DEPARTURE


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

    await update.message.reply_text(
        f"Current return: {data['return_date']}\n\n"
        "Step 4/6\n"
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
        f"Step 5/6\n"
        "Send how many days flexible (0-5), "
        f"or send \"{KEEP}\" to keep it."
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

            await update.message.reply_text(f"❌ {error}")
            return EDIT_FLEX

        data["date_flex_days"] = flex_days

    await update.message.reply_text(
        f"Current target: {data['max_price']:.0f} SAR\n\n"
        "Step 6/6\n"
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

    # Re-validate the final combination in case origin/destination changed
    # after the flex value was already confirmed.
    error = validate_search_scope(
        data["origin"], data["destination"], data["date_flex_days"]
    )

    if error:

        await update.message.reply_text(
            f"❌ {error}\n\nEdit cancelled — nothing was changed.",
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
    )

    flex_text = (
        f"\n🎚 Flex : +/-{data['date_flex_days']} day(s)"
        if data["date_flex_days"]
        else ""
    )

    await update.message.reply_text(
        text=(
            "✅ Flight Updated\n\n"
            f"📍 {','.join(data['origin'])} ➜ {','.join(data['destination'])}\n\n"
            f"📅 Departure : {data['departure_date']}\n"
            f"🔁 Return : {data['return_date']}"
            f"{flex_text}\n\n"
            f"🎯 Target : {data['max_price']:.0f} SAR"
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
        ADD_DEPARTURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_departure)],
        ADD_RETURN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_return)],
        ADD_FLEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_flex)],
        ADD_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_target)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    name="add_flight_conversation",
)


check_flight_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(check_entry, pattern="^menu_check$"),
    ],
    states={
        CHECK_ORIGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_origin)],
        CHECK_DESTINATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_destination)],
        CHECK_DEPARTURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_departure)],
        CHECK_RETURN: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_return)],
        CHECK_FLEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_flex)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    name="check_flight_conversation",
)


edit_flight_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(edit_entry, pattern=r"^edit_\d+$"),
    ],
    states={
        EDIT_ORIGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_origin)],
        EDIT_DESTINATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_destination)],
        EDIT_DEPARTURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_departure)],
        EDIT_RETURN: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_return)],
        EDIT_FLEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_flex)],
        EDIT_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_target)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    name="edit_flight_conversation",
)
