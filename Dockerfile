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

# Without this, Python block-buffers stdout when it isn't attached to
# a TTY (i.e. always, inside a container) - print() output (including
# main.py's startup banner and any scheduler activity) can sit in the
# buffer indefinitely instead of reaching `railway logs`/`fly logs`,
# making a perfectly healthy process look hung. Nixpacks-based builds
# (Railway's old auto-detected build, before this Dockerfile existed)
# set this automatically; a custom Dockerfile doesn't unless told to.
ENV PYTHONUNBUFFERED=1

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

# This directory exists at build time regardless of platform. Railway
# overlays its own persistent Volume here at runtime (already
# configured from the original Nixpacks-based deploy); on platforms
# without a mounted volume (Koyeb free tier, a bare Fly Machine) this
# is ephemeral instead - fine once DATABASE_URL points at Postgres,
# since flight/price data lives there, not in local SQLite; only logs
# and bot_persistence.pickle would be lost on redeploy in that case.
RUN mkdir -p /app/data /app/logs

CMD ["python", "main.py"]
