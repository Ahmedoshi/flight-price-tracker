"""Tests for price history charts (Roadmap Phase 4)."""

from app.services.chart_service import ascii_sparkline, render_price_chart_png

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


def test_sparkline_empty_for_fewer_than_two_points():

    assert ascii_sparkline([]) == ""
    assert ascii_sparkline([100]) == ""


def test_sparkline_length_matches_input():

    prices = [2600, 2550, 2400, 2650, 2300, 2200, 1850]
    spark = ascii_sparkline(prices)

    assert len(spark) == len(prices)


def test_sparkline_flat_line_uses_lowest_bar_for_every_point():

    spark = ascii_sparkline([100, 100, 100])

    assert spark == "▁▁▁"


def test_sparkline_lowest_and_highest_use_extreme_bars():

    prices = [100, 500, 100]
    spark = ascii_sparkline(prices)

    assert spark[0] == "▁"
    assert spark[1] == "█"
    assert spark[2] == "▁"


def test_render_price_chart_png_produces_a_valid_png():

    prices = [2600, 2550, 2400, 2650, 2300, 2200, 1850]
    labels = [f"2026-06-{i + 1:02d}" for i in range(len(prices))]

    png_bytes = render_price_chart_png(prices, labels, title="RUH -> LIS", target_price=2000)

    assert png_bytes[:8] == PNG_HEADER
    assert len(png_bytes) > 1000  # sanity check it's a real image, not a stub


def test_render_price_chart_png_works_without_a_target():

    prices = [2600, 2550, 2400]
    labels = ["2026-06-01", "2026-06-02", "2026-06-03"]

    png_bytes = render_price_chart_png(prices, labels, title="RUH -> LIS", target_price=None)

    assert png_bytes[:8] == PNG_HEADER
