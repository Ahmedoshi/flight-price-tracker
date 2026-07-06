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
    trend: str  # "up" | "down" | "flat"
    trend_pct: float  # % change, second-half avg vs first-half avg (signed)
    best_booking_day: str | None  # weekday name with the lowest avg price
    best_departure_day: str | None  # weekday name (by departure date)


# Below this magnitude, a change in the first-half/second-half average
# is treated as noise rather than a real trend.
TREND_NOISE_THRESHOLD_PCT = 2.0


def _trend_from_prices(prices: list[float]) -> tuple[str, float]:
    """Trend across the whole window, not just the last two checks.

    Compares the average of the first half of the (chronologically
    ordered) prices against the average of the second half - more
    resistant to a single noisy reading than a last-two-points
    comparison, while still being simple enough to reason about.
    """

    if len(prices) < 2:
        return "flat", 0.0

    midpoint = len(prices) // 2
    first_half = prices[:midpoint] or prices[:1]
    second_half = prices[midpoint:]

    first_avg = sum(first_half) / len(first_half)
    second_avg = sum(second_half) / len(second_half)

    if first_avg <= 0:
        return "flat", 0.0

    change_pct = (second_avg - first_avg) / first_avg * 100

    if change_pct > TREND_NOISE_THRESHOLD_PCT:
        return "up", change_pct

    if change_pct < -TREND_NOISE_THRESHOLD_PCT:
        return "down", change_pct

    return "flat", change_pct


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

    trend, trend_pct = _trend_from_prices(prices)

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
    best_departure_day = _cheapest_day(departure_day_prices)

    return RouteStats(
        count=len(prices),
        min_price=minimum,
        max_price=maximum,
        avg_price=average,
        trend=trend,
        trend_pct=trend_pct,
        best_booking_day=best_booking_day,
        best_departure_day=best_departure_day,
    )


def _cheapest_day(day_prices: dict) -> str | None:

    if not day_prices:
        return None

    return min(day_prices, key=lambda day: sum(day_prices[day]) / len(day_prices[day]))


def _parse_timestamp(value: str) -> datetime | None:

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):

        try:
            return datetime.strptime(value, fmt)

        except ValueError:
            continue

    return None


TREND_EMOJI = {
    "up": "📈",
    "down": "📉",
    "flat": "➡️",
}
