from dataclasses import dataclass


@dataclass
class Flight:
    origin: str
    destination: str
    departure_date: str
    return_date: str
    max_price: float = 999999.0