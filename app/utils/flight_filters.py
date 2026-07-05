VALID_TRIP_TYPES = {"round-trip", "one-way"}
VALID_CABIN_CLASSES = {"economy", "premium-economy", "business", "first"}

DEFAULT_FILTERS = {
    "trip_type": "round-trip",
    "cabin_class": "economy",
    "max_stops": None,
}


def parse_filter_tokens(tokens: list[str]) -> tuple[dict, str | None]:
    """Parse optional 'key=value' filter tokens, e.g.

        ["trip=oneway", "cabin=business", "stops=0"]

    Recognized keys: trip (oneway|round), cabin (economy|premium-economy|
    business|first), stops (0 = direct only, N = max N stops).

    Returns (filters, error) - filters always has all three keys filled
    in with sane defaults, even when no tokens are given.
    """

    filters = dict(DEFAULT_FILTERS)

    for token in tokens:

        if "=" not in token:
            return filters, f"'{token}' isn't a valid filter (expected key=value)."

        key, _, value = token.partition("=")
        key = key.strip().lower()
        value = value.strip().lower()

        if key == "trip":

            if value in ("oneway", "one-way"):
                filters["trip_type"] = "one-way"

            elif value in ("round", "round-trip", "roundtrip"):
                filters["trip_type"] = "round-trip"

            else:
                return filters, f"trip must be 'oneway' or 'round', got '{value}'."

        elif key == "cabin":

            normalized = value.replace("_", "-")

            if normalized not in VALID_CABIN_CLASSES:

                return filters, (
                    f"cabin must be one of {', '.join(sorted(VALID_CABIN_CLASSES))}."
                )

            filters["cabin_class"] = normalized

        elif key == "stops":

            try:
                stops = int(value)

            except ValueError:
                return filters, "stops must be a whole number (0 = direct only)."

            if stops < 0:
                return filters, "stops must be 0 or higher."

            filters["max_stops"] = stops

        else:

            return filters, f"Unknown filter '{key}'. Use trip=, cabin=, or stops=."

    return filters, None


def parse_trailing_tokens(tokens: list[str]) -> tuple[int, dict, str | None]:
    """Parse the optional tail of a command: an optional bare integer
    (flex days) followed by zero or more 'key=value' filter tokens, in
    either order relative to each other (the integer, if present, must
    come first).

    Returns (flex_days, filters, error).
    """

    flex_days = 0
    remaining = tokens

    if remaining:

        first = remaining[0]
        sign_stripped = first[1:] if first[:1] == "-" else first

        if sign_stripped.isdigit():

            try:
                flex_days = int(first)
                remaining = remaining[1:]

            except ValueError:
                pass

    filters, error = parse_filter_tokens(remaining)

    return flex_days, filters, error


def format_filters(trip_type: str, cabin_class: str, max_stops: int | None) -> str:
    """Human-readable one-liner for confirmation messages, empty if
    everything is at its default."""

    parts = []

    if trip_type == "one-way":
        parts.append("one-way")

    if cabin_class != "economy":
        parts.append(cabin_class.replace("-", " ").title())

    if max_stops is not None:
        parts.append("direct only" if max_stops == 0 else f"max {max_stops} stop(s)")

    if not parts:
        return ""

    return ", ".join(parts)
