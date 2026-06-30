from playwright.async_api import async_playwright

from app.models.flight import Flight
from app.models.flight_result import FlightResult
from app.providers.base_provider import BaseProvider


class GoogleFlightsProvider(BaseProvider):

    async def search(self, flight: Flight) -> list[FlightResult]:

        print("Launching Google Flights...")

        async with async_playwright() as p:

            browser = await p.chromium.launch(
                headless=False
            )

            page = await browser.new_page()

            await page.goto(
                "https://www.google.com/travel/flights",
                wait_until="networkidle"
            )

            print("Google Flights opened successfully.")

            await page.screenshot(path="google_flights_home.png")

            print("Screenshot saved.")

            await browser.close()

        return []