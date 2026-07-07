"""Tests for the Smart Alert Engine (Roadmap Phase 2) - the five
independent rule types, plus dedup tolerance and quiet-hours policy
layered on top of them.
"""

from datetime import datetime

from app.config.settings import settings
from app.models.flight import Flight
from app.services.notification_rules import evaluate_alert

NOW = datetime(2026, 7, 6, 12, 0, 0)


def _flight(**overrides):
    """A Flight with a target price that's deliberately unreachable
    unless a test overrides max_price - keeps "target met" from
    silently dominating every other rule's test."""

    defaults = dict(
        origin="RUH",
        destination="LIS",
        departure_date="2026-09-30",
        return_date="2026-10-20",
        max_price=1,
        last_notified_price=None,
    )
    defaults.update(overrides)
    return Flight(**defaults)


def test_new_lowest_ever_triggers():

    flight = _flight(lowest_price_seen=2000, last_price=2000)
    decision = evaluate_alert(flight, 1800, NOW)

    assert decision.should_notify
    assert "new_lowest" in decision.triggered_rules
    assert decision.lowest_price_seen == 1800


def test_price_drop_triggers_without_being_a_new_low():

    flight = _flight(lowest_price_seen=1500, last_price=2000)
    decision = evaluate_alert(flight, 1750, NOW)  # 12.5% drop, still above the 1500 all-time low

    assert decision.should_notify
    assert "price_drop" in decision.triggered_rules
    assert "new_lowest" not in decision.triggered_rules


def test_price_drop_below_threshold_does_not_trigger():

    flight = _flight(lowest_price_seen=1500, last_price=2000)
    decision = evaluate_alert(flight, 1950, NOW)  # only 2.5% drop, below default 10% threshold

    assert not decision.should_notify


def test_monthly_low_triggers_when_not_all_time_low():

    flight = _flight(lowest_price_seen=1000, last_price=1900)
    decision = evaluate_alert(flight, 1850, NOW, monthly_low_price=1900)

    assert decision.should_notify
    assert "monthly_low" in decision.triggered_rules
    assert "new_lowest" not in decision.triggered_rules  # 1850 > all-time low of 1000


def test_monthly_low_skipped_when_also_all_time_low():
    """An all-time low is the strictly stronger claim - the monthly_low
    rule shouldn't also fire and produce a redundant reason."""

    flight = _flight(lowest_price_seen=2000, last_price=2000)
    decision = evaluate_alert(flight, 1800, NOW, monthly_low_price=1900)

    assert "new_lowest" in decision.triggered_rules
    assert "monthly_low" not in decision.triggered_rules


def test_flash_deal_triggers_and_escalates():

    flight = _flight(lowest_price_seen=1000, last_price=2000)
    decision = evaluate_alert(flight, 1490, NOW, route_avg_price=2000)  # 25.5% below average

    assert decision.should_notify
    assert "flash_deal" in decision.triggered_rules
    assert decision.is_flash_deal
    assert decision.escalate


def test_rebound_triggers_after_rise_then_fall():

    flight = _flight(lowest_price_seen=1000, last_price=2200)
    decision = evaluate_alert(flight, 2000, NOW, price_before_last=1900)
    # rose 1900 -> 2200 (+15.8%), then fell 2200 -> 2000 (-9.1%)

    assert decision.should_notify
    assert "rebound" in decision.triggered_rules
    assert decision.is_rebound


def test_rebound_does_not_trigger_below_change_threshold():

    flight = _flight(lowest_price_seen=1000, last_price=2050)
    decision = evaluate_alert(flight, 2020, NOW, price_before_last=2000)
    # rose 2000 -> 2050 (+2.5%), fell 2050 -> 2020 (-1.5%) - both under
    # the default 3% rebound_min_change_pct

    assert not decision.is_rebound


def test_no_rule_fires_on_a_flat_uninteresting_price():

    flight = _flight(lowest_price_seen=1000, last_price=1000)
    decision = evaluate_alert(flight, 1000, NOW)

    assert not decision.should_notify
    assert decision.reason == "no trigger"


def test_multiple_rules_combine_in_the_reason_text():

    flight = _flight(lowest_price_seen=1000, last_price=2000)
    decision = evaluate_alert(flight, 1490, NOW, route_avg_price=2000)
    # both flash_deal (25.5% below avg) and price_drop (25.5% since last check) are true

    assert "flash_deal" in decision.triggered_rules
    assert "price_drop" in decision.triggered_rules
    assert "+" in decision.reason


def test_dedup_suppresses_repeat_alert_within_tolerance():

    flight = _flight(lowest_price_seen=1000, last_price=1000, last_notified_price=1005, max_price=99999)
    decision = evaluate_alert(flight, 1000, NOW)  # target met, but only 0.5% moved since last notify (< 3% tolerance)

    assert not decision.should_notify


def test_dedup_allows_alert_once_price_moves_enough():

    flight = _flight(lowest_price_seen=1000, last_price=1000, last_notified_price=1200, max_price=99999)
    decision = evaluate_alert(flight, 1000, NOW)  # ~16.7% moved since last notify - clears the 3% tolerance

    assert decision.should_notify


def test_quiet_hours_suppress_non_escalated_alerts():

    settings.quiet_hours_start = 22
    settings.quiet_hours_end = 7
    quiet_now = datetime(2026, 7, 6, 23, 0, 0)  # 23:00 falls in the 22->7 window

    flight = _flight(lowest_price_seen=1500, last_price=2000)
    decision = evaluate_alert(flight, 1750, quiet_now)  # price_drop only, non-escalated

    assert not decision.should_notify


def test_quiet_hours_do_not_suppress_escalated_alerts():

    settings.quiet_hours_start = 22
    settings.quiet_hours_end = 7
    quiet_now = datetime(2026, 7, 6, 23, 0, 0)

    flight = _flight(lowest_price_seen=1000, last_price=2000)
    decision = evaluate_alert(flight, 1490, quiet_now, route_avg_price=2000)  # flash deal - escalated

    assert decision.should_notify
