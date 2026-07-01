from app.models.flight import Flight
from app.models.flight_result import FlightResult
from app.providers.google_flights import GoogleFlightsProvider


class ProviderManager:

    def __init__(self):

        self.providers = [
            GoogleFlightsProvider(),
        ]

    async def search(self, flight: Flight) -> list[FlightResult]:

        results = []

        for provider in self.providers:
            provider_results = await provider.search(flight)
            results.extend(provider_results)

        results.sort(key=lambda x: x.price)

        return results