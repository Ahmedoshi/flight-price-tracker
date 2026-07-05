from dataclasses import dataclass


@dataclass
class Flight:
    origin: str
    destination: str
    departure_date: str
    return_date: str
    max_price: float = 999999.0
    last_airline: str = ""
    id: int | None = None
    date_flex_days: int = 0

    # Search filters (Sprint 2 / Phase 2)
    trip_type: str = "round-trip"  # "round-trip" or "one-way"
    cabin_class: str = "economy"  # economy | premium-economy | business | first
    max_stops: int | None = None  # 0 = direct only, None = unlimited

    # Monitoring state used by the notification rule engine
    # (Sprint 2 / Phase 1). None means "not checked yet".
    last_price: float | None = None
    lowest_price_seen: float | None = None
    last_notified_price: float | None = None
    last_checked_at: str | None = None
