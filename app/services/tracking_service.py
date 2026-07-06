from __future__ import annotations

from app.database.database import (
    add_flight,
    get_all_flights,
    delete_flight,
    save_price,
    get_last_price,
    get_price_history,
    get_recent_prices,
    get_route_price_history,
    update_flight,
    update_flight_tracking,
)

from app.models.flight import Flight
from app.utils.airports import parse_codes


class TrackingService:

    def add(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        max_price: float,
        date_flex_days: int = 0,
        trip_type: str = "round-trip",
        cabin_class: str = "economy",
        max_stops: int | None = None,
        legs: list[dict] | None = None,
    ):

        # Normalize possibly comma-separated, mixed-case input like
        # "ruh, dmm" into a clean "RUH,DMM" for consistent storage.
        # Multi-city legs are already resolved single airport codes, so
        # they're stored as-is rather than run through parse_codes().
        flight = Flight(
            origin=",".join(parse_codes(origin)) if legs is None else origin,
            destination=",".join(parse_codes(destination)) if legs is None else destination,
            departure_date=departure_date,
            return_date=return_date,
            max_price=max_price,
            date_flex_days=date_flex_days,
            trip_type=trip_type,
            cabin_class=cabin_class,
            max_stops=max_stops,
            legs=legs,
        )

        add_flight(flight)

    def list(self):

        return get_all_flights()

    def delete(self, flight_id: int):

        delete_flight(flight_id)

    def update(
        self,
        flight_id: int,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        max_price: float,
        date_flex_days: int = 0,
        trip_type: str = "round-trip",
        cabin_class: str = "economy",
        max_stops: int | None = None,
        legs: list[dict] | None = None,
    ):

        flight = Flight(
            id=flight_id,
            origin=",".join(parse_codes(origin)) if legs is None else origin,
            destination=",".join(parse_codes(destination)) if legs is None else destination,
            departure_date=departure_date,
            return_date=return_date,
            max_price=max_price,
            date_flex_days=date_flex_days,
            trip_type=trip_type,
            cabin_class=cabin_class,
            max_stops=max_stops,
            legs=legs,
        )

        update_flight(flight)

    def update_tracking(
        self,
        flight_id: int,
        last_price: float,
        last_airline: str,
        lowest_price_seen: float,
        last_notified_price: float | None,
        last_checked_at: str,
    ):

        update_flight_tracking(
            flight_id=flight_id,
            last_price=last_price,
            last_airline=last_airline,
            lowest_price_seen=lowest_price_seen,
            last_notified_price=last_notified_price,
            last_checked_at=last_checked_at,
        )

    def get_by_position(self, position: int) -> Flight | None:
        """Resolve a 1-based position (as shown in /list) to a Flight.

        The database id is not stable against the displayed position
        once flights have been added/deleted out of order, so lookups
        by position must go through here instead of using the id
        directly.
        """

        flights = get_all_flights()

        if position < 1 or position > len(flights):
            return None

        return flights[position - 1]

    def get_by_id(self, flight_id: int) -> Flight | None:

        for flight in get_all_flights():
            if flight.id == flight_id:
                return flight

        return None

    def last_price(self, flight: Flight):

        return get_last_price(flight)

    def recent_prices(self, flight: Flight, limit: int = 3) -> list[float]:
        """Most-recent-first prices for the rebound alert rule. Call
        before save_result() for the current check - see
        get_recent_prices()'s docstring."""

        return get_recent_prices(flight, limit=limit)

    def save_result(self, result):

        save_price(result)

    def history(self, limit: int = 20):

        return get_price_history(limit)

    def route_history(self, flight: Flight, since_days: int | None = None):

        return get_route_price_history(
            origins=parse_codes(flight.origin),
            destinations=parse_codes(flight.destination),
            since_days=since_days,
        )