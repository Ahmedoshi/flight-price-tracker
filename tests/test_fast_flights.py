from fast_flights import (
    FlightQuery,
    Passengers,
    create_query,
    get_flights,
)

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

results = get_flights(query)

print(type(results))
print("Count:", len(results))

flight = results[0]

print(type(flight))
print(dir(flight))
print(vars(flight))