# Koyeb (unlike Railway) has no auto-detect build - this Dockerfile
# is the deploy artifact. Includes Playwright's Chromium browser since
# the Google Flights provider (app/providers/google_flights.py, via
# the fast-flights package) drives a real headless browser.
#
# NOTE: Koyeb's free instance is 512MB RAM / 0.1 vCPU. Headless
# Chromium is memory-hungry (often 300MB+ per run) and can OOM on
# that tier under load. If the bot crashes/restarts under real usage,
# the cheapest fix is disabling the Google Flights provider (it has no
# API key gate, so it's always active) and relying on the other
# API-based providers (Kiwi, Amadeus, Duffel, Skyscanner) instead -
# see app/providers/provider_manager.py.

FROM python:3.11-slim

WORKDIR /app

# Playwright's Chromium needs these system libraries to run headless
# on a minimal Debian slim image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium

COPY . .

# Railway's persistent Volume at /app/data doesn't exist here - Koyeb
# free tier has no volumes, so this directory is ephemeral (fine once
# DATABASE_URL points at Neon, since flight/price data lives there,
# not in local SQLite; only logs and bot_persistence.pickle are lost
# on redeploy).
RUN mkdir -p /app/data /app/logs

CMD ["python", "main.py"]
