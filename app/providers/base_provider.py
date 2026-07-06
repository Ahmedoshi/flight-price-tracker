from abc import ABC, abstractmethod

from app.models.flight import Flight
from app.models.flight_result import FlightResult


class BaseProvider(ABC):

    # Whether ProviderManager should include this provider in
    # scheduler-driven (hourly, automatic) checks, as opposed to
    # manual ones (/check, the Check Flight wizard, "Check Now").
    # Providers with a very small request quota (e.g. Skyscanner's
    # Sky Scrapper free tier) should set this to False so they're
    # only spent on checks a human explicitly asked for.
    ALLOWED_IN_SCHEDULED_CHECKS = True

    @abstractmethod
    async def search(self, flight: Flight) -> list[FlightResult]:
        pass