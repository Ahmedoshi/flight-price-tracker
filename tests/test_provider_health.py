"""Tests for per-provider reliability tracking (Roadmap Phase 1)."""

from app.config.settings import settings
from app.services import provider_health


def test_unknown_provider_is_not_disabled(temp_db):

    assert provider_health.is_disabled("NeverSeenBefore") is False


def test_record_success_updates_stats(temp_db):

    provider_health.record_success("Google Flights", elapsed_ms=2300)

    stats = provider_health.get_stats("Google Flights")

    assert stats["total_checks"] == 1
    assert stats["success_rate_pct"] == 100.0
    assert stats["avg_response_seconds"] == 2.3
    assert stats["offline"] is False


def test_record_failure_increments_consecutive_failures(temp_db):

    provider_health.record_failure("Duffel", "boom")
    stats = provider_health.get_stats("Duffel")

    assert stats["total_checks"] == 1
    assert stats["consecutive_failures"] == 1
    assert stats["success_rate_pct"] == 0.0
    assert stats["avg_response_seconds"] is None  # no successful calls yet
    assert stats["offline"] is False  # hasn't tripped the threshold yet


def test_provider_auto_disables_after_threshold(temp_db):

    settings.provider_failure_threshold = 3

    for _ in range(3):
        provider_health.record_failure("FlakyProvider", "boom")

    assert provider_health.is_disabled("FlakyProvider") is True

    stats = provider_health.get_stats("FlakyProvider")
    assert stats["offline"] is True


def test_success_immediately_clears_disabled_state(temp_db):

    settings.provider_failure_threshold = 2

    provider_health.record_failure("Recovering", "boom")
    provider_health.record_failure("Recovering", "boom")

    assert provider_health.is_disabled("Recovering") is True

    provider_health.record_success("Recovering", elapsed_ms=500)

    assert provider_health.is_disabled("Recovering") is False

    stats = provider_health.get_stats("Recovering")
    assert stats["consecutive_failures"] == 0


def test_get_all_stats_includes_every_recorded_provider(temp_db):

    provider_health.record_success("Google Flights", 1000)
    provider_health.record_success("Duffel", 1500)

    all_stats = provider_health.get_all_stats()

    assert set(all_stats.keys()) == {"Google Flights", "Duffel"}
