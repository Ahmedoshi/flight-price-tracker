from datetime import datetime

import httpx

from app.config.settings import settings
from app.models.flight import Flight
from app.models.flight_result import FlightResult
from app.providers.base_provider import BaseProvider

TEQUILA_SEARCH_URL = "https://api.tequila.kiwi.com/v2/search"

# Kiwi's selected_cabins uses single-letter codes.
CABIN_LOOKUP = {
    "economy": "M",
    "premium-economy": "W",
    "business": "C",
    "first": "F",
}


class KiwiFlightsProvider(BaseProvider):
    """Flight search via the Kiwi.com Tequila API.

    Requires a free API key from https://tequila.kiwi.com - set it as
    KIWI_API_KEY in .env. ProviderManager only instantiates this
    provider when a key is configured, so it's safe even if search()
    is somehow called without one.
    """

    async def search(self, flight: Flight) -> list[FlightResult]:

        if not settings.kiwi_api_key:
            return []

        departure = _to_kiwi_date(flight.departure_date)
        is_round_trip = flight.trip_type == "round-trip"

        params = {
            "fly_from": flight.origin,
            "fly_to": flight.destination,
            "date_from": departure,
            "date_to": departure,
            "flight_type": "round" if is_round_trip else "oneway",
            "adults": 1,
            "curr": "SAR",
            "limit": 5,
            "sort": "price",
            "selected_cabins": CABIN_LOOKUP.get(flight.cabin_class, "M"),
        }

        if is_round_trip:
            return_date = _to_kiwi_date(flight.return_date)
            params["return_from"] = return_date
            params["return_to"] = return_date

        if flight.max_stops is not None:
            params["max_stopovers"] = flight.max_stops

        headers = {"apikey": settings.kiwi_api_key}

        try:
            async with httpx.AsyncClient(timeout=20) as client:

                response = await client.get(
                    TEQUILA_SEARCH_URL,
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()

        except httpx.HTTPError as exc:

            print(f"Kiwi API error: {exc}")
            return []

        currency = payload.get("currency") or "SAR"

        output = []

        for item in payload.get("data", []):

            airlines = item.get("airlines") or []

            output.append(
                FlightResult(
                    provider="Kiwi.com",
                    airline=", ".join(airlines) if airlines else "Unknown",
                    price=float(item.get("price", 0)),
                    currency=currency,
                    origin=flight.origin,
                    destination=flight.destination,
                    departure_date=flight.departure_date,
                    return_date=flight.return_date,
                    booking_url=item.get("deep_link", ""),
                )
            )

        output.sort(key=lambda x: x.price)

        return output


def _to_kiwi_date(date_str: str) -> str:
    """Kiwi's Tequila API wants dates as DD/MM/YYYY."""

    parsed = datetime.strptime(date_str, "%Y-%m-%d")
    return parsed.strftime("%d/%m/%Y")
