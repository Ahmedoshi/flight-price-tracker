from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    bot_token: str
    chat_id: str

    check_interval: int = 1

    database_path: str = "data/flights.db"

    # Postgres connection string (Roadmap Phase 5). When set (Railway
    # injects this automatically once a Postgres plugin is attached to
    # the project), app/database/database.py uses Postgres instead of
    # the local SQLite file - the two backends share the exact same
    # public function signatures, so nothing above the database layer
    # needs to know which one is active. Leave unset for local/dev use
    # (falls back to SQLite at database_path).
    database_url: str = ""

    kiwi_api_key: str = ""

    # Extra providers - optional, no-op until keys are supplied.
    amadeus_client_id: str = ""
    amadeus_client_secret: str = ""
    duffel_api_key: str = ""

    # This is actually a RapidAPI key for the unofficial "Sky Scrapper"
    # API (rapidapi.com/apiheya/api/sky-scrapper), not an official
    # Skyscanner Partner API credential - Skyscanner has no self-serve
    # signup. See app/providers/skyscanner_flights.py for setup notes
    # and an important caveat about its very small free-tier quota.
    skyscanner_api_key: str = ""

    timezone: str = "Asia/Riyadh"

    log_level: str = "INFO"

    # --- WhatsApp notifications (via Twilio) ---
    # twilio_sid/twilio_token match the TWILIO_SID/TWILIO_TOKEN
    # variable names already used in Railway.
    twilio_sid: str = ""
    twilio_token: str = ""

    # Twilio's own WhatsApp-enabled sender number (the sandbox number
    # while testing, e.g. +14155238886, or your approved WhatsApp
    # Business sender) - with or without a leading "whatsapp:" prefix,
    # either is accepted. wa_from is preferred if set (this Railway
    # project already had it holding the real sandbox WhatsApp number);
    # twilio_phone is a fallback for a plain Twilio number that isn't
    # actually WhatsApp-enabled, so don't rely on it alone.
    wa_from: str = ""
    twilio_phone: str = ""

    # The recipient's own WhatsApp number (your phone), in E.164
    # format e.g. +9665XXXXXXXX, with or without a "whatsapp:" prefix.
    # If using the Twilio Sandbox, this number must have already sent
    # the sandbox's "join <code>" message before it can receive
    # anything - see https://www.twilio.com/docs/whatsapp/sandbox.
    whatsapp_to: str = ""

    # --- Notification rule engine (Sprint 2 / Phase 1) ---

    # Alert if the price dropped by at least this % since the last check.
    price_drop_threshold_pct: float = 10.0

    # A "new lowest" that beats the previous lowest by at least this % is
    # treated as an escalated alert (bypasses quiet hours).
    escalation_drop_threshold_pct: float = 30.0

    # A "flash deal": price is at least this % below the route's own
    # historical average (over analytics_window_days), regardless of
    # whether it's a new all-time low or a big drop since the last
    # check - catches a sudden, unusually cheap fare even if the route
    # is normally volatile enough that it isn't a record low.
    flash_deal_drop_pct: float = 25.0

    # Duplicate-alert suppression: don't re-notify unless the price has
    # moved by at least this % since the last price we actually alerted
    # on. Without this, a flight sitting under its target price (or
    # bouncing by a dollar or two) re-fires an alert on every single
    # scheduled check.
    dedup_tolerance_pct: float = 3.0

    # Suppress (non-escalated) alerts between these local hours.
    # Equal values (default) disables quiet hours entirely.
    quiet_hours_start: int = 0
    quiet_hours_end: int = 0

    # How many days of price_history back to consider for trend/analytics
    # and the buy-now recommendation.
    analytics_window_days: int = 45

    # A "rebound" alert (price returned after increasing) needs both
    # the prior rise and the current fall to be at least this % each,
    # so a couple of dollars of noise doesn't count as a real reversal.
    rebound_min_change_pct: float = 3.0

    # --- Provider reliability (Roadmap Phase 1) ---

    # Per-attempt timeout for a single provider's search() call. A slow
    # provider shouldn't be able to stall the whole multi-provider
    # search indefinitely.
    provider_timeout_seconds: float = 15.0

    # How many extra attempts after the first, on timeout/network
    # errors only (not on a provider's own "no flights found" result,
    # which isn't a failure). 2 retries = 3 attempts total.
    provider_max_retries: int = 2

    # Base delay before the first retry; doubles each subsequent retry
    # (1s, 2s, 4s, ...) - standard exponential backoff.
    provider_retry_backoff_seconds: float = 1.0

    # After this many consecutive failed calls, a provider is marked
    # "offline" and skipped entirely (instead of spending a timeout +
    # retries on every single check) until the cooldown below passes.
    provider_failure_threshold: int = 5

    # How long a provider stays auto-disabled after tripping the
    # failure threshold before it's given another chance.
    provider_disable_cooldown_minutes: float = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()

PROJECT_ROOT = Path(__file__).resolve().parents[2]