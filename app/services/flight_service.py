import asyncio

from app.models.flight import Flight
from app.models.flight_result import FlightResult
from app.providers.provider_manager import ProviderManager
from app.services.tracking_service import TrackingService
from app.utils.airports import parse_codes
from app.utils.dates import date_range_pairs, is_valid_date
from app.utils.search_scope import validate_search_scope

# How many combinations (airport pairs x flexible dates) are searched
# at once. Each search is a real provider call (Google Flights is a
# browser-driven scrape), so this stays modest to avoid hammering
# providers or tying up too many worker threads at once.
MAX_CONCURRENT_SEARCHES = 3


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
        date_flex_days: int = 0,
    ) -> list[FlightResult]:
        """Search every origin/destination airport combination across
        the flexible date range, and return all results pooled from
        every provider, cheapest first.

        origin / destination may each be a single airport code or a
        comma-separated list (e.g. "RUH,DMM"). date_flex_days shifts
        the departure/return pair together by -N..+N days.
        """

        origins = parse_codes(origin)
        destinations = parse_codes(destination)

        if not is_valid_date(departure_date) or not is_valid_date(return_date):
            raise ValueError("Dates must be in YYYY-MM-DD format.")

        error = validate_search_scope(origins, destinations, date_flex_days)

        if error:
            raise ValueError(error)

        date_pairs = date_range_pairs(departure_date, return_date, date_flex_days)

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_SEARCHES)

        async def _search_one(o: str, d: str, dep: str, ret: str):

            async with semaphore:

                flight = Flight(
                    origin=o,
                    destination=d,
                    departure_date=dep,
                    return_date=ret,
                )

                return await self.provider_manager.search(flight)

        tasks = [
            _search_one(o, d, dep, ret)
            for o in origins
            for d in destinations
            for dep, ret in date_pairs
        ]

        results_lists = await asyncio.gather(*tasks)

        results = [result for sublist in results_lists for result in sublist]

        results.sort(key=lambda x: x.price)

        return results

    async def cheapest_flight(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        date_flex_days: int = 0,
    ) -> FlightResult | None:

        results = await self.check_flight(
            origin,
            destination,
            departure_date,
            return_date,
            date_flex_days,
        )

        if not results:
            return None

        result = results[0]

        self.tracking.save_result(result)

        return result
