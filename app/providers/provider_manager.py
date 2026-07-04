import asyncio

from app.config.settings import settings
from app.models.flight import Flight
from app.models.flight_result import FlightResult
from app.providers.google_flights import GoogleFlightsProvider
from app.providers.kiwi_flights import KiwiFlightsProvider


class ProviderManager:

    def __init__(self):

        self.providers = [
            GoogleFlightsProvider(),
        ]

        # Kiwi.com requires a free Tequila API key (KIWI_API_KEY in
        # .env). Without one, it's skipped entirely and the bot keeps
        # working on Google Flights alone.
        if settings.kiwi_api_key:
            self.providers.append(KiwiFlightsProvider())

    async def search(self, flight: Flight) -> list[FlightResult]:

        async def _safe_search(provider):

            try:
                return await provider.search(flight)

            except Exception as exc:
                # One provider failing (rate limit, network issue,
                # scrape breaking) shouldn't take down the whole search.
                print(f"{provider.__class__.__name__} failed: {exc}")
                return []

        results_lists = await asyncio.gather(
            *(_safe_search(provider) for provider in self.providers)
        )

        results = [result for sublist in results_lists for result in sublist]

        results.sort(key=lambda x: x.price)

        return results