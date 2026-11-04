from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

WARSAW = ZoneInfo("Europe/Warsaw")


def utc_now() -> datetime:
    """Return the current UTC time (patch point for tests)."""
    return datetime.now(UTC)


def local_today(now: datetime | None = None) -> date:
    """Return today's date in the Europe/Warsaw business timezone."""
    return (now or utc_now()).astimezone(WARSAW).date()


def local_range(first: date, last_exclusive: date) -> tuple[datetime, datetime]:
    """UTC instants bounding Warsaw calendar days [first, last_exclusive)."""

    def start(d: date) -> datetime:
        return datetime(d.year, d.month, d.day, tzinfo=WARSAW).astimezone(UTC)

    return start(first), start(last_exclusive)


def local_date(moment: datetime) -> date:
    """Return the Europe/Warsaw calendar date of a timestamp."""
    return moment.astimezone(WARSAW).date()
