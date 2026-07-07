"""Integration tests for _resilient_search (Roadmap Phase 1): timeout,
retry with backoff, and skipping calls entirely while a provider is
auto-disabled.
"""

import asyncio

import pytest

from app.config.settings import settings
from app.models.flight import Flight
from app.providers.provider_manager import _resilient_search
from app.services import provider_health


def _flight():

    return Flight(
        origin="RUH",
        destination="LIS",
        departure_date="2026-09-30",
        return_date="2026-10-20",
    )


class FlakyProvider:

    NAME = "FlakyTest"

    def __init__(self):
        self.calls = 0

    async def search(self, flight):
        self.calls += 1
        raise RuntimeError("simulated network error")


class SlowProvider:

    NAME = "SlowTest"

    async def search(self, flight):
        await asyncio.sleep(5)
        return []


class GoodProvider:

    NAME = "GoodTest"

    async def search(self, flight):
        await asyncio.sleep(0.01)
        return ["ok"]


@pytest.fixture(autouse=True)
def fast_retry_settings():
    """Keep retry/backoff/timeout tight so these tests run in
    milliseconds, not real minutes."""

    settings.provider_timeout_seconds = 0.2
    settings.provider_max_retries = 2
    settings.provider_retry_backoff_seconds = 0.01
    settings.provider_failure_threshold = 3
    settings.provider_disable_cooldown_minutes = 30


async def test_successful_call_records_health(temp_db):

    provider = GoodProvider()
    result = await _resilient_search(provider, _flight())

    assert result == ["ok"]

    stats = provider_health.get_stats("GoodTest")
    assert stats["success_rate_pct"] == 100.0


async def test_failing_call_retries_up_to_max_attempts(temp_db):

    provider = FlakyProvider()
    result = await _resilient_search(provider, _flight())

    assert result == []
    # max_retries=2 -> 3 total attempts for this one outer call
    assert provider.calls == 3


async def test_timeout_counts_as_a_failure(temp_db):

    provider = SlowProvider()
    result = await _resilient_search(provider, _flight())

    assert result == []

    stats = provider_health.get_stats("SlowTest")
    assert stats["consecutive_failures"] > 0


async def test_provider_stops_being_called_once_disabled(temp_db):

    provider = FlakyProvider()

    # 3 outer calls x 3 attempts each trips the failure_threshold=3
    for _ in range(3):
        await _resilient_search(provider, _flight())

    assert provider_health.is_disabled("FlakyTest") is True

    calls_before = provider.calls
    result = await _resilient_search(provider, _flight())

    assert result == []
    assert provider.calls == calls_before  # search() was never actually invoked


async def test_disabled_provider_is_reachable_again_after_cooldown(temp_db):

    settings.provider_disable_cooldown_minutes = 0  # expires immediately

    provider = FlakyProvider()

    for _ in range(3):
        await _resilient_search(provider, _flight())

    assert provider_health.is_disabled("FlakyTest") is False
