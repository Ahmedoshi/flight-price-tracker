import asyncio

from app.models.flight import Flight
from app.models.flight_result import FlightResult
from app.providers.provider_manager import ProviderManager
from app.services.tracking_service import TrackingService
from app.utils.airports import parse_codes
from app.utils.dates import date_range_pairs, is_valid_date, single_date_range
from app.utils.flight_filters import VALID_CABIN_CLASSES, VALID_TRIP_TYPES
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
        return_date: str | None = None,
        date_flex_days: int = 0,
        trip_type: str = "round-trip",
        cabin_class: str = "economy",
        max_stops: int | None = None,
        is_scheduled_check: bool = False,
    ) -> list[FlightResult]:
        """Search every origin/destination airport combination across
        the flexible date range, and return all results pooled from
        every provider, cheapest first.

        origin / destination may each be a single airport code or a
        comma-separated list (e.g. "RUH,DMM"). date_flex_days shifts
        the departure (and, for round-trips, return) date together by
        -N..+N days. return_date is ignored for one-way trips.

        is_scheduled_check should be True only when called from the
        hourly scheduler - it excludes providers with a request quota
        too small for automatic checks (see ProviderManager.search).
        """

        origins = parse_codes(origin)
        destinations = parse_codes(destination)

        if trip_type not in VALID_TRIP_TYPES:
            raise ValueError(f"trip_type must be one of {', '.join(VALID_TRIP_TYPES)}.")

        if cabin_class not in VALID_CABIN_CLASSES:
            raise ValueError(f"cabin_class must be one of {', '.join(VALID_CABIN_CLASSES)}.")

        if not is_valid_date(departure_date):
            raise ValueError("Departure date must be in YYYY-MM-DD format.")

        if trip_type == "round-trip" and not (return_date and is_valid_date(return_date)):
            raise ValueError("Return date must be in YYYY-MM-DD format for round-trip.")

        error = validate_search_scope(origins, destinations, date_flex_days)

        if error:
            raise ValueError(error)

        if trip_type == "round-trip":
            date_pairs = date_range_pairs(departure_date, return_date, date_flex_days)
        else:
            date_pairs = [(dep, "") for dep in single_date_range(departure_date, date_flex_days)]

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_SEARCHES)

        async def _search_one(o: str, d: str, dep: str, ret: str):

            async with semaphore:

                flight = Flight(
                    origin=o,
                    destination=d,
                    departure_date=dep,
                    return_date=ret,
                    trip_type=trip_type,
                    cabin_class=cabin_class,
                    max_stops=max_stops,
                )

                return await self.provider_manager.search(flight, is_scheduled_check)

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

    async def check_multi_city(
        self,
        legs: list[dict],
        cabin_class: str = "economy",
        max_stops: int | None = None,
    ) -> list[FlightResult]:
        """Search a fixed multi-city itinerary (2-5 legs, each a dict
        with origin/destination/date). Unlike check_flight(), there's
        no flexible-date or multi-airport combinatorial expansion here
        - multi-city legs are exact, as entered.

        Only providers that implement multi-city search will return
        anything (currently Google Flights only); the rest skip
        themselves via their own trip_type == "multi-city" guard.
        """

        if len(legs) < 2:
            raise ValueError("A multi-city trip needs at least 2 legs.")

        if cabin_class not in VALID_CABIN_CLASSES:
            raise ValueError(f"cabin_class must be one of {', '.join(VALID_CABIN_CLASSES)}.")

        for leg in legs:
            if not is_valid_date(leg["date"]):
                raise ValueError(f"Leg date '{leg['date']}' must be in YYYY-MM-DD format.")

        flight = Flight(
            origin=legs[0]["origin"],
            destination=legs[-1]["destination"],
            departure_date=legs[0]["date"],
            return_date="",
            trip_type="multi-city",
            cabin_class=cabin_class,
            max_stops=max_stops,
            legs=legs,
        )

        results = await self.provider_manager.search(flight)
        results.sort(key=lambda x: x.price)

        return results

    async def cheapest_multi_city(
        self,
        legs: list[dict],
        cabin_class: str = "economy",
        max_stops: int | None = None,
    ) -> FlightResult | None:

        results = await self.check_multi_city(legs, cabin_class, max_stops)

        if not results:
            return None

        result = results[0]

        self.tracking.save_result(result)

        return result

    async def cheapest_flight(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str | None = None,
        date_flex_days: int = 0,
        trip_type: str = "round-trip",
        cabin_class: str = "economy",
        max_stops: int | None = None,
        is_scheduled_check: bool = False,
    ) -> FlightResult | None:

        results = await self.check_flight(
            origin,
            destination,
            departure_date,
            return_date,
            date_flex_days,
            trip_type,
            cabin_class,
            max_stops,
            is_scheduled_check,
        )

        if not results:
            return None

        result = results[0]

        self.tracking.save_result(result)

        return result
