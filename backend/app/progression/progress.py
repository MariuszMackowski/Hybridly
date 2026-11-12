from collections import defaultdict
from datetime import date, datetime, timedelta

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.bodyweight.service import bodyweight_lookup
from app.exercises.models import Exercise
from app.time import local_date
from app.workouts.models import Workout, WorkoutExercise, WorkoutSet


class ProgressSession(BaseModel):
    """Per-workout summary of an exercise's working reps sets."""

    workout_id: int
    started_at: datetime
    grip: str | None
    best_e1rm_kg: float | None
    top_weight_kg: float
    top_reps: int
    volume_kg: float


class ProgressWeek(BaseModel):
    """Working-set volume in one Monday-based week."""

    week_start: date
    volume_kg: float
    sets: int


class ExerciseProgress(BaseModel):
    """Charts data for one exercise, optionally limited to one grip."""

    grips: list[str]
    sessions: list[ProgressSession]
    weeks: list[ProgressWeek]


def _working(entry: WorkoutExercise) -> list[WorkoutSet]:
    """Working sets that have reps."""
    return [s for s in entry.sets if s.reps and not s.is_warmup]


def _session(entry: WorkoutExercise, sets: list[WorkoutSet], extra_kg: float) -> ProgressSession:
    """Summarise one entry; extra_kg is the bodyweight added for bodyweight exercises."""
    top = max(sets, key=lambda s: (float(s.weight_kg or 0), s.reps))
    e1rms = [float(s.e1rm_kg) for s in sets if s.e1rm_kg is not None]
    return ProgressSession(
        workout_id=entry.workout_id,
        started_at=entry.workout.started_at,
        grip=entry.grip,
        best_e1rm_kg=max(e1rms) if e1rms else None,
        top_weight_kg=float(top.weight_kg or 0),
        top_reps=top.reps,
        volume_kg=round(sum((float(s.weight_kg or 0) + extra_kg) * s.reps for s in sets), 1),
    )


def _weeks(sessions: list[ProgressSession], set_counts: list[int]) -> list[ProgressWeek]:
    """Sum session volume and set counts into local Monday-based weeks; gaps become zero weeks."""
    volume: dict[date, float] = defaultdict(float)
    count: dict[date, int] = defaultdict(int)
    for session, n in zip(sessions, set_counts, strict=True):
        day = local_date(session.started_at)
        monday = day - timedelta(days=day.weekday())
        volume[monday] += session.volume_kg
        count[monday] += n
    if not volume:
        return []
    weeks, week, last = [], min(volume), max(volume)
    while week <= last:
        weeks.append(
            ProgressWeek(week_start=week, volume_kg=round(volume[week], 1), sets=count[week])
        )
        week += timedelta(days=7)
    return weeks


def exercise_progress(db: Session, exercise: Exercise, grip: str | None) -> ExerciseProgress:
    """Chronological sessions and weekly volume of an exercise (all grips when grip is None)."""
    entries = list(
        db.scalars(
            select(WorkoutExercise)
            .join(Workout)
            .where(WorkoutExercise.exercise_id == exercise.id)
            .order_by(Workout.started_at, WorkoutExercise.position)
            .options(selectinload(WorkoutExercise.sets), selectinload(WorkoutExercise.workout))
        )
    )
    grips = sorted({e.grip for e in entries if e.grip})
    bodyweight = bodyweight_lookup(db) if exercise.is_bodyweight else None
    sessions: list[ProgressSession] = []
    set_counts: list[int] = []
    for entry in entries:
        sets = _working(entry)
        if not sets or (grip is not None and entry.grip != grip):
            continue
        extra = (bodyweight(local_date(entry.workout.started_at)) or 0) if bodyweight else 0
        sessions.append(_session(entry, sets, extra))
        set_counts.append(len(sets))
    return ExerciseProgress(grips=grips, sessions=sessions, weeks=_weeks(sessions, set_counts))
