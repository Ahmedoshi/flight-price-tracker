"""Shared pytest fixtures.

Sets required env vars BEFORE any `app.*` module is imported, since
app.config.settings builds a module-level `settings = Settings()` at
import time that would otherwise raise a validation error the moment
anything in the app package is imported during test collection.
"""

import os

os.environ.setdefault("BOT_TOKEN", "test-bot-token")
os.environ.setdefault("CHAT_ID", "test-chat-id")

import pytest


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """An isolated, freshly-initialized SQLite database for a single
    test - nothing here ever touches the real data/flights.db."""

    import app.database.database as dbmod

    db_path = tmp_path / "test_flights.db"
    monkeypatch.setattr(dbmod, "DB_PATH", db_path)
    dbmod.initialize_database()

    return dbmod


@pytest.fixture(autouse=True)
def reset_settings():
    """Some tests deliberately mutate global `settings` fields (e.g.
    quiet hours). Snapshot every field before the test and restore it
    after, so tests can't leak state into each other regardless of
    execution order."""

    from app.config.settings import settings

    original = dict(settings.__dict__)

    yield

    for key, value in original.items():
        setattr(settings, key, value)
