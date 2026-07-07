import asyncio
import io

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import ContextTypes

from app.bot.keyboards import main_menu
from app.bot.screens import (
    home_screen,
    status_screen,
    scheduler_screen,
    flights_screen,
    history_screen,
    analytics_screen,
)
from app.scheduler.scheduler import (
    hourly_check,
    pause_scheduler,
    resume_scheduler,
    set_interval_hours,
)
from app.config.settings import settings
from app.services.analytics_service import AnalyticsService
from app.services.chart_service import ascii_sparkline, render_price_chart_png
from app.services.flight_service import FlightService
from app.services.tracking_service import TrackingService
from app.utils.text import esc

tracking = TrackingService()


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
    # PAUSE / RESUME SCHEDULER
    # ==========================

    elif query.data == "scheduler_pause":

        pause_scheduler()

        text, keyboard = scheduler_screen()

        await query.message.reply_text(
            text="⏸ Scheduler paused.\n\n" + text,
            reply_markup=keyboard,
        )

    elif query.data == "scheduler_resume":

        resume_scheduler()

        text, keyboard = scheduler_screen()

        await query.message.reply_text(
            text="▶ Scheduler resumed.\n\n" + text,
            reply_markup=keyboard,
        )

    # ==========================
    # SCHEDULER INTERVAL
    # ==========================

    elif query.data in ("scheduler_1", "scheduler_2", "scheduler_6"):

        hours = int(query.data.split("_")[1])

        set_interval_hours(hours)

        text, keyboard = scheduler_screen()

        await query.message.reply_text(
            text=f"🕑 Interval set to every {hours} hour(s).\n\n" + text,
            reply_markup=keyboard,
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
    # ANALYTICS
    # ==========================

    elif query.data == "menu_analytics":

        cards = analytics_screen()

        for text, keyboard in cards:

            await query.message.reply_text(
                text=text,
                reply_markup=keyboard,
            )

    # ==========================
    # CHECK FLIGHT (interactive search wizard)
    # ==========================
    # menu_check / menu_add are handled by the ConversationHandlers in
    # app.bot.conversations, which are registered ahead of this generic
    # handler. They're listed in main.py's handler order, not here.

    # ==========================
    # CHECK NOW (re-check price for a saved flight)
    # ==========================

    elif query.data.startswith("check_"):

        flight_id = int(query.data.split("_")[1])
        flight = tracking.get_by_id(flight_id)

        if flight is None:

            await query.message.reply_text(
                "❌ That flight no longer exists.",
                reply_markup=main_menu(),
            )

        else:

            await query.message.reply_text("🔍 Searching...")

            service = FlightService()
            is_multi_city = flight.trip_type == "multi-city" and flight.legs

            try:
                if is_multi_city:

                    result = await service.cheapest_multi_city(
                        legs=flight.legs,
                        cabin_class=flight.cabin_class,
                        max_stops=flight.max_stops,
                    )

                else:

                    result = await service.cheapest_flight(
                        origin=flight.origin,
                        destination=flight.destination,
                        departure_date=flight.departure_date,
                        return_date=flight.return_date,
                        date_flex_days=flight.date_flex_days,
                        trip_type=flight.trip_type,
                        cabin_class=flight.cabin_class,
                        max_stops=flight.max_stops,
                    )

            except ValueError as exc:

                await query.message.reply_text(
                    f"❌ {esc(exc)}",
                    reply_markup=main_menu(),
                )
                return

            if result is None:

                await query.message.reply_text(
                    "❌ No flights found.",
                    reply_markup=main_menu(),
                )

            elif is_multi_city:

                legs_text = "\n".join(
                    f"{i}. {esc(leg['origin'])} ➜ {esc(leg['destination'])} on {esc(leg['date'])}"
                    for i, leg in enumerate(flight.legs, start=1)
                )

                text = (
                    "<b>✈️ Cheapest Multi-city Itinerary</b>\n\n"
                    f"🏢 Provider : {esc(result.provider)}\n\n"
                    f"✈ Airline : {esc(result.airline)}\n\n"
                    f"💰 Price : <b>{result.price:.0f} {esc(result.currency)}</b>\n\n"
                    f"{legs_text}"
                )

                if result.booking_url:
                    text += f'\n\n<a href="{esc(result.booking_url)}">🔗 View Flight</a>'

                await query.message.reply_text(
                    text=text,
                    reply_markup=main_menu(),
                )

            else:

                text = (
                    "<b>✈️ Cheapest Flight</b>\n\n"
                    f"🏢 Provider : {esc(result.provider)}\n\n"
                    f"✈ Airline : {esc(result.airline)}\n\n"
                    f"💰 Price : <b>{result.price:.0f} {esc(result.currency)}</b>\n\n"
                    f"📍 Route : <b>{esc(result.origin)} ➜ {esc(result.destination)}</b>\n\n"
                    f"📅 Departure : {esc(result.departure_date)}"
                )

                if flight.trip_type == "round-trip":
                    text += f"\n\n🔁 Return : {esc(result.return_date)}"

                if result.booking_url:
                    text += f'\n\n<a href="{esc(result.booking_url)}">🔗 View Flight</a>'

                recommendation = AnalyticsService().recommendation_for_route(
                    result.origin, result.destination, result.price
                )

                if recommendation:
                    text += f"\n\n<b>{recommendation}</b>"

                await query.message.reply_text(
                    text=text,
                    reply_markup=main_menu(),
                )

    # ==========================
    # CHART (price history - ASCII sparkline + PNG line chart)
    # ==========================

    elif query.data.startswith("chart_"):

        flight_id = int(query.data.split("_")[1])
        flight = tracking.get_by_id(flight_id)

        if flight is None:

            await query.message.reply_text(
                "❌ That flight no longer exists.",
                reply_markup=main_menu(),
            )

        else:

            window_days = settings.analytics_window_days
            rows = tracking.route_history(flight, since_days=window_days)

            if len(rows) < 2:

                await query.message.reply_text(
                    "📉 Not enough price history yet for a chart "
                    "(need at least 2 checks).",
                    reply_markup=main_menu(),
                )

            else:

                prices = [row[0] for row in rows]
                # row[2] is checked_at ("YYYY-MM-DD HH:MM:SS" or
                # "YYYY-MM-DDTHH:MM:SS") - just the date portion reads
                # cleanly as an x-axis label.
                labels = [row[2][:10] for row in rows]

                spark = ascii_sparkline(prices)

                text = (
                    f"📉 <b>{esc(flight.origin)} ➜ {esc(flight.destination)}</b> — last {window_days}d\n\n"
                    f"{spark}\n\n"
                    f"Low {min(prices):.0f} · High {max(prices):.0f} · "
                    f"Latest <b>{prices[-1]:.0f} SAR</b>"
                )

                await query.message.reply_text(text=text)

                # matplotlib rendering is blocking CPU work - offload
                # to a worker thread so it can't stall the event loop
                # (same reasoning as fast_flights' get_flights() and
                # Twilio's client.messages.create()).
                png_bytes = await asyncio.to_thread(
                    render_price_chart_png,
                    prices=prices,
                    labels=labels,
                    title=f"{flight.origin} ➜ {flight.destination}",
                    target_price=flight.max_price,
                )

                await query.message.reply_photo(
                    photo=io.BytesIO(png_bytes),
                    reply_markup=main_menu(),
                )

    # ==========================
    # EDIT (handled by edit_flight_conversation in app.bot.conversations,
    # registered ahead of this generic handler)
    # ==========================

    # ==========================
    # DELETE (with confirmation)
    # ==========================

    elif query.data.startswith("delete_"):

        flight_id = int(query.data.split("_")[1])
        flight = tracking.get_by_id(flight_id)

        if flight is None:

            await query.message.reply_text(
                "❌ That flight no longer exists.",
                reply_markup=main_menu(),
            )

        else:

            confirm_keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ Yes, delete it",
                            callback_data=f"confirm_delete_{flight_id}",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "❌ Cancel",
                            callback_data="menu_list",
                        ),
                    ],
                ]
            )

            await query.message.reply_text(
                text=(
                    "🗑 Delete this flight?\n\n"
                    f"<b>{esc(flight.origin)} ➜ {esc(flight.destination)}</b>\n"
                    f"📅 {esc(flight.departure_date)} / 🔁 {esc(flight.return_date)}"
                ),
                reply_markup=confirm_keyboard,
            )

    elif query.data.startswith("confirm_delete_"):

        flight_id = int(query.data.split("_")[2])

        tracking.delete(flight_id)

        await query.message.reply_text(
            "✅ Flight deleted.",
            reply_markup=main_menu(),
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