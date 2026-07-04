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


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.pop("add", None)
    context.user_data.pop("check", None)

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
