"""Amadeus Self-Service Flight Offers Search - scaffolding only.

Not wired up with real credentials yet (Sprint 2 / Phase 5: build the
extension point now, fill in a real key later without touching
anything else).

To activate this provider:
  1. Get free test-environment credentials at
     https://developers.amadeus.com/self-service
  2. Set AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET in .env (and in
     Railway's environment variables for the deployed bot).
  3. ProviderManager will then include this provider automatically -
     see app/providers/provider_manager.py's PROVIDER_REGISTRY.

Reference flow (test environment, verify against current docs before
relying on it - this hasn't been exercised against a live key):
  - POST https://test.api.amadeus.com/v1/security/oauth2/token
    body: grant_type=client_credentials&client_id=...&client_secret=...
    -> { "access_token": "...", "expires_in": 1799, ... }
  - GET https://test.api.amadeus.com/v2/shopping/flight-offers
    headers: Authorization: Bearer <access_token>
    params: originLocationCode, destinationLocationCode, departureDate,
            returnDate (omit for one-way), adults, currencyCode,
            travelClass (ECONOMY|PREMIUM_ECONOMY|BUSINESS|FIRST),
            nonStop=true (for direct-only), max (result count)
"""

import time

import httpx

from app.config.settings import settings
from app.models.flight import Flight
from app.models.flight_result import FlightResult
from app.providers.base_provider import BaseProvider

TOKEN_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
SEARCH_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"

CABIN_LOOKUP = {
    "economy": "ECONOMY",
    "premium-economy": "PREMIUM_ECONOMY",
    "business": "BUSINESS",
    "first": "FIRST",
}

# Cached in-process; a real implementation would want this shared
# across requests/instances rather than per-provider-object.
_token_cache: dict = {"access_token": None, "expires_at": 0}


class AmadeusFlightsProvider(BaseProvider):

    async def search(self, flight: Flight) -> list[FlightResult]:

        if not (settings.amadeus_client_id and settings.amadeus_client_secret):
            return []

        try:
            token = await self._get_access_token()

            params = {
                "originLocationCode": flight.origin,
                "destinationLocationCode": flight.destination,
                "departureDate": flight.departure_date,
                "adults": 1,
                "currencyCode": "SAR",
                "travelClass": CABIN_LOOKUP.get(flight.cabin_class, "ECONOMY"),
                "max": 5,
            }

            if flight.trip_type == "round-trip":
                params["returnDate"] = flight.return_date

            if flight.max_stops == 0:
                params["nonStop"] = "true"

            async with httpx.AsyncClient(timeout=20) as client:

                response = await client.get(
                    SEARCH_URL,
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                payload = response.json()

        except httpx.HTTPError as exc:

            print(f"Amadeus API error: {exc}")
            return []

        output = []

        for offer in payload.get("data", []):

            try:
                price = float(offer["price"]["total"])
                currency = offer["price"]["currency"]

            except (KeyError, ValueError):
                continue

            airlines = ", ".join(offer.get("validatingAirlineCodes", []) or ["Unknown"])

            output.append(
                FlightResult(
                    provider="Amadeus",
                    airline=airlines,
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

    async def _get_access_token(self) -> str:

        if _token_cache["access_token"] and _token_cache["expires_at"] > time.time():
            return _token_cache["access_token"]

        async with httpx.AsyncClient(timeout=20) as client:

            response = await client.post(
                TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.amadeus_client_id,
                    "client_secret": settings.amadeus_client_secret,
                },
            )
            response.raise_for_status()
            payload = response.json()

        _token_cache["access_token"] = payload["access_token"]
        _token_cache["expires_at"] = time.time() + payload.get("expires_in", 1700)

        return _token_cache["access_token"]
