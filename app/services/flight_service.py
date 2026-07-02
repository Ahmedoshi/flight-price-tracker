from app.models.flight import Flight
from app.models.flight_result import FlightResult
from app.providers.provider_manager import ProviderManager
from app.services.tracking_service import TrackingService


class FlightService:

    def __init__(self):
        self.provider_manager = ProviderManager()
        self.tracking = TrackingService()

    async def check_flight(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
    ) -> list[FlightResult]:

        flight = Flight(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
        )

        results = await self.provider_manager.search(flight)

        results.sort(key=lambda x: x.price)

        return results

    async def cheapest_flight(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
    ) -> FlightResult | None:

        results = await self.check_flight(
            origin,
            destination,
            departure_date,
            return_date,
        )

        if not results:
            return None

        result = results[0]

        self.tracking.save_result(result)

        return result