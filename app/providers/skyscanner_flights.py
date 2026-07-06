"""Skyscanner-sourced flight search, via the unofficial "Sky Scrapper"
API on RapidAPI (https://rapidapi.com/apiheya/api/sky-scrapper).

This is NOT Skyscanner's own official Travel Partners API - that one
requires a partnership application, a ~2 week business review, and
isn't guaranteed even then. Sky Scrapper is a third-party scraper that
returns the same public Skyscanner data via a normal REST API you can
subscribe to instantly on RapidAPI.

Setup:
  1. Sign up at https://rapidapi.com and subscribe to "Air Scraper" /
     Sky Scrapper (https://rapidapi.com/apiheya/api/sky-scrapper). The
     free "Basic" plan works for testing.
  2. Copy your X-RapidAPI-Key from the app dashboard.
  3. Set SKYSCANNER_API_KEY to that key (same setting name Skyscanner
     already had reserved - it now means "RapidAPI key for Sky
     Scrapper" rather than an official Skyscanner credential).

IMPORTANT - free tier limit: the Basic plan caps out at 20 requests
per MONTH (not per day). That's nowhere near enough for hourly
scheduled monitoring - a single tracked flight checked every hour
would blow through the whole month's quota in under a day. Because of
this, this provider deliberately opts OUT of the scheduler's hourly
checks (see ALLOWED_IN_SCHEDULED_CHECKS below) and is only queried on
manual /check, the Check Flight wizard, and the "Check Now" button -
places where a human is actively spending one of those 20 requests on
purpose.

Each search here costs 3 API calls (resolve origin airport, resolve
destination airport, search flights), so the free tier is really only
good for a handful of manual lookups per month. Upgrading to the
Pro plan ($9.99/mo, 10,600 requests) removes that constraint.

Response shape below is based on the published RapidAPI documentation
for this endpoint, not a live test call (the account used to research
this didn't have an active subscription). If the real shape differs
once you have a live key, the parsing in _parse_itinerary() is the
place to adjust - everything else (airport resolution, request
params) is verified against the docs.
"""

import httpx

from app.config.settings import settings
from app.models.flight import Flight
from app.models.flight_result import FlightResult
from app.providers.base_provider import BaseProvider

API_HOST = "sky-scrapper.p.rapidapi.com"
BASE_URL = f"https://{API_HOST}/api"

CABIN_LOOKUP = {
    "economy": "economy",
    "premium-economy": "premium_economy",
    "business": "business",
    "first": "first",
}


class SkyscannerFlightsProvider(BaseProvider):

    NAME = "Skyscanner"

    # Deliberately excluded from the scheduler's hourly checks - see
    # the module docstring for why (20 requests/month free tier).
    ALLOWED_IN_SCHEDULED_CHECKS = False

    def _headers(self) -> dict:

        return {
            "x-rapidapi-host": API_HOST,
            "x-rapidapi-key": settings.skyscanner_api_key,
        }

    async def search(self, flight: Flight) -> list[FlightResult]:

        if not settings.skyscanner_api_key:
            return []

        if flight.trip_type == "multi-city":
            # Sky Scrapper's searchFlights endpoint is a single
            # origin/destination pair - no multi-leg support.
            return []

        try:

            async with httpx.AsyncClient(timeout=20) as client:

                origin_sky_id, origin_entity_id = await self._resolve_airport(
                    client, flight.origin
                )
                destination_sky_id, destination_entity_id = await self._resolve_airport(
                    client, flight.destination
                )

                if not origin_sky_id or not destination_sky_id:
                    return []

                params = {
                    "originSkyId": origin_sky_id,
                    "destinationSkyId": destination_sky_id,
                    "originEntityId": origin_entity_id,
                    "destinationEntityId": destination_entity_id,
                    "date": flight.departure_date,
                    "cabinClass": CABIN_LOOKUP.get(flight.cabin_class, "economy"),
                    "adults": 1,
                    "sortBy": "best",
                    "currency": "SAR",
                    "market": "en-US",
                    "countryCode": "US",
                }

                if flight.trip_type == "round-trip" and flight.return_date:
                    params["returnDate"] = flight.return_date

                response = await client.get(
                    f"{BASE_URL}/v2/flights/searchFlights",
                    params=params,
                    headers=self._headers(),
                )
                response.raise_for_status()
                payload = response.json()

        except httpx.HTTPError as exc:

            print(f"Skyscanner (Sky Scrapper) API error: {exc}")
            return []

        itineraries = (payload.get("data") or {}).get("itineraries") or []

        currency = "SAR"
        output = []

        for item in itineraries:

            result = self._parse_itinerary(item, flight, currency)

            if result is not None:
                output.append(result)

        if flight.max_stops is not None:

            output = [
                r for r in output
                if r.stops is None or r.stops <= flight.max_stops
            ]

        output.sort(key=lambda r: r.price)

        return output

    async def _resolve_airport(
        self, client: httpx.AsyncClient, airport_code: str
    ) -> tuple[str | None, str | None]:
        """Resolve an IATA code (e.g. "RUH") to Sky Scrapper's own
        skyId/entityId pair, required by searchFlights. Returns
        (None, None) if nothing matched."""

        try:
            response = await client.get(
                f"{BASE_URL}/v1/flights/searchAirport",
                params={"query": airport_code, "locale": "en-US"},
                headers=self._headers(),
            )
            response.raise_for_status()
            payload = response.json()

        except httpx.HTTPError as exc:

            print(f"Skyscanner (Sky Scrapper) airport lookup failed: {exc}")
            return None, None

        for item in payload.get("data") or []:

            flight_params = item.get("navigation", {}).get("relevantFlightParams", {})
            sky_id = flight_params.get("skyId")

            if sky_id and sky_id.upper() == airport_code.upper():
                return sky_id, flight_params.get("entityId")

        # No exact code match - fall back to the first suggestion, if any.
        if payload.get("data"):

            flight_params = payload["data"][0].get("navigation", {}).get(
                "relevantFlightParams", {}
            )
            return flight_params.get("skyId"), flight_params.get("entityId")

        return None, None

    def _parse_itinerary(self, item: dict, flight: Flight, currency: str) -> FlightResult | None:

        try:
            price = item.get("price", {}).get("raw")

            if price is None:
                return None

            legs = item.get("legs") or []

            if not legs:
                return None

            first_leg = legs[0]
            carriers = first_leg.get("carriers", {}).get("marketing") or []
            airline = ", ".join(c.get("name", "") for c in carriers if c.get("name")) or "Unknown"

            stops = first_leg.get("stopCount")

            return FlightResult(
                provider="Skyscanner",
                airline=airline,
                price=float(price),
                currency=currency,
                origin=flight.origin,
                destination=flight.destination,
                departure_date=flight.departure_date,
                return_date=flight.return_date,
                booking_url="",
                stops=stops,
            )

        except (KeyError, TypeError, ValueError):
            # Any unexpected shape from a docs-only implementation
            # should skip this one result, not blow up the whole search.
            return None
