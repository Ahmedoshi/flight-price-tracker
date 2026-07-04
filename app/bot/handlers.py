from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards import main_menu
from app.config.settings import settings
from app.services.flight_service import FlightService
from app.services.tracking_service import TrackingService
from app.scheduler.scheduler import hourly_check
from app.utils.airports import parse_codes, validate_codes
from app.utils.dates import is_valid_date
from app.utils.search_scope import validate_search_scope

tracking = TrackingService()


def _parse_flex_arg(text: str) -> tuple[int | None, str | None]:
    """Parse a flex-days argument. Returns (value, error)."""

    try:
        value = int(text)

    except ValueError:
        return None, "❌ Flex days must be a whole number."

    return value, None


def _kiwi_enabled() -> bool:

    return bool(settings.kiwi_api_key)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    flights = tracking.list()

    await update.message.reply_text(
        text=(
            "✈️ Flight Price Tracker\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🟢 Bot Online\n"
            f"📍 Saved Flights : {len(flights)}\n"
            "⏰ Scheduler Ready\n\n"
            "Select an option below."
        ),
        reply_markup=main_menu(),
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    flights = tracking.list()

    providers_text = "🟢 Google Flights : Ready\n"
    providers_text += (
        "🟢 Kiwi.com : Ready\n" if _kiwi_enabled() else "⚪ Kiwi.com : Not configured\n"
    )

    await update.message.reply_text(
        text=(
            "ℹ️ System Status\n\n"
            "🟢 Bot : Online\n"
            "🟢 Database : Ready\n"
            f"{providers_text}"
            "🟢 Scheduler : Running\n\n"
            f"📍 Saved Flights : {len(flights)}"
        ),
        reply_markup=main_menu(),
    )


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) not in (4, 5):

        await update.message.reply_text(
            text=(
                "Usage\n\n"
                "/check ORIGIN DESTINATION DEPARTURE RETURN [FLEX_DAYS]\n\n"
                "ORIGIN/DESTINATION can be a comma-separated list of airports.\n"
                "FLEX_DAYS (optional) searches +/- that many days.\n\n"
                "Example\n"
                "/check RUH,DMM LIS,OPO 2026-09-01 2026-09-15 3"
            ),
            reply_markup=main_menu(),
        )
        return

    origin = context.args[0]
    destination = context.args[1]
    departure_date = context.args[2]
    return_date = context.args[3]

    flex_days = 0

    if len(context.args) == 5:

        flex_days, error = _parse_flex_arg(context.args[4])

        if error:
            await update.message.reply_text(error, reply_markup=main_menu())
            return

    origins = parse_codes(origin)
    destinations = parse_codes(destination)

    code_error = validate_codes(origins) or validate_codes(destinations)

    if code_error:
        await update.message.reply_text(f"❌ {code_error}", reply_markup=main_menu())
        return

    scope_error = validate_search_scope(origins, destinations, flex_days)

    if scope_error:
        await update.message.reply_text(f"❌ {scope_error}", reply_markup=main_menu())
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
        )

    except ValueError as exc:
        await update.message.reply_text(f"❌ {exc}", reply_markup=main_menu())
        return

    if result is None:

        await update.message.reply_text(
            "❌ No flights found.",
            reply_markup=main_menu(),
        )
        return

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


async def check_now(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        text="Press 🔍 Check Flight from the menu.",
        reply_markup=main_menu(),
    )


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) not in (5, 6):

        await update.message.reply_text(
            text=(
                "Usage\n\n"
                "/add ORIGIN DESTINATION DEPARTURE RETURN TARGET [FLEX_DAYS]\n\n"
                "ORIGIN/DESTINATION can be a comma-separated list of airports.\n"
                "FLEX_DAYS (optional) tracks +/- that many days too.\n\n"
                "Example\n"
                "/add RUH,DMM LIS,OPO 2026-09-01 2026-09-15 1800 3"
            ),
            reply_markup=main_menu(),
        )
        return

    origin = context.args[0]
    destination = context.args[1]
    departure_date = context.args[2]
    return_date = context.args[3]

    try:
        max_price = float(context.args[4])

    except ValueError:

        await update.message.reply_text(
            "❌ Target price must be numeric.",
            reply_markup=main_menu(),
        )
        return

    if not is_valid_date(departure_date) or not is_valid_date(return_date):

        await update.message.reply_text(
            "❌ Dates must be in YYYY-MM-DD format.",
            reply_markup=main_menu(),
        )
        return

    flex_days = 0

    if len(context.args) == 6:

        flex_days, error = _parse_flex_arg(context.args[5])

        if error:
            await update.message.reply_text(error, reply_markup=main_menu())
            return

    origins = parse_codes(origin)
    destinations = parse_codes(destination)

    code_error = validate_codes(origins) or validate_codes(destinations)

    if code_error:
        await update.message.reply_text(f"❌ {code_error}", reply_markup=main_menu())
        return

    scope_error = validate_search_scope(origins, destinations, flex_days)

    if scope_error:
        await update.message.reply_text(f"❌ {scope_error}", reply_markup=main_menu())
        return

    tracking.add(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        max_price=max_price,
        date_flex_days=flex_days,
    )

    flex_text = f"\n🎚 Flex : +/-{flex_days} day(s)" if flex_days else ""

    await update.message.reply_text(
        text=(
            "✅ Flight Added\n\n"
            f"📍 {','.join(origins)} ➜ {','.join(destinations)}\n\n"
            f"📅 Departure : {departure_date}\n"
            f"🔁 Return : {return_date}"
            f"{flex_text}\n\n"
            f"🎯 Target : {max_price:.0f} SAR"
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

    text = "📋 Saved Flights\n\n"

    for i, flight in enumerate(flights, start=1):

        flex_text = f" (+/-{flight.date_flex_days}d)" if flight.date_flex_days else ""

        text += (
            f"{i}. {flight.origin} ➜ {flight.destination}\n"
            f"📅 {flight.departure_date}\n"
            f"🔁 {flight.return_date}{flex_text}\n"
            f"🎯 {flight.max_price:.0f} SAR\n\n"
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

    text = "📈 Price History\n\n"

    for airline, price, checked_at in rows:

        text += (
            f"{checked_at}\n"
            f"{airline}\n"
            f"{price:.0f} SAR\n\n"
        )

    await update.message.reply_text(
        text=text,
        reply_markup=main_menu(),
    )


async def run_scheduler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("⏳ Running Scheduler...")

    await hourly_check(context.application)

    await update.message.reply_text(
        "✅ Scheduler Finished.",
        reply_markup=main_menu(),
    )