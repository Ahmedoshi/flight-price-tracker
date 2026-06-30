from app.database.database import (
    initialize_database,
    add_flight,
    get_all_flights,
)

from app.models.flight import Flight


initialize_database()

flight = Flight(
    origin="RUH",
    destination="LIS",
    departure_date="2026-09-01",
    return_date="2026-09-15",
    max_price=2200,
)

add_flight(flight)

print(get_all_flights())