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
    best_booking_day: str | None  # weekday name with the lowest avg price
    best_departure_day: str | None  # weekday name (by departure date)


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

        if current_price <= stats.avg_price * 0.95:
            return "🟡 Below the recent average — a reasonable time to book."

        if current_price >= stats.avg_price * 1.10:
            return "🔴 Above the recent average — you may want to wait."

        return "⚪ Around the recent average price — no strong signal either way."


def _compute_stats(rows) -> RouteStats | None:

    if not rows:
        return None

    prices = [row[0] for row in rows]

    minimum = min(prices)
    maximum = max(prices)
    average = sum(prices) / len(prices)

    trend = "flat"

    if len(prices) >= 2:

        if prices[-1] < prices[-2]:
            trend = "down"
        elif prices[-1] > prices[-2]:
            trend = "up"

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
