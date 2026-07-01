from urllib.parse import quote


class GoogleFlightsURLBuilder:

    BASE_URL = "https://www.google.com/travel/flights"

    @staticmethod
    def build(
        origin: str,
        destination: str,
        departure: str,
        return_date: str,
    ) -> str:

        query = (
            f"?q=Flights%20from%20{quote(origin)}"
            f"%20to%20{quote(destination)}"
            f"%20{departure}"
            f"%20{return_date}"
        )

        return GoogleFlightsURLBuilder.BASE_URL + query