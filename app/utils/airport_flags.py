"""Airport code -> country flag emoji, for a bit of visual texture on
route lines (RUH -> LIS reads as 🇸🇦 RUH -> 🇵🇹 LIS).

Deliberately not exhaustive - covers the airports a personal flight
tracker realistically deals with (Gulf/Middle East, major European,
North American, and Asian hubs). Unknown codes just return "" rather
than guessing, so an unmapped airport degrades gracefully to plain
text instead of showing a wrong flag.

Flags are computed algorithmically from the 2-letter ISO country code
via Unicode regional indicator symbols, so adding a new airport only
needs one line here - no need to hunt down the actual flag emoji.
"""

# IATA airport code -> ISO 3166-1 alpha-2 country code.
_AIRPORT_COUNTRY: dict[str, str] = {
    # Saudi Arabia
    "RUH": "SA", "JED": "SA", "DMM": "SA", "MED": "SA", "AHB": "SA",
    "TIF": "SA", "ELQ": "SA", "TUU": "SA", "GIZ": "SA", "HAS": "SA",
    "AJF": "SA", "AQI": "SA", "ABT": "SA", "YNB": "SA",
    # Gulf / Middle East
    "DXB": "AE", "AUH": "AE", "SHJ": "AE", "DOH": "QA", "BAH": "BH",
    "KWI": "KW", "MCT": "OM", "AMM": "JO", "BEY": "LB", "TLV": "IL",
    "CAI": "EG", "HRG": "EG",
    # Europe
    "LHR": "GB", "LGW": "GB", "LTN": "GB", "STN": "GB", "MAN": "GB",
    "EDI": "GB", "CDG": "FR", "ORY": "FR", "NCE": "FR", "LYS": "FR",
    "FRA": "DE", "MUC": "DE", "BER": "DE", "DUS": "DE", "HAM": "DE",
    "AMS": "NL", "MAD": "ES", "BCN": "ES", "AGP": "ES", "PMI": "ES",
    "FCO": "IT", "MXP": "IT", "VCE": "IT", "NAP": "IT", "LIS": "PT",
    "OPO": "PT", "ZRH": "CH", "GVA": "CH", "VIE": "AT", "CPH": "DK",
    "ARN": "SE", "OSL": "NO", "HEL": "FI", "DUB": "IE", "ATH": "GR",
    "IST": "TR", "SAW": "TR", "WAW": "PL", "PRG": "CZ", "BUD": "HU",
    "BRU": "BE", "LUX": "LU", "OTP": "RO", "SOF": "BG", "ZAG": "HR",
    "KEF": "IS",
    # North America
    "JFK": "US", "EWR": "US", "LGA": "US", "LAX": "US", "ORD": "US",
    "SFO": "US", "MIA": "US", "ATL": "US", "DFW": "US", "SEA": "US",
    "BOS": "US", "IAD": "US", "YYZ": "CA", "YVR": "CA", "YUL": "CA",
    "MEX": "MX", "CUN": "MX",
    # Asia
    "DEL": "IN", "BOM": "IN", "BLR": "IN", "MAA": "IN", "BKK": "TH",
    "DMK": "TH", "SIN": "SG", "KUL": "MY", "HKG": "HK", "NRT": "JP",
    "HND": "JP", "KIX": "JP", "ICN": "KR", "GMP": "KR", "PEK": "CN",
    "PVG": "CN", "CAN": "CN", "SZX": "CN", "TPE": "TW", "MNL": "PH",
    "CGK": "ID", "DPS": "ID", "SGN": "VN", "HAN": "VN",
    # Africa
    "CMN": "MA", "RAK": "MA", "TUN": "TN", "ALG": "DZ", "JNB": "ZA",
    "CPT": "ZA", "NBO": "KE", "ADD": "ET", "LOS": "NG", "ACC": "GH",
    "DAR": "TZ",
    # Oceania
    "SYD": "AU", "MEL": "AU", "BNE": "AU", "PER": "AU", "AKL": "NZ",
}


def _flag_from_country_code(iso2: str) -> str:

    return "".join(chr(0x1F1E6 + ord(letter) - ord("A")) for letter in iso2.upper())


def airport_flag(code: str) -> str:
    """Flag emoji for an IATA airport code, or "" if unknown. Safe to
    call with anything - non-airport strings (e.g. a multi-airport
    "RUH,DMM" list someone forgot to split) just return ""."""

    country = _AIRPORT_COUNTRY.get(code.strip().upper())

    return _flag_from_country_code(country) if country else ""
