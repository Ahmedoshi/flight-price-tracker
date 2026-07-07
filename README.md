# Flight Price Tracker

A Telegram bot that tracks flight prices across multiple providers
(Google Flights, Duffel, Kiwi.com, Amadeus, Skyscanner) and alerts on
price drops, new lows, flash deals, and more.

## Running the bot

```
pip install -r requirements.txt
cp .env.example .env   # fill in BOT_TOKEN, CHAT_ID, etc.
python3 main.py
```

## Running tests

```
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

Tests are fully isolated from real data - every test gets a fresh
temporary SQLite database (see `tests/conftest.py`) and never touches
`data/flights.db` or makes real network calls.

`scripts/` contains manual debug scripts (`debug_fast_flights.py`,
`debug_google_playwright.py`) that make real live network/browser
calls - these are intentionally kept out of `tests/` so pytest never
executes them by accident. Run them directly when needed:
`python3 scripts/debug_fast_flights.py`.
