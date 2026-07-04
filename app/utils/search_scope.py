# Multiple origin/destination airports combined with flexible dates
# multiplies out into N searches, each of which is a real (slow)
# provider call. These caps keep a single /add or /check bounded so it
# can't accidentally trigger dozens of scrapes at once.

MAX_AIRPORTS_PER_SIDE = 3
MAX_DATE_FLEX_DAYS = 5
MAX_TOTAL_COMBINATIONS = 12


def validate_search_scope(
    origins: list[str],
    destinations: list[str],
    flex_days: int,
) -> str | None:
    """Return an error message if the requested search is too broad or
    malformed, otherwise None."""

    if not origins:
        return "Origin is required."

    if not destinations:
        return "Destination is required."

    if len(origins) > MAX_AIRPORTS_PER_SIDE:
        return f"Too many origin airports (max {MAX_AIRPORTS_PER_SIDE})."

    if len(destinations) > MAX_AIRPORTS_PER_SIDE:
        return f"Too many destination airports (max {MAX_AIRPORTS_PER_SIDE})."

    if flex_days < 0:
        return "Flex days must be 0 or higher."

    if flex_days > MAX_DATE_FLEX_DAYS:
        return f"Flex days too high (max {MAX_DATE_FLEX_DAYS})."

    total = len(origins) * len(destinations) * (2 * flex_days + 1)

    if total > MAX_TOTAL_COMBINATIONS:

        return (
            f"That's {total} searches (max {MAX_TOTAL_COMBINATIONS}). "
            "Use fewer airports or a smaller flex range."
        )

    return None
