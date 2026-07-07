"""Manual debug script - makes a REAL live Google Flights request via
fast_flights when run directly. Not a pytest test (moved out of
tests/ so pytest's default collection can't import and execute this
at collection time). Run with: python3 scripts/debug_fast_flights.py
"""

from fast_flights import *
from pprint import pprint

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
    trip="round-trip",
    seat="economy",
    passengers=Passengers(adults=1),
    currency="SAR",
)

results = get_flights(query)

print("Results:", len(results))

for i, r in enumerate(results):
    print("=" * 80)
    print(i)
    pprint(r.__dict__)