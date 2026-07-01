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
            trip="round-trip",
            seat="economy",
            passengers=Passengers(adults=1),
            currency="SAR",
        )

        try:
            results = get_flights(query)

        except FlightsNotFound:
            return []

        output = []

        print("\n========== RAW FAST-FLIGHTS ==========")

        for item in results:

            print(
                f"Price={item.price} | Airline={', '.join(item.airlines)}"
            )

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
                    booking_url="",
                )
            )

        print("=====================================\n")

        output.sort(key=lambda x: x.price)

        return output