from datetime import datetime, timedelta


def format_checked_at(value, length: int | None = None) -> str:
    """Normalize a price_history.checked_at value to a display string.

    SQLite always hands this column back as plain text ("YYYY-MM-DD
    HH:MM:SS"), but Postgres (Roadmap Phase 5) decodes its TIMESTAMP
    column into a native datetime.datetime via psycopg2 - slicing or
    string-formatting a datetime the same way you'd slice a string
    either crashes (row[2][:10] on a datetime raises TypeError) or
    prints microseconds SQLite never did. This accepts either and
    always returns a clean "YYYY-MM-DD HH:MM:SS"-shaped string,
    optionally truncated to `length` characters (e.g. 10 for just the
    date portion).
    """

    if isinstance(value, datetime):
        text = value.strftime("%Y-%m-%d %H:%M:%S")
    else:
        text = str(value)

    return text[:length] if length is not None else text


def is_valid_date(text: str) -> bool:

    try:
        datetime.strptime(text, "%Y-%m-%d")
        return True

    except ValueError:
        return False


def date_range_pairs(
    departure_date: str,
    return_date: str,
    flex_days: int,
) -> list[tuple[str, str]]:
    """Build (departure, return) date pairs for a flexible-date search.

    Both dates are shifted together by the same offset, from
    -flex_days to +flex_days, so the trip length stays fixed while the
    whole trip slides earlier/later. flex_days=0 returns just the
    original pair.
    """

    departure = datetime.strptime(departure_date, "%Y-%m-%d").date()
    return_ = datetime.strptime(return_date, "%Y-%m-%d").date()

    pairs = []

    for offset in range(-flex_days, flex_days + 1):

        shift = timedelta(days=offset)

        pairs.append(
            (
                (departure + shift).isoformat(),
                (return_ + shift).isoformat(),
            )
        )

    return pairs


def single_date_range(date_str: str, flex_days: int) -> list[str]:
    """Same idea as date_range_pairs but for a one-way trip: just the
    departure date, shifted -flex_days..+flex_days."""

    departure = datetime.strptime(date_str, "%Y-%m-%d").date()

    return [
        (departure + timedelta(days=offset)).isoformat()
        for offset in range(-flex_days, flex_days + 1)
    ]
