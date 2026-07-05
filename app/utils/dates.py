from datetime import datetime, timedelta


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
