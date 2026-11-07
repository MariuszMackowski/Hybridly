"""Unified history feed: strength workouts and cardio activities, newest first."""

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, defer

from app.activities.models import Activity
from app.activities.schemas import ActivitySummary
from app.db import get_db
from app.load.service import workout_loads
from app.time import local_date, local_range
from app.workouts.models import Workout
from app.workouts.service import list_summaries

router = APIRouter(tags=["history"])
Kind = Literal["all", "gym", "run", "walk", "other"]


class HistoryItem(BaseModel):
    """One row of the history list (fields not relevant to the kind are null)."""

    kind: Literal["workout", "activity"]
    id: int
    started_at: datetime
    title: str | None
    sport: str
    duration_s: int | None = None
    distance_m: float | None = None
    avg_pace_s_per_km: float | None = None
    avg_speed: float | None = None
    avg_hr: int | None = None
    training_load: int | None = None
    exercise_count: int | None = None
    set_count: int | None = None
    pr_count: int | None = None


def _workouts(db: Session, count: int, between=None) -> list[HistoryItem]:
    """Newest strength workouts as history items, with their training load."""
    summaries = list_summaries(db, count, 0, between)
    loads = workout_loads(db, [w.id for w in summaries])
    return [
        HistoryItem(
            kind="workout",
            id=w.id,
            started_at=w.started_at,
            title=w.title or w.template_name,
            sport="gym",
            duration_s=int((w.ended_at - w.started_at).total_seconds()) if w.ended_at else None,
            exercise_count=w.exercise_count,
            set_count=w.set_count,
            pr_count=w.pr_count,
            training_load=loads.get(w.id),
        )
        for w in summaries
    ]


def _activities(db: Session, count: int, kind: Kind, between=None) -> list[HistoryItem]:
    """Newest cardio activities (optionally one sport group) as history items."""
    query = (
        select(Activity)
        .options(defer(Activity.streams))
        .order_by(Activity.started_at.desc())
        .limit(count)
    )
    if between:
        query = query.where(Activity.started_at >= between[0], Activity.started_at < between[1])
    if kind in ("run", "walk"):
        query = query.where(Activity.sport == kind)
    elif kind == "other":
        query = query.where(Activity.sport.not_in(("run", "walk")))
    items = []
    for activity in db.scalars(query):
        summary = ActivitySummary.model_validate(activity)
        items.append(
            HistoryItem(
                kind="activity",
                title=summary.name,
                **summary.model_dump(
                    include={
                        "id",
                        "started_at",
                        "sport",
                        "duration_s",
                        "distance_m",
                        "avg_pace_s_per_km",
                        "avg_speed",
                        "avg_hr",
                        "training_load",
                    }
                ),
            )
        )
    return items


@router.get("/history", response_model=list[HistoryItem])
def history(
    kind: Kind = "all",
    day: date | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Merged feed; each source supplies its newest offset+limit rows, then one page is cut."""
    needed = offset + limit
    between = local_range(day, day + timedelta(days=1)) if day else None
    items: list[HistoryItem] = []
    if kind in ("all", "gym"):
        items += _workouts(db, needed, between)
    if kind != "gym":
        items += _activities(db, needed, kind, between)
    items.sort(key=lambda i: i.started_at, reverse=True)
    return items[offset:needed]


class CalendarDay(BaseModel):
    """Kinds of training done on one local day."""

    day: date
    kinds: list[str]


KIND_ORDER = ("gym", "run", "walk", "other")


@router.get("/history/calendar", response_model=list[CalendarDay])
def calendar(month: str = Query(pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db)):
    """Days of a month (Europe/Warsaw) that have workouts or activities."""
    first = date.fromisoformat(f"{month}-01")
    after = (first + timedelta(days=32)).replace(day=1)
    start, end = local_range(first, after)
    kinds: dict[date, set[str]] = defaultdict(set)
    workouts = select(Workout.started_at).where(
        Workout.started_at >= start, Workout.started_at < end
    )
    for (started,) in db.execute(workouts):
        kinds[local_date(started)].add("gym")
    activities = select(Activity.started_at, Activity.sport).where(
        Activity.started_at >= start, Activity.started_at < end
    )
    for started, sport in db.execute(activities):
        kinds[local_date(started)].add(sport if sport in ("run", "walk") else "other")
    return [
        CalendarDay(day=d, kinds=[k for k in KIND_ORDER if k in kinds[d]]) for d in sorted(kinds)
    ]
