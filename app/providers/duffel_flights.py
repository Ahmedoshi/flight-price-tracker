"""Duffel API flight search - scaffolding only.

Not wired up with a real token yet (Sprint 2 / Phase 5: build the
extension point now, fill in a real key later).

To activate this provider:
  1. Sign up at https://duffel.com and create an access token
     (Dashboard -> your org -> Developers -> Access tokens). Test
     tokens start with "duffel_test_".
  2. Set DUFFEL_API_KEY in .env (and Railway's environment variables).
  3. ProviderManager will then include this provider automatically -
     see app/providers/provider_manager.py's PROVIDER_REGISTRY.

Reference flow (verify against current docs before relying on it -
this hasn't been exercised against a live key):
  - POST https://api.duffel.com/air/offer_requests
    headers: Authorization: Bearer <token>, Duffel-Version: v2
    body: {"data": {"slices": [...], "passengers": [...],
                     "cabin_class": "economy"}}
    A one-way search has one slice (origin/destination/date); a
    round-trip has two (outbound + return).
  -> response.data.offers is a list of priced offers, cheapest first
     is not guaranteed - sort client-side same as our other providers.
"""

import httpx

from app.config.settings import settings
from app.models.flight import Flight
from app.models.flight_result import FlightResult
from app.providers.base_provider import BaseProvider
from app.services.fx_service import convert_to_sar

OFFER_REQUESTS_URL = "https://api.duffel.com/air/offer_requests"


class DuffelFlightsProvider(BaseProvider):

    NAME = "Duffel"

    async def search(self, flight: Flight) -> list[FlightResult]:

        if not settings.duffel_api_key:
            return []

        if flight.trip_type == "multi-city":
            # Duffel does support multi-slice offer requests, but that
            # needs a dedicated request shape - not wired up yet.
            return []

        slices = [
            {
                "origin": flight.origin,
                "destination": flight.destination,
                "departure_date": flight.departure_date,
            }
        ]

        if flight.trip_type == "round-trip":

            slices.append(
                {
                    "origin": flight.destination,
                    "destination": flight.origin,
                    "departure_date": flight.return_date,
                }
            )

        body = {
            "data": {
                "slices": slices,
                "passengers": [{"type": "adult"}],
                "cabin_class": flight.cabin_class.replace("-", "_"),
            }
        }

        headers = {
            "Authorization": f"Bearer {settings.duffel_api_key}",
            "Duffel-Version": "v2",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:

                response = await client.post(
                    # "?return_offers=true" gets offers back synchronously
                    # instead of requiring a follow-up GET.
                    f"{OFFER_REQUESTS_URL}?return_offers=true&limit=5",
                    json=body,
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()

        except httpx.HTTPError as exc:

            print(f"Duffel API error: {exc}")
            return []

        output = []

        for offer in payload.get("data", {}).get("offers", []):

            try:
                price = float(offer["total_amount"])
                currency = offer["total_currency"]

            except (KeyError, ValueError):
                continue

            # Duffel's total_currency is fixed to this account's billing
            # currency (not requestable per search, unlike every other
            # provider here) - convert to SAR so it's comparable against
            # the user's SAR-denominated target price. See fx_service.py.
            if currency.upper() != "SAR":
                price, currency = await convert_to_sar(price, currency)

            airline = (offer.get("owner") or {}).get("name", "Unknown")

            output.append(
                FlightResult(
                    provider="Duffel",
                    airline=airline,
                    price=price,
                    currency=currency,
                    origin=flight.origin,
                    destination=flight.destination,
                    departure_date=flight.departure_date,
                    return_date=flight.return_date,
                    booking_url="",
                )
            )

        output.sort(key=lambda x: x.price)

        return output
