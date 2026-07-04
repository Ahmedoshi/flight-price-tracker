from app.database.database import (
    add_flight,
    get_all_flights,
    delete_flight,
    save_price,
    get_last_price,
    get_price_history,
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
    ):

        # Normalize possibly comma-separated, mixed-case input like
        # "ruh, dmm" into a clean "RUH,DMM" for consistent storage.
        flight = Flight(
            origin=",".join(parse_codes(origin)),
            destination=",".join(parse_codes(destination)),
            departure_date=departure_date,
            return_date=return_date,
            max_price=max_price,
            date_flex_days=date_flex_days,
        )

        add_flight(flight)

    def list(self):

        return get_all_flights()

    def delete(self, flight_id: int):

        delete_flight(flight_id)

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

    def save_result(self, result):

        save_price(result)

    def history(self, limit: int = 20):

        return get_price_history(limit)