import asyncio
import time

from app.config.settings import settings
from app.models.flight import Flight
from app.models.flight_result import FlightResult
from app.providers.amadeus_flights import AmadeusFlightsProvider
from app.providers.duffel_flights import DuffelFlightsProvider
from app.providers.google_flights import GoogleFlightsProvider
from app.providers.kiwi_flights import KiwiFlightsProvider
from app.providers.skyscanner_flights import SkyscannerFlightsProvider
from app.services import provider_health

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


async def _resilient_search(provider, flight: Flight) -> list[FlightResult]:
    """Run one provider's search() with a timeout, retries (with
    exponential backoff) on transient failures, and health tracking -
    Roadmap Phase 1 (provider reliability).

    A provider's own "no flights found" is not a failure (providers
    already catch that internally and return []) - only exceptions
    (timeouts, network/HTTP errors, unexpected parsing crashes) count
    against a provider's health here.
    """

    name = provider.NAME

    if provider_health.is_disabled(name):
        # Recently tripped the failure threshold - skip the network
        # round-trip entirely until its cooldown passes, rather than
        # spending a full timeout + retries on a provider we already
        # know is down.
        return []

    attempts = settings.provider_max_retries + 1
    start = time.monotonic()
    last_exc: Exception | None = None

    for attempt in range(attempts):

        try:
            result = await asyncio.wait_for(
                provider.search(flight),
                timeout=settings.provider_timeout_seconds,
            )

            elapsed_ms = (time.monotonic() - start) * 1000
            provider_health.record_success(name, elapsed_ms)

            return result

        except Exception as exc:  # noqa: BLE001 - deliberately broad, see docstring

            last_exc = exc

            if attempt < attempts - 1:

                backoff = settings.provider_retry_backoff_seconds * (2**attempt)
                await asyncio.sleep(backoff)

    # Every attempt failed.
    provider_health.record_failure(name, str(last_exc))
    print(f"{provider.__class__.__name__} failed after {attempts} attempt(s): {last_exc}")

    return []


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

        results_lists = await asyncio.gather(
            *(_resilient_search(provider, flight) for provider in providers)
        )

        results = [result for sublist in results_lists for result in sublist]

        results.sort(key=lambda x: x.price)

        return results
