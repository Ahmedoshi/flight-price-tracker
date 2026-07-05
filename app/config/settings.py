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
    skyscanner_api_key: str = ""

    timezone: str = "Asia/Riyadh"

    log_level: str = "INFO"

    # --- Notification rule engine (Sprint 2 / Phase 1) ---

    # Alert if the price dropped by at least this % since the last check.
    price_drop_threshold_pct: float = 10.0

    # A "new lowest" that beats the previous lowest by at least this % is
    # treated as an escalated alert (bypasses quiet hours).
    escalation_drop_threshold_pct: float = 30.0

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