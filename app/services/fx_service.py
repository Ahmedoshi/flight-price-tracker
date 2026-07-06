"""Currency conversion to SAR.

Every part of this app assumes prices are in SAR - the user enters
target prices in SAR, and Google Flights/Kiwi/Amadeus/Skyscanner all
explicitly request SAR-denominated results from their APIs. Duffel is
the exception: its `total_currency` is fixed to the Duffel account's
own billing currency (e.g. EUR), not something that can be requested
per search. Left unconverted, a EUR price gets compared directly
against a SAR target and mislabeled in alerts.

convert_to_sar() closes that gap using a free, keyless FX API
(open.er-api.com). Rates are cached in memory for a day - exchange
rates don't move enough in a day to matter for a "is this a good
flight deal" check, and it avoids hitting a free API on every
scheduled check for every tracked flight.
"""

import time

import httpx

_RATE_CACHE: dict[str, tuple[float, float]] = {}  # currency -> (rate_to_sar, fetched_at)
_CACHE_TTL_SECONDS = 24 * 60 * 60

FX_URL = "https://open.er-api.com/v6/latest/{currency}"


async def _fetch_rate_to_sar(currency: str) -> float | None:

    try:
        async with httpx.AsyncClient(timeout=10) as client:

            response = await client.get(FX_URL.format(currency=currency))
            response.raise_for_status()
            payload = response.json()

        rate = payload.get("rates", {}).get("SAR")
        return float(rate) if rate else None

    except (httpx.HTTPError, ValueError, TypeError) as exc:

        print(f"FX lookup failed for {currency} -> SAR: {exc}")
        return None


async def convert_to_sar(amount: float, currency: str) -> tuple[float, str]:
    """Convert `amount` in `currency` to SAR.

    Returns (converted_amount, "SAR") normally. If `currency` is
    already SAR, or if the FX lookup fails for any reason, returns the
    original (amount, currency) unconverted - better to surface a
    non-SAR price than to crash a scheduled check or silently show a
    wrong SAR number.
    """

    currency = (currency or "SAR").upper()

    if currency == "SAR":
        return amount, "SAR"

    cached = _RATE_CACHE.get(currency)

    if cached and (time.time() - cached[1]) < _CACHE_TTL_SECONDS:
        rate = cached[0]

    else:
        rate = await _fetch_rate_to_sar(currency)

        if rate is None:
            return amount, currency

        _RATE_CACHE[currency] = (rate, time.time())

    return amount * rate, "SAR"
