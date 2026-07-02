from app.database.database import (
    add_flight,
    get_all_flights,
    delete_flight,
    save_price,
    get_last_price,
    get_price_history,
)

from app.models.flight import Flight


class TrackingService:

    def add(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        max_price: float,
    ):

        flight = Flight(
            origin=origin.upper(),
            destination=destination.upper(),
            departure_date=departure_date,
            return_date=return_date,
            max_price=max_price,
        )

        add_flight(flight)

    def list(self):

        return get_all_flights()

    def delete(self, index: int):

        delete_flight(index)

    def last_price(self, flight: Flight):

        return get_last_price(flight)

    def save_result(self, result):

        save_price(result)

    def history(self, limit: int = 20):

        return get_price_history(limit)