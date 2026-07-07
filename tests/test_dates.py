"""Tests for app.utils.dates, notably format_checked_at() - added
alongside the fix for a production crash where Postgres (Roadmap Phase
5) hands back price_history.checked_at as a native datetime.datetime
instead of the plain string SQLite always returned.
"""

from datetime import datetime

from app.utils.dates import format_checked_at


def test_format_checked_at_accepts_plain_string():

    assert format_checked_at("2026-07-06 14:46:21") == "2026-07-06 14:46:21"


def test_format_checked_at_accepts_native_datetime():

    value = datetime(2026, 7, 6, 14, 46, 21)

    assert format_checked_at(value) == "2026-07-06 14:46:21"


def test_format_checked_at_truncates_to_requested_length():

    value = datetime(2026, 7, 6, 14, 46, 21)

    assert format_checked_at(value, length=10) == "2026-07-06"
    assert format_checked_at("2026-07-06 14:46:21", length=10) == "2026-07-06"
