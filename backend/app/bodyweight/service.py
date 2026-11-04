from collections.abc import Callable
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bodyweight.models import BodyweightEntry


def bodyweight_lookup(db: Session) -> Callable[[date], float | None]:
    """Preload entries; the returned function gives the latest weight on or before a day,
    else the earliest known weight, else None."""
    entries = list(db.scalars(select(BodyweightEntry).order_by(BodyweightEntry.day)))

    def lookup(day: date) -> float | None:
        """Resolve bodyweight for a day using the preloaded entries."""
        if not entries:
            return None
        chosen = entries[0]
        for entry in entries:
            if entry.day > day:
                break
            chosen = entry
        return float(chosen.kg)

    return lookup


def bodyweight_on(db: Session, day: date) -> float | None:
    """Bodyweight valid for a single day (see bodyweight_lookup)."""
    return bodyweight_lookup(db)(day)
