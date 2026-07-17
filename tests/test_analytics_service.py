"""Tests for the expanded analytics dashboard (Roadmap Phase 3)."""

import datetime

from app.models.flight import Flight
from app.services.analytics_service import AnalyticsService, _compute_stats, _parse_timestamp


def _seed_price_history(dbmod, prices, start=None):
    """Seeds price_history starting `start` (default: 40 days before
    "now", computed at call time rather than a hardcoded calendar
    date). Tests query with since_days=45, so a fixed calendar date
    (e.g. 2026-06-01) works today but silently falls out of that
    window as real time marches past it - this rots the test instead
    of catching real regressions. Computing relative to "now" keeps
    the test valid indefinitely."""

    if start is None:
        start = datetime.datetime.now() - datetime.timedelta(days=40)

    conn = dbmod.get_connection()

    for i, price in enumerate(prices):

        checked_at = (start + datetime.timedelta(days=i)).strftime("%Y-%m-%d %H:%M:%S")

        conn.execute(
            """
            INSERT INTO price_history
            (origin, destination, departure_date, return_date, airline, price, checked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("RUH", "LIS", "2026-09-30", "2026-10-20", "TestAir", price, checked_at),
        )

    conn.commit()
    conn.close()


def _flight():

    return Flight(
        origin="RUH",
        destination="LIS",
        departure_date="2026-09-30",
        return_date="2026-10-20",
        max_price=2000,
    )


def test_compute_stats_returns_none_with_no_history(temp_db):

    analytics = AnalyticsService()
    stats = analytics.compute_stats(_flight(), since_days=45)

    assert stats is None


def test_compute_stats_basic_aggregates(temp_db):

    prices = [2600, 2550, 2400, 2650, 2300, 2200, 2350, 2100, 2000, 2150, 1950, 1900, 2050, 1850]
    _seed_price_history(temp_db, prices)

    analytics = AnalyticsService()
    stats = analytics.compute_stats(_flight(), since_days=45)

    assert stats.count == len(prices)
    assert stats.min_price == min(prices)
    assert stats.max_price == max(prices)
    assert stats.avg_price == sum(prices) / len(prices)
    # median of a sorted 14-item list is the average of the two middle values
    assert stats.median_price > 0
    assert stats.volatility_pct > 0


def test_compute_stats_downward_trend_detected(temp_db):

    # Clearly higher first half, clearly lower second half.
    prices = [2600, 2550, 2400, 2650, 2300, 2200, 1350, 1100, 1000, 1150, 950, 900, 1050, 850]
    _seed_price_history(temp_db, prices)

    analytics = AnalyticsService()
    stats = analytics.compute_stats(_flight(), since_days=45)

    assert stats.trend == "down"
    assert stats.trend_pct < 0


def test_expected_price_reflects_recent_half_not_whole_window(temp_db):

    # First half much higher than second half - expected_price (recent
    # regime) should sit close to the second half, well below avg_price.
    first_half = [3000, 3000, 3000, 3000, 3000, 3000, 3000]
    second_half = [1000, 1000, 1000, 1000, 1000, 1000, 1000]
    _seed_price_history(temp_db, first_half + second_half)

    analytics = AnalyticsService()
    stats = analytics.compute_stats(_flight(), since_days=45)

    assert stats.expected_price == 1000
    assert stats.avg_price == 2000
    assert stats.expected_price < stats.avg_price


def test_best_and_worst_booking_day_differ(temp_db):

    # Mondays cheap, Fridays expensive - anchored to a Monday safely
    # in the past (relative to "now") rather than a hardcoded calendar
    # date, so this doesn't fall outside the since_days=45 window as
    # real time passes.
    conn = temp_db.get_connection()

    this_monday = datetime.datetime.now() - datetime.timedelta(
        days=datetime.datetime.now().weekday()
    )
    base_monday = this_monday - datetime.timedelta(days=14)

    rows = [
        ((base_monday).strftime("%Y-%m-%d") + " 10:00:00", 1000),  # Monday
        ((base_monday + datetime.timedelta(days=7)).strftime("%Y-%m-%d") + " 10:00:00", 1000),  # Monday
        ((base_monday + datetime.timedelta(days=4)).strftime("%Y-%m-%d") + " 10:00:00", 3000),  # Friday
        ((base_monday + datetime.timedelta(days=11)).strftime("%Y-%m-%d") + " 10:00:00", 3000),  # Friday
    ]

    for checked_at, price in rows:

        conn.execute(
            """
            INSERT INTO price_history
            (origin, destination, departure_date, return_date, airline, price, checked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("RUH", "LIS", "2026-09-30", "2026-10-20", "TestAir", price, checked_at),
        )

    conn.commit()
    conn.close()

    analytics = AnalyticsService()
    stats = analytics.compute_stats(_flight(), since_days=45)

    assert stats.best_booking_day == "Monday"
    assert stats.worst_booking_day == "Friday"


def test_recommendation_says_buy_now_at_the_lowest_price(temp_db):

    prices = [2600, 2550, 2400, 2650, 2300, 2200, 2350, 2100, 2000, 2150, 1950, 1900, 2050, 1850]
    _seed_price_history(temp_db, prices)

    analytics = AnalyticsService()
    stats = analytics.compute_stats(_flight(), since_days=45)

    recommendation = analytics.recommendation(min(prices), stats)

    assert "lowest price" in recommendation.lower()
    assert "buy now" in recommendation.lower()


def test_recommendation_handles_insufficient_history(temp_db):

    analytics = AnalyticsService()
    recommendation = analytics.recommendation(2000, stats=None)

    assert "not enough" in recommendation.lower()


def test_parse_timestamp_accepts_native_datetime():
    """Regression test: Postgres (Roadmap Phase 5) decodes the
    checked_at TIMESTAMP column into a native datetime.datetime via
    psycopg2, unlike SQLite which always hands back a plain string.
    _parse_timestamp() must accept both without raising."""

    value = datetime.datetime(2026, 7, 6, 14, 46, 21)

    assert _parse_timestamp(value) == value
    assert _parse_timestamp("2026-07-06 14:46:21") == value


def test_compute_stats_handles_postgres_style_datetime_rows():
    """Regression test for the production crash: _compute_stats() (via
    analytics_screen) threw TypeError: strptime() argument 1 must be
    str, not datetime.datetime the moment checked_at rows came back as
    real datetimes instead of strings - simulates exactly that shape
    without needing a live Postgres connection."""

    rows = [
        (2600.0, "2026-09-30", datetime.datetime(2026, 7, 1, 10, 0, 0)),
        (2400.0, "2026-09-30", datetime.datetime(2026, 7, 2, 10, 0, 0)),
        (2200.0, "2026-09-30", datetime.datetime(2026, 7, 3, 10, 0, 0)),
    ]

    stats = _compute_stats(rows)

    assert stats is not None
    assert stats.count == 3
    assert stats.min_price == 2200.0
    assert stats.best_booking_day is not None
