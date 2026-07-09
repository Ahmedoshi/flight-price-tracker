# Moving off Railway: Koyeb (free) + Neon (free Postgres)

> **Deprecated (July 2026):** Koyeb closed its free Starter tier to
> new signups after the Mistral AI acquisition - new accounts now
> start at $29/month, which defeats the point of this doc. Left here
> for reference only. See [DEPLOY_FLY.md](./DEPLOY_FLY.md) for the
> path actually used instead.

Railway started charging (~$5/mo). This is a $0 alternative, with one
tradeoff spelled out below.

## Why this needs a keepalive trick

This bot is a background process (Telegram long-polling + an hourly
APScheduler job) - it doesn't serve HTTP requests. Koyeb's free
instance only supports **Web Services**, not **Worker Services**, and
free Web Services scale to zero after 1 hour with no incoming traffic.

The fix already shipped in this repo: `main.py` now starts a tiny
built-in HTTP server (`/`) on `$PORT` alongside the bot, purely so
Koyeb sees it as a healthy Web Service. An external free "pinger"
hits that URL every ~10 minutes to keep the instance from sleeping.
This is a known, common pattern for running always-on bots on
free-tier PaaS platforms - not a hack specific to this repo.

**Known limitation:** if the pinger ever stops (its own free tier
hiccups, etc.), Koyeb will scale the bot to zero after an hour of
silence, and it'll take a few seconds to wake back up on the next
ping - you may miss part of an hourly price-check cycle in that
window. For a personal tracker this is a reasonable tradeoff for $0;
it would not be acceptable for anything more serious.

**Also worth knowing:** Koyeb's free instance is 512MB RAM / 0.1 vCPU.
The Google Flights provider drives a real headless Chromium browser
(via the `fast-flights` package), which is memory-heavy and has no
API-key gate (it's always active). If you see the bot crash-looping
on Koyeb, the first thing to try is disabling Google Flights and
relying on the other providers (Kiwi, Amadeus, Duffel, Skyscanner) -
see `app/providers/provider_manager.py`.

## Steps

### 1. Create the Neon database

1. Go to neon.tech and create a free account/project.
2. From the project dashboard, copy the connection string under
   **Connection Details** (looks like
   `postgresql://user:password@ep-xxxx.neon.tech/dbname?sslmode=require`).
3. Keep this handy - it becomes `DATABASE_URL`.

### 2. Copy existing data from Railway to Neon (optional, one-time)

Only needed if you want to keep your currently tracked flights/price
history. Get your Railway Postgres URL from Railway's Postgres
service → **Variables** → `DATABASE_URL` (use `DATABASE_PUBLIC_URL`
if running this from your own machine rather than inside Railway).

```
python3 scripts/migrate_railway_to_neon.py "<railway_database_url>" "<neon_database_url>"
```

This only reads from Railway - safe to re-run against a fresh Neon
database if something goes wrong.

### 3. Push this repo to GitHub

Already done if you're deploying from the same repo Railway used.

### 4. Create the Koyeb service

1. Go to koyeb.com and create a free account.
2. **Create Service → GitHub** → select this repo/branch (`main`).
3. Builder: Koyeb should detect the `Dockerfile` in the repo root
   automatically (Docker builder, not Buildpack).
4. Instance type: **Free**.
5. Port: Koyeb sets `$PORT` automatically and the bot's built-in
   health server reads it - no manual port config needed, but if
   asked, use `8000`.
6. Health check path: `/`.
7. Environment variables - add everything from your `.env` /
   `.env.example`, at minimum:
   - `BOT_TOKEN`
   - `CHAT_ID`
   - `DATABASE_URL` = the Neon connection string from step 1
   - any provider API keys you use (`KIWI_API_KEY`, `AMADEUS_CLIENT_ID`,
     `AMADEUS_CLIENT_SECRET`, `DUFFEL_API_KEY`, `SKYSCANNER_API_KEY`)
   - Twilio/WhatsApp vars if you use those
8. Deploy. Watch the build logs - the Playwright/Chromium install
   step takes a few minutes on first build.
9. Once running, open the service URL in a browser - you should see
   `ok`. That confirms the health server is up.

### 5. Set up the keepalive pinger

1. Go to cron-job.org (or UptimeRobot) and create a free account.
2. Create a new cron job / monitor:
   - URL: your Koyeb service URL (e.g. `https://your-app.koyeb.app`)
   - Interval: every 10 minutes
3. Save. Within an hour you should see repeated hits in Koyeb's
   request logs confirming the instance is staying awake.

### 6. Verify the bot

Message the bot on Telegram - `/status` should respond, and after the
next scheduled check confirm price alerts still arrive.

### 7. Decommission Railway

Once Koyeb + Neon are confirmed working for a day or two, delete the
Railway project to stop the $5/mo charge.
