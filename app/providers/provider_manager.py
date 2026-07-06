import asyncio

from app.config.settings import settings
from app.models.flight import Flight
from app.models.flight_result import FlightResult
from app.providers.amadeus_flights import AmadeusFlightsProvider
from app.providers.duffel_flights import DuffelFlightsProvider
from app.providers.google_flights import GoogleFlightsProvider
from app.providers.kiwi_flights import KiwiFlightsProvider
from app.providers.skyscanner_flights import SkyscannerFlightsProvider

# Registry of every provider the bot knows how to use, each gated on
# whether its required setting(s) are actually configured. Adding a
# new provider is: write a BaseProvider subclass, add its settings
# field(s) in app/config/settings.py, and add one line here - nothing
# else in the app needs to change.
PROVIDER_REGISTRY = [
    (lambda: True, GoogleFlightsProvider),  # always on, no key needed
    (lambda: bool(settings.kiwi_api_key), KiwiFlightsProvider),
    (
        lambda: bool(settings.amadeus_client_id and settings.amadeus_client_secret),
        AmadeusFlightsProvider,
    ),
    (lambda: bool(settings.duffel_api_key), DuffelFlightsProvider),
    (lambda: bool(settings.skyscanner_api_key), SkyscannerFlightsProvider),
]


class ProviderManager:

    def __init__(self):

        self.providers = [
            provider_class()
            for is_enabled, provider_class in PROVIDER_REGISTRY
            if is_enabled()
        ]

    async def search(self, flight: Flight, is_scheduled_check: bool = False) -> list[FlightResult]:
        """Search every enabled provider for this flight.

        is_scheduled_check=True is used by the hourly scheduler; it
        skips any provider with ALLOWED_IN_SCHEDULED_CHECKS=False
        (e.g. Skyscanner's Sky Scrapper, whose free tier is only 20
        requests/month - nowhere near enough for hourly automatic
        checks). Manual searches (/check, the wizards, "Check Now")
        leave this at the default False, so those providers still get
        used when a person deliberately asks for a check.
        """

        providers = self.providers

        if is_scheduled_check:
            providers = [p for p in providers if p.ALLOWED_IN_SCHEDULED_CHECKS]

        async def _safe_search(provider):

            try:
                return await provider.search(flight)

            except Exception as exc:
                # One provider failing (rate limit, network issue,
                # scrape breaking) shouldn't take down the whole search.
                print(f"{provider.__class__.__name__} failed: {exc}")
                return []

        results_lists = await asyncio.gather(
            *(_safe_search(provider) for provider in providers)
        )

        results = [result for sublist in results_lists for result in sublist]

        results.sort(key=lambda x: x.price)

        return results
