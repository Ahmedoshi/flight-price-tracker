from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from the .env file.
    """

    bot_token: str
    chat_id: str = ""
    check_interval: int = 2
    database_path: str = "data/flights.db"
    timezone: str = "Asia/Riyadh"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()

PROJECT_ROOT = Path(__file__).resolve().parents[2]