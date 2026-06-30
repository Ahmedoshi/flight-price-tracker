from dataclasses import dataclass


@dataclass
class FlightResult:
    provider: str
    airline: str
    price: float
    currency: str
    origin: str
    destination: str
    departure_date: str
    return_date: str
    booking_url: str