# Moving off Railway: Fly.io + Neon (free Postgres)

Railway started charging (~$5/mo). Koyeb's free tier turned out to be
gone for new signups (see DEPLOY_KOYEB.md), and Oracle Cloud's Always
Free VM signup rejected cards repeatedly during identity verification.
Fly.io is the fallback: not free, but usage-based billing for a bot
this small typically lands well under Railway's $5/month.

## Why this is simpler than the Koyeb attempt

Fly Machines don't require an HTTP service to stay running - a
Machine with no `[http_service]`/`[[services]]` block in `fly.toml`
just runs continuously. This bot is a background process (Telegram
long-polling + an internal APScheduler job, no HTTP API of its own),
so it fits Fly's model directly. No keepalive-pinger workaround needed
(the `/health` endpoint added to `main.py` during the Koyeb attempt is
harmless and left in - just unused here).

**Worth knowing:** the Google Flights provider drives real headless
Chromium (via the `fast-flights` package) and has no API-key gate, so
it's always active and is the heaviest thing this process does
memory-wise. `fly.toml` starts at 512MB - if you see OOM restarts in
`fly logs`, bump memory to `1gb`, or disable Google Flights and rely
on the other providers (Kiwi, Amadeus, Duffel, Skyscanner).

## Steps

### 1. Install flyctl

```
curl -L https://fly.io/install.sh | sh
```

(or `brew install flyctl` on macOS). This has to run on your own
machine - not something I can do from here.

### 2. Sign up / log in

```
fly auth signup   # or: fly auth login
```

This opens your browser for account creation/login - card verification
happens here too (Fly also requires a card on file, but billing is
usage-based rather than a flat paid tier).

### 3. Create the Neon database (if not done already)

Same as the Koyeb plan - go to neon.tech, create a free project, copy
the connection string from **Connection Details**. Keep it handy for
step 5.

If you still have flights tracked in Railway's Postgres and want to
carry them over:

```
python3 scripts/migrate_railway_to_neon.py "<railway_database_url>" "<neon_database_url>"
```

### 4. Launch the app

From the repo root:

```
fly launch --no-deploy
```

- It will detect the `Dockerfile` and `fly.toml` already in this repo.
- Pick an app name (or accept the generated one) and a region.
- Say **no** to adding a Postgres database - we're using Neon instead.
- This registers the app but doesn't deploy yet (`--no-deploy`), so
  you can set secrets first.

### 5. Set secrets (env vars)

Do NOT put these in `fly.toml` (that file is committed to git). Set
them as encrypted secrets instead:

```
fly secrets set \
  BOT_TOKEN="<your bot token>" \
  CHAT_ID="<your chat id>" \
  DATABASE_URL="<neon connection string>" \
  KIWI_API_KEY="<if you use it>" \
  AMADEUS_CLIENT_ID="<if you use it>" \
  AMADEUS_CLIENT_SECRET="<if you use it>" \
  DUFFEL_API_KEY="<if you use it>" \
  SKYSCANNER_API_KEY="<if you use it>"
```

Only include the ones you actually use - check `.env.example` for the
full list (Twilio/WhatsApp vars too, if applicable).

### 6. Deploy

```
fly deploy
```

Watch the build logs - the Playwright/Chromium install step takes a
few minutes on first build, same as it would anywhere else.

### 7. Verify

```
fly logs
```

You should see the bot's normal startup logs (no crash loop). Message
it on Telegram - `/status` should respond, and the scheduler should
run its next hourly check on schedule.

### 8. Decommission Railway

Once Fly is confirmed stable for a day or two, delete the Railway
project.
