"""Everything the Today screen shows besides the strength template."""

from datetime import date, timedelta

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.activities.models import Activity
from app.coros.models import CorosDaily
from app.plans.router import SessionOut, session_out
from app.plans.service import sessions_on, week_of
from app.routines.router import RoutineOut, done_on, routine_out, routines_for_weekday
from app.time import local_range

STRENGTH_HINT = "Cutback/taper week: drop 1 set from main lifts."


class WeekInfo(BaseModel):
    """Plan week summary with distance run so far."""

    week: int
    phase: str | None
    flags: list[str]
    target_km: float | None
    done_km: float


class TodayRoutine(BaseModel):
    """Routine planned for today and whether it is ticked."""

    routine: RoutineOut
    done: bool


class TodayExtras(BaseModel):
    """Plan, routines and recovery for one day."""

    runs: list[SessionOut] = []
    week: WeekInfo | None = None
    day_notes: list[str] = []
    routines: list[TodayRoutine] = []
    recovery: dict | None = None
    strength_hint: str | None = None


def _run_km(db: Session, monday: date) -> float:
    """Kilometres run in the Warsaw week starting on monday."""
    start, end = local_range(monday, monday + timedelta(days=7))
    meters = db.scalar(
        select(func.coalesce(func.sum(Activity.distance_m), 0)).where(
            Activity.sport == "run", Activity.started_at >= start, Activity.started_at < end
        )
    )
    return round(float(meters) / 1000, 1)


def build_today(db: Session, day: date) -> TodayExtras:
    """Assemble the Today data for a calendar day."""
    extras = TodayExtras(runs=[session_out(db, s) for s in sessions_on(db, day)])
    week = week_of(db, day)
    if week is not None and day < week.start + timedelta(days=7):
        extras.week = WeekInfo(
            week=week.week,
            phase=week.phase,
            flags=list(week.flags or []),
            target_km=week.target_km,
            done_km=_run_km(db, week.start),
        )
        extras.day_notes = [n["text"] for n in week.day_notes or [] if n["date"] == day.isoformat()]
        if {"cutback", "taper"} & set(week.flags or []):
            extras.strength_hint = STRENGTH_HINT
    done = done_on(db, day)
    extras.routines = [
        TodayRoutine(routine=routine_out(db, r), done=r.id in done)
        for r in routines_for_weekday(db, day.weekday())
    ]
    recovery = db.scalar(
        select(CorosDaily)
        .where(CorosDaily.kind == "recovery", CorosDaily.day <= day)
        .order_by(CorosDaily.day.desc())
        .limit(1)
    )
    extras.recovery = recovery.data if recovery else None
    return extras
