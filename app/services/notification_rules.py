from dataclasses import dataclass
from datetime import datetime

from app.config.settings import settings
from app.models.flight import Flight


@dataclass
class AlertDecision:
    should_notify: bool
    escalate: bool
    reason: str
    lowest_price_seen: float
    is_flash_deal: bool = False


def evaluate_alert(
    flight: Flight,
    price: float,
    now: datetime,
    route_avg_price: float | None = None,
) -> AlertDecision:
    """Decide whether a newly-observed price should trigger an alert.

    Global policy (Sprint 2 / Phase 1), applied the same way to every
    tracked flight:

    - Notify if the price meets the flight's target (existing behavior).
    - Notify if it's the lowest price ever seen for this flight, even if
      still above target - that's useful signal on its own.
    - Notify if the price dropped by at least
      settings.price_drop_threshold_pct since the last check.
    - Notify on a "flash deal": price is at least
      settings.flash_deal_drop_pct below the route's own historical
      average (route_avg_price, from AnalyticsService), even if it's
      neither a new all-time low nor a big drop since the last check -
      this catches a sudden cheap fare on a route that's normally
      volatile enough that today's price isn't a record.
    - Don't repeat an alert unless the price has moved by at least
      settings.dedup_tolerance_pct since the price we last actually
      notified on - a flight sitting under target (or bouncing by a
      dollar or two) shouldn't re-fire every single scheduled check.
    - Suppress (non-escalated) alerts during quiet hours.
    - A new lowest that beats the previous lowest by at least
      settings.escalation_drop_threshold_pct, or a flash deal, is
      "escalated": it bypasses quiet hours and gets a louder message.
    """

    previous_lowest = flight.lowest_price_seen
    is_new_lowest = previous_lowest is None or price < previous_lowest
    lowest_price_seen = price if is_new_lowest else previous_lowest

    meets_target = price <= flight.max_price

    drop_pct = 0.0

    if flight.last_price:
        drop_pct = (flight.last_price - price) / flight.last_price * 100

    meets_drop = (
        flight.last_price is not None
        and flight.last_price > 0
        and drop_pct >= settings.price_drop_threshold_pct
    )

    below_avg_pct = 0.0
    is_flash_deal = False

    if route_avg_price and route_avg_price > 0:
        below_avg_pct = (route_avg_price - price) / route_avg_price * 100
        is_flash_deal = below_avg_pct >= settings.flash_deal_drop_pct

    escalate_on_lowest = (
        is_new_lowest
        and previous_lowest is not None
        and previous_lowest > 0
        and price <= previous_lowest * (1 - settings.escalation_drop_threshold_pct / 100)
    )

    escalate = escalate_on_lowest or is_flash_deal

    should_notify = meets_target or is_new_lowest or meets_drop or is_flash_deal

    # Dedup: don't repeat an alert unless the price has moved enough
    # since the last one we actually notified on.
    if should_notify and flight.last_notified_price is not None and flight.last_notified_price > 0:

        change_pct = (
            abs(flight.last_notified_price - price) / flight.last_notified_price * 100
        )

        if change_pct < settings.dedup_tolerance_pct:
            should_notify = False

    # Quiet hours suppress everything except escalated alerts.
    if should_notify and not escalate and _in_quiet_hours(now):
        should_notify = False

    if is_flash_deal:
        reason = f"flash deal - {below_avg_pct:.0f}% below the route's average price"
    elif meets_target and is_new_lowest:
        reason = "target met and new lowest price"
    elif meets_target:
        reason = "target met"
    elif is_new_lowest:
        reason = "new lowest price seen"
    elif meets_drop:
        reason = f"price dropped {drop_pct:.0f}% since last check"
    else:
        reason = "no trigger"

    return AlertDecision(
        should_notify=should_notify,
        escalate=escalate,
        reason=reason,
        lowest_price_seen=lowest_price_seen,
        is_flash_deal=is_flash_deal,
    )


def _in_quiet_hours(now: datetime) -> bool:

    start = settings.quiet_hours_start
    end = settings.quiet_hours_end

    if start == end:
        return False  # quiet hours disabled

    hour = now.hour

    if start < end:
        return start <= hour < end

    # Window wraps past midnight, e.g. 22 -> 7.
    return hour >= start or hour < end
