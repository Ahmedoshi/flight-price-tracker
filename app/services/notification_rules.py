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
    is_monthly_low: bool = False
    is_rebound: bool = False
    triggered_rules: list[str] = None

    def __post_init__(self):
        if self.triggered_rules is None:
            self.triggered_rules = []


def evaluate_alert(
    flight: Flight,
    price: float,
    now: datetime,
    route_avg_price: float | None = None,
    monthly_low_price: float | None = None,
    price_before_last: float | None = None,
) -> AlertDecision:
    """Decide whether a newly-observed price should trigger an alert.

    Smart Alert Engine (Roadmap Phase 2) - five independent rules are
    checked every time, each able to trigger a notification on its own:

    1. New lowest ever - the cheapest this flight has ever been seen.
    2. Price drop - dropped by at least settings.price_drop_threshold_pct
       since the last check.
    3. Lowest this month - the cheapest in the last 30 days, even if
       not an all-time record (a route with a much cheaper blip many
       months ago shouldn't mask "this is a good price right now").
    4. Flash deal - at least settings.flash_deal_drop_pct below the
       route's own historical average (route_avg_price), even if
       neither a record low nor a big drop since the last check.
    5. Rebound - price rose by at least settings.rebound_min_change_pct
       and has now fallen back by at least that much - a sign the
       spike is over and it's worth booking before it climbs again.

    (Target-price-met is also checked, as the original/simplest rule.)

    Plus the existing policy layered on top of all of them:
    - Don't repeat an alert unless the price has moved by at least
      settings.dedup_tolerance_pct since the price we last actually
      notified on.
    - Suppress non-escalated alerts during quiet hours.
    - A new lowest that beats the previous lowest by at least
      settings.escalation_drop_threshold_pct, or a flash deal, is
      "escalated": bypasses quiet hours, gets a louder message.

    monthly_low_price and price_before_last must be looked up (via
    TrackingService/AnalyticsService) before this check's price is
    saved to price_history, or they'd include the very price being
    evaluated in their own baseline.
    """

    previous_lowest = flight.lowest_price_seen
    is_new_lowest = previous_lowest is None or price < previous_lowest
    lowest_price_seen = price if is_new_lowest else previous_lowest

    meets_target = price <= flight.max_price

    # Rule: price drop since the last check.
    drop_pct = 0.0

    if flight.last_price:
        drop_pct = (flight.last_price - price) / flight.last_price * 100

    meets_drop = (
        flight.last_price is not None
        and flight.last_price > 0
        and drop_pct >= settings.price_drop_threshold_pct
    )

    # Rule: flash deal (well below the route's own historical average).
    below_avg_pct = 0.0
    is_flash_deal = False

    if route_avg_price and route_avg_price > 0:
        below_avg_pct = (route_avg_price - price) / route_avg_price * 100
        is_flash_deal = below_avg_pct >= settings.flash_deal_drop_pct

    # Rule: lowest price in the last 30 days. Redundant (and skipped)
    # if it's already an all-time low - "new lowest ever" is strictly
    # the stronger claim.
    is_monthly_low = (
        not is_new_lowest
        and monthly_low_price is not None
        and monthly_low_price > 0
        and price <= monthly_low_price
    )

    # Rule: rebound - rose, then fell back by a comparable amount.
    increase_pct = 0.0
    decrease_pct = 0.0
    is_rebound = False

    if (
        price_before_last is not None
        and price_before_last > 0
        and flight.last_price is not None
        and flight.last_price > 0
    ):
        increase_pct = (flight.last_price - price_before_last) / price_before_last * 100
        decrease_pct = (flight.last_price - price) / flight.last_price * 100

        is_rebound = (
            increase_pct >= settings.rebound_min_change_pct
            and decrease_pct >= settings.rebound_min_change_pct
        )

    escalate_on_lowest = (
        is_new_lowest
        and previous_lowest is not None
        and previous_lowest > 0
        and price <= previous_lowest * (1 - settings.escalation_drop_threshold_pct / 100)
    )

    escalate = escalate_on_lowest or is_flash_deal

    should_notify = (
        meets_target
        or is_new_lowest
        or meets_drop
        or is_flash_deal
        or is_monthly_low
        or is_rebound
    )

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

    triggered_rules = []
    reasons = []

    if is_flash_deal:
        triggered_rules.append("flash_deal")
        reasons.append(f"flash deal - {below_avg_pct:.0f}% below the route's average price")

    if meets_target and is_new_lowest:
        triggered_rules += ["target_met", "new_lowest"]
        reasons.append("target met and new lowest price")
    elif meets_target:
        triggered_rules.append("target_met")
        reasons.append("target met")
    elif is_new_lowest:
        triggered_rules.append("new_lowest")
        reasons.append("new lowest price seen")

    if is_monthly_low:
        triggered_rules.append("monthly_low")
        reasons.append("lowest price in the last 30 days")

    if is_rebound:
        triggered_rules.append("rebound")
        reasons.append(
            f"price rebounded {decrease_pct:.0f}% after rising {increase_pct:.0f}% - "
            "the spike may be over"
        )

    if meets_drop and "target_met" not in triggered_rules and "new_lowest" not in triggered_rules:
        triggered_rules.append("price_drop")
        reasons.append(f"price dropped {drop_pct:.0f}% since last check")

    reason = " + ".join(reasons) if reasons else "no trigger"

    return AlertDecision(
        should_notify=should_notify,
        escalate=escalate,
        reason=reason,
        lowest_price_seen=lowest_price_seen,
        is_flash_deal=is_flash_deal,
        is_monthly_low=is_monthly_low,
        is_rebound=is_rebound,
        triggered_rules=triggered_rules,
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
