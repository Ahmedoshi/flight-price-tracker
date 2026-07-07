from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards import main_menu
from app.bot.screens import DIVIDER, analytics_screen, status_screen
from app.config.settings import settings
from app.services.analytics_service import AnalyticsService
from app.services.flight_service import FlightService
from app.services.tracking_service import TrackingService
from app.scheduler.scheduler import hourly_check
from app.utils.airports import parse_codes, validate_codes
from app.utils.dates import format_checked_at, is_valid_date
from app.utils.flight_filters import format_filters, parse_trailing_tokens
from app.utils.search_scope import validate_search_scope
from app.utils.text import esc

tracking = TrackingService()


def _kiwi_enabled() -> bool:

    return bool(settings.kiwi_api_key)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    flights = tracking.list()

    await update.message.reply_text(
        text=(
            "<b>✈️ Flight Price Tracker</b>\n\n"
            f"{DIVIDER}\n\n"
            "🟢 Bot Online\n"
            f"📍 Saved Flights : <b>{len(flights)}</b>\n"
            "⏰ Scheduler Ready\n\n"
            "<i>Select an option below.</i>"
        ),
        reply_markup=main_menu(),
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text, keyboard = status_screen()

    await update.message.reply_text(
        text=text,
        reply_markup=keyboard,
    )


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) < 4:

        await update.message.reply_text(
            text=(
                "Usage\n\n"
                "/check ORIGIN DESTINATION DEPARTURE RETURN [FLEX_DAYS] "
                "[trip=oneway] [cabin=business] [stops=0]\n\n"
                "ORIGIN/DESTINATION can be a comma-separated list of airports.\n"
                "For one-way, send RETURN as \"-\" and add trip=oneway.\n\n"
                "Example\n"
                "/check RUH,DMM LIS,OPO 2026-09-01 2026-09-15 3\n"
                "/check RUH LIS 2026-09-01 - trip=oneway cabin=business"
            ),
            reply_markup=main_menu(),
        )
        return

    origin = context.args[0]
    destination = context.args[1]
    departure_date = context.args[2]
    return_date_arg = context.args[3]

    flex_days, filters, error = parse_trailing_tokens(context.args[4:])

    if error:
        await update.message.reply_text(f"❌ {esc(error)}", reply_markup=main_menu())
        return

    trip_type = filters["trip_type"]
    return_date = None if return_date_arg == "-" else return_date_arg

    if trip_type == "round-trip" and return_date is None:

        await update.message.reply_text(
            "❌ Round-trip needs a real RETURN date "
            "(or send \"-\" together with trip=oneway).",
            reply_markup=main_menu(),
        )
        return

    origins = parse_codes(origin)
    destinations = parse_codes(destination)

    code_error = validate_codes(origins) or validate_codes(destinations)

    if code_error:
        await update.message.reply_text(f"❌ {esc(code_error)}", reply_markup=main_menu())
        return

    scope_error = validate_search_scope(origins, destinations, flex_days)

    if scope_error:
        await update.message.reply_text(f"❌ {esc(scope_error)}", reply_markup=main_menu())
        return

    combos = len(origins) * len(destinations) * (2 * flex_days + 1)

    await update.message.reply_text(
        f"🔍 Searching {combos} combination(s) across Google Flights"
        + (" and Kiwi.com" if _kiwi_enabled() else "")
        + "..."
    )

    service = FlightService()

    try:
        result = await service.cheapest_flight(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            date_flex_days=flex_days,
            trip_type=trip_type,
            cabin_class=filters["cabin_class"],
            max_stops=filters["max_stops"],
        )

    except ValueError as exc:
        await update.message.reply_text(f"❌ {esc(exc)}", reply_markup=main_menu())
        return

    if result is None:

        await update.message.reply_text(
            "❌ No flights found.",
            reply_markup=main_menu(),
        )
        return

    text = (
        "<b>✈️ Cheapest Flight</b>\n\n"
        f"🏢 Provider : {esc(result.provider)}\n\n"
        f"✈ Airline : {esc(result.airline)}\n\n"
        f"💰 Price : <b>{result.price:.0f} {esc(result.currency)}</b>\n\n"
        f"📍 Route : <b>{esc(result.origin)} ➜ {esc(result.destination)}</b>\n\n"
        f"📅 Departure : {esc(result.departure_date)}"
    )

    if trip_type == "round-trip":
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


async def check_now(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        text="Press 🔍 Check Flight from the menu.",
        reply_markup=main_menu(),
    )


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) < 5:

        await update.message.reply_text(
            text=(
                "Usage\n\n"
                "/add ORIGIN DESTINATION DEPARTURE RETURN TARGET [FLEX_DAYS] "
                "[trip=oneway] [cabin=business] [stops=0]\n\n"
                "ORIGIN/DESTINATION can be a comma-separated list of airports.\n"
                "For one-way, send RETURN as \"-\" and add trip=oneway.\n\n"
                "Example\n"
                "/add RUH,DMM LIS,OPO 2026-09-01 2026-09-15 1800 3\n"
                "/add RUH LIS 2026-09-01 - 1800 trip=oneway stops=0"
            ),
            reply_markup=main_menu(),
        )
        return

    origin = context.args[0]
    destination = context.args[1]
    departure_date = context.args[2]
    return_date_arg = context.args[3]

    try:
        max_price = float(context.args[4])

    except ValueError:

        await update.message.reply_text(
            "❌ Target price must be numeric.",
            reply_markup=main_menu(),
        )
        return

    if not is_valid_date(departure_date):

        await update.message.reply_text(
            "❌ Departure date must be in YYYY-MM-DD format.",
            reply_markup=main_menu(),
        )
        return

    flex_days, filters, error = parse_trailing_tokens(context.args[5:])

    if error:
        await update.message.reply_text(f"❌ {esc(error)}", reply_markup=main_menu())
        return

    trip_type = filters["trip_type"]
    return_date = None if return_date_arg == "-" else return_date_arg

    if trip_type == "round-trip":

        if return_date is None or not is_valid_date(return_date):

            await update.message.reply_text(
                "❌ Round-trip needs a real RETURN date in YYYY-MM-DD format "
                "(or send \"-\" together with trip=oneway).",
                reply_markup=main_menu(),
            )
            return

    else:
        return_date = ""  # not applicable for one-way, stored blank

    origins = parse_codes(origin)
    destinations = parse_codes(destination)

    code_error = validate_codes(origins) or validate_codes(destinations)

    if code_error:
        await update.message.reply_text(f"❌ {esc(code_error)}", reply_markup=main_menu())
        return

    scope_error = validate_search_scope(origins, destinations, flex_days)

    if scope_error:
        await update.message.reply_text(f"❌ {esc(scope_error)}", reply_markup=main_menu())
        return

    tracking.add(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        max_price=max_price,
        date_flex_days=flex_days,
        trip_type=trip_type,
        cabin_class=filters["cabin_class"],
        max_stops=filters["max_stops"],
    )

    flex_text = f"\n🎚 Flex : +/-{flex_days} day(s)" if flex_days else ""
    filters_text = format_filters(trip_type, filters["cabin_class"], filters["max_stops"])
    filters_line = f"\n🎛 {filters_text}" if filters_text else ""

    return_line = (
        f"🔁 Return : {esc(return_date)}\n" if trip_type == "round-trip" else "↩ One-way\n"
    )

    await update.message.reply_text(
        text=(
            "✅ Flight Added\n\n"
            f"📍 <b>{esc(','.join(origins))} ➜ {esc(','.join(destinations))}</b>\n\n"
            f"📅 Departure : {esc(departure_date)}\n"
            f"{return_line}"
            f"{flex_text}{filters_line}\n\n"
            f"🎯 Target : <b>{max_price:.0f} SAR</b>"
        ),
        reply_markup=main_menu(),
    )


async def list(update: Update, context: ContextTypes.DEFAULT_TYPE):

    flights = tracking.list()

    if not flights:

        await update.message.reply_text(
            "📋 No saved flights.",
            reply_markup=main_menu(),
        )
        return

    text = "<b>📋 Saved Flights</b>\n\n"

    for i, flight in enumerate(flights, start=1):

        flex_text = f" <i>(+/-{flight.date_flex_days}d)</i>" if flight.date_flex_days else ""

        return_line = (
            f"🔁 {esc(flight.return_date)}{flex_text}\n"
            if flight.trip_type == "round-trip"
            else "↩ <i>One-way</i>\n"
        )

        filters_text = format_filters(
            flight.trip_type, flight.cabin_class, flight.max_stops
        )
        filters_line = f"🎛 <i>{esc(filters_text)}</i>\n" if filters_text else ""

        text += (
            f"{i}. <b>{esc(flight.origin)} ➜ {esc(flight.destination)}</b>\n"
            f"📅 {esc(flight.departure_date)}\n"
            f"{return_line}"
            f"{filters_line}"
            f"🎯 <b>{flight.max_price:.0f} SAR</b>\n\n"
        )

    await update.message.reply_text(
        text=text,
        reply_markup=main_menu(),
    )


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) != 1:

        await update.message.reply_text(
            "Usage\n\n/delete 1",
            reply_markup=main_menu(),
        )
        return

    try:
        position = int(context.args[0])

    except ValueError:

        await update.message.reply_text(
            "❌ Invalid number.",
            reply_markup=main_menu(),
        )
        return

    flight = tracking.get_by_position(position)

    if flight is None:

        await update.message.reply_text(
            "❌ No flight at that number. Use /list to see valid numbers.",
            reply_markup=main_menu(),
        )
        return

    tracking.delete(flight.id)

    await update.message.reply_text(
        f"✅ Flight #{position} deleted.",
        reply_markup=main_menu(),
    )


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rows = tracking.history()

    if not rows:

        await update.message.reply_text(
            "📈 No price history.",
            reply_markup=main_menu(),
        )
        return

    text = "<b>📈 Price History</b>\n\n"

    for airline, price, checked_at in rows:

        text += (
            f"<i>{esc(format_checked_at(checked_at))}</i>\n"
            f"{esc(airline)}\n"
            f"<b>{price:.0f} SAR</b>\n\n"
        )

    await update.message.reply_text(
        text=text,
        reply_markup=main_menu(),
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cards = analytics_screen()

    for text, keyboard in cards:

        await update.message.reply_text(
            text=text,
            reply_markup=keyboard,
        )


async def run_scheduler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("⏳ Running Scheduler...")

    await hourly_check(context.application)

    await update.message.reply_text(
        "✅ Scheduler Finished.",
        reply_markup=main_menu(),
    )