from datetime import UTC, date, datetime
from functools import cache
from zoneinfo import ZoneInfo

from app.config import get_settings


@cache
def local_tz() -> ZoneInfo:
    """The app's calendar timezone (TIMEZONE env, default Europe/Warsaw)."""
    return ZoneInfo(get_settings().timezone)


def utc_now() -> datetime:
    """Return the current UTC time (patch point for tests)."""
    return datetime.now(UTC)


def local_today(now: datetime | None = None) -> date:
    """Return today's date in the app timezone."""
    return (now or utc_now()).astimezone(local_tz()).date()


def local_range(first: date, last_exclusive: date) -> tuple[datetime, datetime]:
    """UTC instants bounding local calendar days [first, last_exclusive)."""

    def start(d: date) -> datetime:
        return datetime(d.year, d.month, d.day, tzinfo=local_tz()).astimezone(UTC)

    return start(first), start(last_exclusive)


def local_date(moment: datetime) -> date:
    """Return the local calendar date of a timestamp."""
    return moment.astimezone(local_tz()).date()
