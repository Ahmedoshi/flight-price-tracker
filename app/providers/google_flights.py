import asyncio

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
from app.providers.google_url import GoogleFlightsURLBuilder


class GoogleFlightsProvider(BaseProvider):

    async def search(self, flight: Flight) -> list[FlightResult]:

        if flight.trip_type == "multi-city":

            if not flight.legs or len(flight.legs) < 2:
                return []

            flight_legs = [
                FlightQuery(
                    date=leg["date"],
                    from_airport=leg["origin"],
                    to_airport=leg["destination"],
                )
                for leg in flight.legs
            ]

        else:

            flight_legs = [
                FlightQuery(
                    date=flight.departure_date,
                    from_airport=flight.origin,
                    to_airport=flight.destination,
                ),
            ]

            if flight.trip_type == "round-trip":

                flight_legs.append(
                    FlightQuery(
                        date=flight.return_date,
                        from_airport=flight.destination,
                        to_airport=flight.origin,
                    )
                )

        query = create_query(
            flights=flight_legs,
            trip=flight.trip_type,
            seat=flight.cabin_class,
            passengers=Passengers(adults=1),
            currency="SAR",
            max_stops=flight.max_stops,
        )

        try:
            # get_flights() is a blocking/synchronous call (it drives a
            # headless browser under the hood). Calling it directly here
            # would freeze the asyncio event loop for the whole duration
            # of the scrape - including the Telegram bot's long-poll
            # connection, which is what was causing the bot to lose its
            # getUpdates connection and crash with "Conflict: terminated
            # by other getUpdates request". Running it in a worker thread
            # keeps the event loop free.
            results = await asyncio.to_thread(get_flights, query)

        except FlightsNotFound:
            return []

        output = []

        if flight.trip_type == "multi-city":
            # The URL builder only understands a single origin/destination
            # pair, so there's no clean deep link for a multi-leg
            # itinerary yet - leave it blank rather than show a wrong one.
            booking_url = ""
        else:
            booking_url = GoogleFlightsURLBuilder.build(
                origin=flight.origin,
                destination=flight.destination,
                departure=flight.departure_date,
                return_date=flight.return_date,
            )

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
                    booking_url=booking_url,
                )
            )

        print("=====================================\n")

        output.sort(key=lambda x: x.price)

        return output