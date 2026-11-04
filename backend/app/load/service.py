"""Collect training events from the database and expose recovery + muscle fatigue."""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.activities.models import Activity
from app.coros.models import CorosDaily
from app.db import get_db
from app.exercises.models import Exercise
from app.load.model import (
    Event,
    activity_load,
    capacity_from_daily,
    levels_from_scores,
    muscle_scores,
    recovery,
    region_recovery,
    strength_set_load,
)
from app.time import local_date, utc_now
from app.workouts.models import Workout, WorkoutExercise, WorkoutSet

router = APIRouter(tags=["recovery"])
WINDOW_DAYS = 42
DAILY_DAYS = 14
LEG_MUSCLES = ("quads", "hamstrings", "glutes", "calves")
RUN_TL_PER_SET = {"walk": 50.0}  # COROS TL per leg-muscle hard-set equivalent
DEFAULT_TL_PER_SET = 25.0


class DayLoad(BaseModel):
    """Load of one day split by kind."""

    day: date
    strength: float
    cardio: float


class RegionOut(BaseModel):
    """Recovery of one body region (upper / lower)."""

    region: str
    recovery_pct: int
    hours_to_ready: int


class RecoveryOut(BaseModel):
    """Recovery state for the Today card and the Recovery page."""

    recovery_pct: int
    hours_to_full: int
    acute: float
    capacity: float
    coros_pct: int | None
    muscles: dict[str, float]
    regions: list[RegionOut]
    daily: list[DayLoad]


def _strength_events(db: Session, since: datetime) -> list[tuple[Event, str]]:
    """One event per working set, with muscle hard-set equivalents."""
    best = dict(
        db.execute(
            select(WorkoutExercise.exercise_id, func.max(WorkoutSet.e1rm_kg))
            .join(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
            .group_by(WorkoutExercise.exercise_id)
        ).all()
    )
    rows = db.execute(
        select(WorkoutSet, Exercise, Workout.started_at)
        .join(WorkoutExercise, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .join(Exercise, WorkoutExercise.exercise_id == Exercise.id)
        .where(Workout.started_at >= since, WorkoutSet.is_warmup.is_(False))
    ).all()
    events = []
    for workout_set, exercise, started_at in rows:
        top = best.get(exercise.id)
        rel = float(workout_set.e1rm_kg) / float(top) if workout_set.e1rm_kg and top else None
        sides = 2 if exercise.per_side else 1
        hard = (rel or 0.6) * sides
        muscles = {m: hard for m in exercise.primary_muscles}
        for m in exercise.secondary_muscles:
            muscles[m] = muscles.get(m, 0.0) + 0.5 * hard
        load = strength_set_load(exercise.load_factor, rel, exercise.per_side)
        events.append((Event(started_at, load, muscles), "strength"))
    return events


def _cardio_events(db: Session, since: datetime) -> list[tuple[Event, str]]:
    """Activities with COROS (or estimated) load; legs take the impact."""
    events = []
    for activity in db.scalars(select(Activity).where(Activity.started_at >= since)):
        load = activity_load(activity.sport, activity.training_load, activity.duration_s)
        per_set = RUN_TL_PER_SET.get(activity.sport, DEFAULT_TL_PER_SET)
        muscles = {m: load / per_set for m in LEG_MUSCLES}
        events.append((Event(activity.started_at, load, muscles), "cardio"))
    return events


def _daily(events: list[tuple[Event, str]], first: date, days: int) -> dict[date, DayLoad]:
    """Load per Warsaw day split into strength / cardio."""
    out = {
        first + timedelta(days=i): DayLoad(day=first + timedelta(days=i), strength=0, cardio=0)
        for i in range(days)
    }
    for event, kind in events:
        bucket = out.get(local_date(event.at))
        if bucket is not None:
            setattr(bucket, kind, round(getattr(bucket, kind) + event.load, 1))
    return out


@router.get("/recovery", response_model=RecoveryOut)
def get_recovery(db: Session = Depends(get_db)):
    """Overall recovery %, muscle fatigue levels and recent daily load."""
    return current_state(db)


def current_state(db: Session) -> RecoveryOut:
    """Recovery state right now."""
    now = utc_now()
    today = local_date(now)
    since = now - timedelta(days=WINDOW_DAYS)
    events = _strength_events(db, since) + _cardio_events(db, since)
    window = _daily(events, today - timedelta(days=WINDOW_DAYS - 1), WINDOW_DAYS)
    capacity = capacity_from_daily([d.strength + d.cardio for d in window.values()])
    state = recovery([e for e, _ in events], now, capacity)
    scores = muscle_scores([e for e, _ in events], now)
    coros = db.scalar(
        select(CorosDaily)
        .where(CorosDaily.kind == "recovery", CorosDaily.day <= today)
        .order_by(CorosDaily.day.desc())
        .limit(1)
    )
    return RecoveryOut(
        recovery_pct=state.recovery_pct,
        hours_to_full=state.hours_to_full,
        acute=state.acute,
        capacity=state.capacity,
        coros_pct=(coros.data or {}).get("recovery_pct") if coros else None,
        muscles=levels_from_scores(scores),
        regions=[RegionOut(**vars(r)) for r in region_recovery(scores)],
        daily=list(window.values())[-DAILY_DAYS:],
    )
