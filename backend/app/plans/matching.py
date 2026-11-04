"""Link runs to the planned sessions they fulfil."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.activities.models import Activity
from app.plans.models import PlanSession
from app.plans.service import sessions_on
from app.time import local_date, local_range

NEIGHBOR_DISTANCE_RATIO = (0.5, 2.0)


def _plausible(session: PlanSession, activity: Activity) -> bool:
    """For a run on a neighbouring day, distance must be roughly what was planned."""
    if not session.distance_km or not activity.distance_m:
        return True
    ratio = activity.distance_m / (session.distance_km * 1000)
    return NEIGHBOR_DISTANCE_RATIO[0] <= ratio <= NEIGHBOR_DISTANCE_RATIO[1]


def _free_session(db: Session, day: date, activity: Activity | None = None) -> PlanSession | None:
    """First unmatched planned session on a day; with `activity`, only plausible ones."""
    return next(
        (
            s
            for s in sessions_on(db, day)
            if s.activity_id is None and (activity is None or _plausible(s, activity))
        ),
        None,
    )


def _distance_error(session: PlanSession, activity: Activity) -> float:
    """How far a run's distance is from the plan (0 when unknown)."""
    if not session.distance_km or not activity.distance_m:
        return 0.0
    return abs(activity.distance_m - session.distance_km * 1000)


def _claim(db: Session, session: PlanSession, activity: Activity) -> PlanSession:
    """Give the session to the activity and re-home whoever held it (without stealing)."""
    previous = session.activity_id
    session.activity_id = activity.id
    db.flush()
    if previous is not None and previous != activity.id:
        displaced = db.get(Activity, previous)
        if displaced is not None:
            match_activity(db, displaced, allow_steal=False)
    return session


def _same_day_contested(db: Session, day: date, activity: Activity) -> PlanSession | None:
    """A same-day session held by a neighbour-day run, or by a same-day run further from plan."""
    for session in sessions_on(db, day):
        holder = db.get(Activity, session.activity_id) if session.activity_id else None
        if holder is None:
            continue
        if local_date(holder.started_at) != day:
            return session
        if _distance_error(session, activity) < _distance_error(session, holder):
            return session
    return None


def match_activity(db: Session, activity: Activity, allow_steal: bool = True) -> PlanSession | None:
    """Same-day session first (may take it back from a worse holder), else day before/after."""
    if activity.sport != "run":
        return None
    if db.scalar(select(PlanSession.id).where(PlanSession.activity_id == activity.id)):
        return None
    day = local_date(activity.started_at)
    session = _free_session(db, day)
    if session is None and allow_steal:
        session = _same_day_contested(db, day, activity)
    if session is not None:
        return _claim(db, session, activity)
    for offset in (-1, 1):
        session = _free_session(db, day + timedelta(days=offset), activity)
        if session is not None:
            return _claim(db, session, activity)
    return None


def rematch_from(db: Session, first_day: date) -> None:
    """Re-run matching for runs from a day on (after a plan import), oldest first."""
    start, _ = local_range(first_day - timedelta(days=1), first_day)
    runs = db.scalars(
        select(Activity)
        .where(Activity.sport == "run", Activity.started_at >= start)
        .order_by(Activity.started_at)
    )
    for activity in runs:
        match_activity(db, activity)


def link(db: Session, session: PlanSession, activity_id: int | None) -> None:
    """Manually (re)assign or clear the activity of a session."""
    if activity_id is not None:
        for other in db.scalars(select(PlanSession).where(PlanSession.activity_id == activity_id)):
            other.activity_id = None
        db.flush()
    session.activity_id = activity_id
    db.commit()
