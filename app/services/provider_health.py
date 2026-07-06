"""Per-provider reliability tracking (Roadmap Phase 1).

Every provider call made through ProviderManager reports its outcome
here. This lets the bot:

  - Show per-provider average response time and success rate (Status
    screen).
  - Auto-disable a provider that's failing repeatedly, instead of
    spending a full timeout + retries on it every single check (see
    is_disabled() / consecutive-failure threshold below).

Stats are stored in the provider_health SQLite table (survives
restarts via Railway's persistent volume), one row per provider name
(BaseProvider.NAME).
"""

from datetime import datetime, timedelta, timezone

from app.config.settings import settings
from app.database.database import (
    get_all_provider_health,
    get_provider_health,
    upsert_provider_health,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(dt_str: str | None) -> datetime | None:

    if not dt_str:
        return None

    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return None


def is_disabled(provider: str) -> bool:
    """Whether `provider` is currently auto-disabled (in cooldown
    after tripping the consecutive-failure threshold)."""

    row = get_provider_health(provider)

    if row is None:
        return False

    disabled_until = _parse(row["disabled_until"])

    return disabled_until is not None and _now() < disabled_until


def record_success(provider: str, elapsed_ms: float):

    row = get_provider_health(provider) or _blank_row(provider)

    upsert_provider_health(
        provider=provider,
        total_checks=row["total_checks"] + 1,
        success_count=row["success_count"] + 1,
        success_response_ms=row["success_response_ms"] + elapsed_ms,
        consecutive_failures=0,
        disabled_until=None,  # a success always lifts any disable
        last_error=None,
        last_checked_at=_now().isoformat(),
    )


def record_failure(provider: str, error: str):

    row = get_provider_health(provider) or _blank_row(provider)

    consecutive_failures = row["consecutive_failures"] + 1
    disabled_until = _parse(row["disabled_until"])

    if consecutive_failures >= settings.provider_failure_threshold:

        disabled_until = _now() + timedelta(
            minutes=settings.provider_disable_cooldown_minutes
        )

    upsert_provider_health(
        provider=provider,
        total_checks=row["total_checks"] + 1,
        success_count=row["success_count"],
        success_response_ms=row["success_response_ms"],
        consecutive_failures=consecutive_failures,
        disabled_until=disabled_until.isoformat() if disabled_until else None,
        last_error=(error or "")[:500],
        last_checked_at=_now().isoformat(),
    )


def _blank_row(provider: str) -> dict:

    return {
        "provider": provider,
        "total_checks": 0,
        "success_count": 0,
        "success_response_ms": 0.0,
        "consecutive_failures": 0,
        "disabled_until": None,
        "last_error": None,
        "last_checked_at": None,
    }


def get_stats(provider: str) -> dict:
    """Human-friendly stats for one provider - used by the Status
    screen. Always returns a dict (zeros/None if never checked)."""

    row = get_provider_health(provider) or _blank_row(provider)

    return _summarize(row)


def get_all_stats() -> dict[str, dict]:

    rows = get_all_provider_health()

    return {name: _summarize(row) for name, row in rows.items()}


def _summarize(row: dict) -> dict:

    total = row["total_checks"]
    successes = row["success_count"]

    success_rate_pct = (successes / total * 100) if total else None

    avg_response_seconds = (
        (row["success_response_ms"] / successes / 1000) if successes else None
    )

    disabled_until = _parse(row["disabled_until"])
    currently_disabled = disabled_until is not None and _now() < disabled_until

    return {
        "total_checks": total,
        "success_rate_pct": success_rate_pct,
        "avg_response_seconds": avg_response_seconds,
        "consecutive_failures": row["consecutive_failures"],
        "offline": currently_disabled,
        "disabled_until": disabled_until,
        "last_error": row["last_error"],
        "last_checked_at": row["last_checked_at"],
    }
