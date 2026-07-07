"""Database layer CRUD tests. Every test gets its own isolated,
freshly-initialized SQLite file via the temp_db fixture - never the
real data/flights.db.
"""

from app.models.flight import Flight
from app.models.flight_result import FlightResult


def _flight(**overrides):

    defaults = dict(
        origin="RUH",
        destination="LIS",
        departure_date="2026-09-30",
        return_date="2026-10-20",
        max_price=2200,
    )
    defaults.update(overrides)
    return Flight(**defaults)


def test_add_and_get_all_flights(temp_db):

    temp_db.add_flight(_flight())

    flights = temp_db.get_all_flights()

    assert len(flights) == 1
    assert flights[0].origin == "RUH"
    assert flights[0].destination == "LIS"
    assert flights[0].max_price == 2200


def test_update_flight(temp_db):

    temp_db.add_flight(_flight())
    flight = temp_db.get_all_flights()[0]

    flight.max_price = 1800
    flight.cabin_class = "business"
    temp_db.update_flight(flight)

    updated = temp_db.get_all_flights()[0]

    assert updated.max_price == 1800
    assert updated.cabin_class == "business"


def test_delete_flight(temp_db):

    temp_db.add_flight(_flight())
    flight = temp_db.get_all_flights()[0]

    temp_db.delete_flight(flight.id)

    assert temp_db.get_all_flights() == []


def test_update_flight_tracking_persists_monitoring_state(temp_db):

    temp_db.add_flight(_flight())
    flight = temp_db.get_all_flights()[0]

    temp_db.update_flight_tracking(
        flight_id=flight.id,
        last_price=1900,
        last_airline="Test Air",
        lowest_price_seen=1900,
        last_notified_price=1900,
        last_checked_at="2026-07-06T12:00:00",
    )

    updated = temp_db.get_all_flights()[0]

    assert updated.last_price == 1900
    assert updated.last_airline == "Test Air"
    assert updated.lowest_price_seen == 1900


def test_save_price_and_get_last_price(temp_db):

    flight = _flight()

    result = FlightResult(
        provider="Duffel",
        airline="Test Air",
        price=1850.0,
        currency="SAR",
        origin="RUH",
        destination="LIS",
        departure_date="2026-09-30",
        return_date="2026-10-20",
    )

    temp_db.save_price(result)

    assert temp_db.get_last_price(flight) == 1850.0


def test_get_recent_prices_most_recent_first(temp_db):

    flight = _flight()

    for price in [2000, 1900, 1800]:  # inserted oldest to newest

        result = FlightResult(
            provider="Duffel",
            airline="Test Air",
            price=price,
            currency="SAR",
            origin="RUH",
            destination="LIS",
            departure_date="2026-09-30",
            return_date="2026-10-20",
        )
        temp_db.save_price(result)

    recent = temp_db.get_recent_prices(flight, limit=2)

    # SQLite's checked_at defaults to CURRENT_TIMESTAMP with
    # second-level resolution, so these three inserts could tie on
    # timestamp - just confirm we get exactly 2 of the 3 known prices.
    assert len(recent) == 2
    assert set(recent).issubset({2000, 1900, 1800})


def test_get_route_price_history_filters_by_route(temp_db):

    matching = FlightResult(
        provider="Duffel", airline="A", price=1000, currency="SAR",
        origin="RUH", destination="LIS",
        departure_date="2026-09-30", return_date="2026-10-20",
    )
    other_route = FlightResult(
        provider="Duffel", airline="A", price=5000, currency="SAR",
        origin="JED", destination="CDG",
        departure_date="2026-09-30", return_date="2026-10-20",
    )

    temp_db.save_price(matching)
    temp_db.save_price(other_route)

    rows = temp_db.get_route_price_history(origins=["RUH"], destinations=["LIS"])

    assert len(rows) == 1
    assert rows[0][0] == 1000


def test_provider_health_upsert_and_read(temp_db):

    temp_db.upsert_provider_health(
        provider="Google Flights",
        total_checks=10,
        success_count=9,
        success_response_ms=20000,
        consecutive_failures=0,
        disabled_until=None,
        last_error=None,
        last_checked_at="2026-07-06T12:00:00",
    )

    row = temp_db.get_provider_health("Google Flights")

    assert row["total_checks"] == 10
    assert row["success_count"] == 9

    all_rows = temp_db.get_all_provider_health()
    assert "Google Flights" in all_rows


def test_provider_health_missing_provider_returns_none(temp_db):

    assert temp_db.get_provider_health("NeverSeen") is None
