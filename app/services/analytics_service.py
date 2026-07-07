import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from app.config.settings import settings
from app.models.flight import Flight
from app.services.tracking_service import TrackingService


@dataclass
class RouteStats:
    count: int
    min_price: float
    max_price: float
    avg_price: float
    median_price: float
    volatility_pct: float  # stdev as a % of the average - how much prices bounce around
    trend: str  # "up" | "down" | "flat"
    trend_pct: float  # % change, second-half avg vs first-half avg (signed)
    expected_price: float  # recent-regime average (second half of window) - a forward-looking estimate, distinct from avg_price which covers the whole window
    best_booking_day: str | None  # weekday name with the lowest avg price
    worst_booking_day: str | None  # weekday name with the highest avg price
    best_departure_day: str | None  # weekday name (by departure date)


# Below this magnitude, a change in the first-half/second-half average
# is treated as noise rather than a real trend.
TREND_NOISE_THRESHOLD_PCT = 2.0


def _trend_from_prices(prices: list[float]) -> tuple[str, float, float]:
    """Trend across the whole window, not just the last two checks.

    Compares the average of the first half of the (chronologically
    ordered) prices against the average of the second half - more
    resistant to a single noisy reading than a last-two-points
    comparison, while still being simple enough to reason about.

    Also returns the second-half average itself, used as
    RouteStats.expected_price - a "what to expect right now" estimate
    that reflects the recent regime rather than the whole window
    (which may include older, less-relevant prices).
    """

    if len(prices) < 2:
        return "flat", 0.0, prices[0] if prices else 0.0

    midpoint = len(prices) // 2
    first_half = prices[:midpoint] or prices[:1]
    second_half = prices[midpoint:]

    first_avg = sum(first_half) / len(first_half)
    second_avg = sum(second_half) / len(second_half)

    if first_avg <= 0:
        return "flat", 0.0, second_avg

    change_pct = (second_avg - first_avg) / first_avg * 100

    if change_pct > TREND_NOISE_THRESHOLD_PCT:
        return "up", change_pct, second_avg

    if change_pct < -TREND_NOISE_THRESHOLD_PCT:
        return "down", change_pct, second_avg

    return "flat", change_pct, second_avg


class AnalyticsService:

    def __init__(self):
        self.tracking = TrackingService()

    def compute_stats(
        self,
        flight: Flight,
        since_days: int | None = None,
    ) -> RouteStats | None:

        rows = self.tracking.route_history(flight, since_days=since_days)

        return _compute_stats(rows)

    def recommendation_for_route(
        self,
        origin: str,
        destination: str,
        current_price: float,
        since_days: int | None = None,
    ) -> str | None:
        """Convenience wrapper for one-off /check-style lookups that
        don't have a persisted Flight record - builds stats straight
        from origin/destination strings. Returns None if there isn't
        enough history yet to say anything (silently skips rather than
        showing a "not enough data" message every time)."""

        since_days = since_days or settings.analytics_window_days

        temp_flight = Flight(
            origin=origin,
            destination=destination,
            departure_date="",
            return_date="",
        )

        stats = self.compute_stats(temp_flight, since_days=since_days)

        if stats is None or stats.count < 2:
            return None

        return self.recommendation(current_price, stats, since_days)

    def recommendation(
        self,
        current_price: float,
        stats: RouteStats | None,
        window_days: int | None = None,
    ) -> str:

        window_days = window_days or settings.analytics_window_days

        if stats is None or stats.count < 2:
            return "⚪ Not enough price history yet for a recommendation."

        if current_price <= stats.min_price:
            return (
                f"🟢 This is the lowest price seen in the last {window_days} days. "
                "Recommended: buy now."
            )

        # Combine trend direction/strength with where the price sits
        # relative to the recent low, rather than just the average -
        # "falling but still expensive" and "falling and already cheap"
        # deserve different advice.
        near_low = current_price <= stats.min_price * 1.05

        if stats.trend == "down":

            if near_low:
                return (
                    f"🟢 Prices are trending down ({abs(stats.trend_pct):.0f}% over "
                    f"the last {window_days} days) and you're already close to the "
                    "recent low. Good time to buy - it could dip a little further, "
                    "but not by much."
                )

            return (
                f"🟡 Prices are trending down ({abs(stats.trend_pct):.0f}% over the "
                f"last {window_days} days). Worth waiting a bit longer if your dates "
                "are flexible."
            )

        if stats.trend == "up":
            return (
                f"🔴 Prices are trending up ({stats.trend_pct:.0f}% over the last "
                f"{window_days} days). Booking soon is safer than waiting."
            )

        if current_price <= stats.avg_price * 0.95:
            return "🟡 Below the recent average — a reasonable time to book."

        if current_price >= stats.avg_price * 1.10:
            return "🔴 Above the recent average — you may want to wait."

        return (
            "⚪ Around the recent average price with no clear trend — "
            "no strong signal either way."
        )


def _compute_stats(rows) -> RouteStats | None:

    if not rows:
        return None

    prices = [row[0] for row in rows]

    minimum = min(prices)
    maximum = max(prices)
    average = sum(prices) / len(prices)
    median = statistics.median(prices)

    # Volatility as a % of the average, rather than a raw currency
    # figure - "prices bounce around by about 12%" reads the same
    # regardless of the route's price level. pstdev (population stdev)
    # since this is the complete set of observed prices in the window,
    # not a sample standing in for a larger population.
    stdev = statistics.pstdev(prices) if len(prices) > 1 else 0.0
    volatility_pct = (stdev / average * 100) if average > 0 else 0.0

    trend, trend_pct, expected_price = _trend_from_prices(prices)

    booking_day_prices = defaultdict(list)
    departure_day_prices = defaultdict(list)

    for price, departure_date, checked_at in rows:

        checked_dt = _parse_timestamp(checked_at)

        if checked_dt:
            booking_day_prices[checked_dt.strftime("%A")].append(price)

        try:
            departure_dt = datetime.strptime(departure_date, "%Y-%m-%d")
            departure_day_prices[departure_dt.strftime("%A")].append(price)

        except ValueError:
            pass

    best_booking_day = _cheapest_day(booking_day_prices)
    worst_booking_day = _priciest_day(booking_day_prices)
    best_departure_day = _cheapest_day(departure_day_prices)

    return RouteStats(
        count=len(prices),
        min_price=minimum,
        max_price=maximum,
        avg_price=average,
        median_price=median,
        volatility_pct=volatility_pct,
        trend=trend,
        trend_pct=trend_pct,
        expected_price=expected_price,
        best_booking_day=best_booking_day,
        worst_booking_day=worst_booking_day,
        best_departure_day=best_departure_day,
    )


def _cheapest_day(day_prices: dict) -> str | None:

    if not day_prices:
        return None

    return min(day_prices, key=lambda day: sum(day_prices[day]) / len(day_prices[day]))


def _priciest_day(day_prices: dict) -> str | None:

    if not day_prices:
        return None

    return max(day_prices, key=lambda day: sum(day_prices[day]) / len(day_prices[day]))


def _parse_timestamp(value) -> datetime | None:
    """Parse a price_history.checked_at value into a datetime.

    SQLite always hands this column back as a plain string, but
    Postgres (Roadmap Phase 5) decodes its TIMESTAMP column straight
    into a native datetime.datetime via psycopg2 - so this needs to
    accept both, not just strings.
    """

    if isinstance(value, datetime):
        return value

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):

        try:
            return datetime.strptime(value, fmt)

        except (TypeError, ValueError):
            continue

    return None


TREND_EMOJI = {
    "up": "📈",
    "down": "📉",
    "flat": "➡️",
}
