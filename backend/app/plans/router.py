from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.activities.models import Activity
from app.db import get_db
from app.plans import matching
from app.plans.compare import Comparison, compare
from app.plans.format import COACH_INSTRUCTIONS, PlanFormatError
from app.plans.models import PlanSession, PlanWeek, TrainingPlan
from app.plans.service import import_plan
from app.time import local_today

router = APIRouter(prefix="/plans", tags=["plans"])


class SessionOut(BaseModel):
    """Planned run with its match and comparison."""

    id: int
    date: date
    type: str
    title: str
    description: str
    distance_km: float | None
    pace_min_s: int | None
    pace_max_s: int | None
    hr_min: int | None
    hr_max: int | None
    intervals: dict | None
    activity_id: int | None
    comparison: Comparison | None = None


class WeekOut(BaseModel):
    """Plan week with sessions."""

    week: int
    start: date
    phase: str | None
    flags: list[str]
    target_km: float | None
    note: str | None
    day_notes: list
    sessions: list[SessionOut]


class PlanOut(BaseModel):
    """Plan in effect today."""

    id: int
    name: str
    goal: dict | None
    notes: list
    effective_from: date
    weeks: list[WeekOut]


def session_out(db: Session, session: PlanSession) -> SessionOut:
    """Serialize a session, comparing with its matched activity."""
    out = SessionOut.model_validate(session, from_attributes=True)
    if session.activity_id:
        activity = db.scalar(
            select(Activity)
            .where(Activity.id == session.activity_id)
            .options(selectinload(Activity.laps))
        )
        if activity is not None:
            out.comparison = compare(session, activity)
    return out


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_plan_endpoint(request: Request, db: Session = Depends(get_db)) -> dict:
    """Import a plan YAML sent as the raw request body or as a multipart `file`."""
    if request.headers.get("content-type", "").startswith("multipart/"):
        form = await request.form()
        text = (await form["file"].read()).decode("utf-8")
    else:
        text = (await request.body()).decode("utf-8")
    try:
        plan = import_plan(db, text, local_today())
    except PlanFormatError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    sessions = sum(len(w.sessions) for w in plan.weeks)
    return {
        "id": plan.id,
        "name": plan.name,
        "weeks": len(plan.weeks),
        "sessions": sessions,
        "effective_from": plan.effective_from.isoformat(),
    }


@router.get("/active", response_model=PlanOut | None)
def active_plan(db: Session = Depends(get_db)):
    """The plan in effect today (or the newest one if none applies yet)."""
    today = local_today()
    plan = db.scalar(
        select(TrainingPlan)
        .where(TrainingPlan.effective_from <= today)
        .order_by(TrainingPlan.imported_at.desc())
        .limit(1)
    ) or db.scalar(select(TrainingPlan).order_by(TrainingPlan.imported_at.desc()).limit(1))
    if plan is None:
        return None
    weeks = db.scalars(
        select(PlanWeek)
        .where(PlanWeek.plan_id == plan.id)
        .order_by(PlanWeek.start)
        .options(selectinload(PlanWeek.sessions))
    )
    return PlanOut(
        id=plan.id,
        name=plan.name,
        goal=plan.goal,
        notes=plan.notes or [],
        effective_from=plan.effective_from,
        weeks=[
            WeekOut(
                **{
                    k: getattr(w, k)
                    for k in ("week", "start", "phase", "flags", "target_km", "note")
                },
                day_notes=w.day_notes or [],
                sessions=[session_out(db, s) for s in w.sessions],
            )
            for w in weeks
        ],
    )


@router.get("/instructions")
def instructions() -> dict[str, str]:
    """Format description + example to paste to the AI coach."""
    return {"text": COACH_INSTRUCTIONS}


class LinkIn(BaseModel):
    """Activity to attach (null to detach)."""

    activity_id: int | None


@router.post("/sessions/{session_id}/link", response_model=SessionOut)
def link_session(session_id: int, data: LinkIn, db: Session = Depends(get_db)):
    """Manually set which run fulfilled a planned session."""
    session = db.get(PlanSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    if data.activity_id is not None and db.get(Activity, data.activity_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown activity")
    matching.link(db, session, data.activity_id)
    return session_out(db, session)
