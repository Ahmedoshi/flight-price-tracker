from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    bot_token: str
    chat_id: str

    check_interval: int = 1

    database_path: str = "data/flights.db"

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
    # twilio_sid/twilio_token/twilio_phone match the TWILIO_SID/
    # TWILIO_TOKEN/TWILIO_PHONE variable names already used in
    # Railway. twilio_phone is Twilio's own WhatsApp-enabled sender
    # number (the sandbox number while testing, e.g. +14155238886, or
    # your approved WhatsApp Business sender) - with or without a
    # leading "whatsapp:" prefix, either is accepted.
    twilio_sid: str = ""
    twilio_token: str = ""
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()

PROJECT_ROOT = Path(__file__).resolve().parents[2]