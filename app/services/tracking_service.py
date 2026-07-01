from app.database.database import (
    add_flight,
    get_all_flights,
    delete_flight,
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