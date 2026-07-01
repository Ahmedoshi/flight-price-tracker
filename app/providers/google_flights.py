from fast_flights import (
    FlightQuery,
    Passengers,
    create_query,
    get_flights,
    FlightsNotFound,
)

from app.models.flight import Flight
from app.models.flight_result import FlightResult
from app.providers.base_provider import BaseProvider


class GoogleFlightsProvider(BaseProvider):

    async def search(self, flight: Flight) -> list[FlightResult]:

        query = create_query(
            flights=[
                FlightQuery(
                    date=flight.departure_date,
                    from_airport=flight.origin,
                    to_airport=flight.destination,
                ),
                FlightQuery(
                    date=flight.return_date,
                    from_airport=flight.destination,
                    to_airport=flight.origin,
                ),
            ],
            seat="economy",
            passengers=Passengers(adults=1),
        )

        try:
            results = get_flights(query)

        except FlightsNotFound:
            return []

        output = []

        for item in results:

            output.append(
                FlightResult(
                    provider="Google Flights",
                    airline=", ".join(item.airlines),
                    price=float(item.price),
                    currency="SAR",
                    origin=flight.origin,
                    destination=flight.destination,
                    departure_date=flight.departure_date,
                    return_date=flight.return_date,
                )
            )

        return output