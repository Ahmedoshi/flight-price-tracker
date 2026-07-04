def parse_codes(text: str) -> list[str]:
    """Split a comma-separated airport code list into clean codes.

    "ruh, dmm" -> ["RUH", "DMM"]
    """

    return [code.strip().upper() for code in text.split(",") if code.strip()]


def validate_codes(codes: list[str]) -> str | None:
    """Return an error message if any code isn't a plausible 3-letter
    IATA airport code, otherwise None."""

    for code in codes:

        if not (code.isalpha() and len(code) == 3):
            return f"'{code}' isn't a valid 3-letter airport code."

    return None
