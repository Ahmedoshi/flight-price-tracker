from fast_flights import (
    FlightQuery,
    Passengers,
    create_query,
    get_flights,
    FlightsNotFound,
)

print("Searching Google Flights...")

query = create_query(
    flights=[
        FlightQuery(
            date="2026-09-01",
            from_airport="RUH",
            to_airport="LIS",
        ),
        FlightQuery(
            date="2026-09-15",
            from_airport="LIS",
            to_airport="RUH",
        ),
    ],
    seat="economy",
    passengers=Passengers(adults=1),
)

try:
    results = get_flights(query)

    print(f"\nFlights found: {len(results)}\n")

    for i, flight in enumerate(results[:5], start=1):
        print("=" * 60)
        print(f"Flight #{i}")

        if hasattr(flight, "price"):
            print("Price:", flight.price)

        if hasattr(flight, "airlines"):
            print("Airline:", flight.airlines)

        if hasattr(flight, "departure"):
            print("Departure:", flight.departure)

        if hasattr(flight, "arrival"):
            print("Arrival:", flight.arrival)

        if hasattr(flight, "duration"):
            print("Duration:", flight.duration)

        if hasattr(flight, "stops"):
            print("Stops:", flight.stops)

except FlightsNotFound:
    print("No flights found.")

except Exception as e:
    print(type(e).__name__)
    print(e)