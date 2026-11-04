"""Link runs to the planned sessions they fulfil."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.activities.models import Activity
from app.plans.models import PlanSession
from app.plans.service import sessions_on
from app.time import local_date, local_range


def _free_session(db: Session, day: date) -> PlanSession | None:
    """First unmatched planned session on a day (plan in effect)."""
    return next((s for s in sessions_on(db, day) if s.activity_id is None), None)


def match_activity(db: Session, activity: Activity) -> PlanSession | None:
    """Same-day session first, else the day before, else the day after."""
    if activity.sport != "run":
        return None
    if db.scalar(select(PlanSession.id).where(PlanSession.activity_id == activity.id)):
        return None
    day = local_date(activity.started_at)
    for candidate in (day, day - timedelta(days=1), day + timedelta(days=1)):
        session = _free_session(db, candidate)
        if session is not None:
            session.activity_id = activity.id
            db.flush()
            return session
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
