"""Skyscanner flight search - placeholder only.

Unlike Kiwi and Amadeus, Skyscanner doesn't have an easy self-service
signup. Their official "Travel APIs" (formerly available via RapidAPI)
require a partnership application and business review - there's no
instant free-tier key to grab the way there is for Kiwi/Amadeus/Duffel.

This class exists purely so ProviderManager has a slot ready to go:
if/when a SKYSCANNER_API_KEY is actually obtained through a partner
agreement, fill in the real request here (endpoint and auth scheme
depend on which Skyscanner product tier you're approved for, so it's
deliberately not guessed at). Until then this always returns no
results.
"""

from app.config.settings import settings
from app.models.flight import Flight
from app.models.flight_result import FlightResult
from app.providers.base_provider import BaseProvider


class SkyscannerFlightsProvider(BaseProvider):

    async def search(self, flight: Flight) -> list[FlightResult]:

        if not settings.skyscanner_api_key:
            return []

        # No implementation yet - see module docstring. Returning []
        # rather than raising, consistent with how every other
        # provider degrades when something isn't wired up.
        print(
            "SkyscannerFlightsProvider: SKYSCANNER_API_KEY is set but no "
            "request implementation exists yet - see module docstring."
        )
        return []
