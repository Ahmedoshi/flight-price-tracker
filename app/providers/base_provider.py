from abc import ABC, abstractmethod

from app.models.flight import Flight
from app.models.flight_result import FlightResult


class BaseProvider(ABC):

    @abstractmethod
    async def search(self, flight: Flight) -> list[FlightResult]:
        pass