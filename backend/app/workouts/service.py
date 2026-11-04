from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.exercises.models import Exercise
from app.workouts.models import Workout, WorkoutExercise, WorkoutSet
from app.workouts.schemas import (
    SetOut,
    WorkoutCreate,
    WorkoutExerciseOut,
    WorkoutOut,
    WorkoutSummary,
)
from app.workouts.stats import recompute_stats


class UnknownExerciseError(Exception):
    """Raised when a payload references a missing exercise."""


def _load_options():
    """Eager-load options for full workout trees."""
    return (
        selectinload(Workout.template),
        selectinload(Workout.exercises).selectinload(WorkoutExercise.sets),
        selectinload(Workout.exercises).selectinload(WorkoutExercise.exercise),
    )


def get_workout(db: Session, workout_id: int) -> Workout | None:
    """Load one workout with exercises and sets."""
    return db.scalar(select(Workout).where(Workout.id == workout_id).options(*_load_options()))


def _existing_id(db: Session, client_id) -> int | None:
    """Id of a workout already saved with this client_id."""
    return db.scalar(select(Workout.id).where(Workout.client_id == client_id))


def create_workout(db: Session, data: WorkoutCreate) -> tuple[Workout, bool]:
    """Store a workout; an already-used client_id returns the existing one (created=False)."""
    existing = _existing_id(db, data.client_id)
    if existing is not None:
        return get_workout(db, existing), False
    exercise_ids = {e.exercise_id for e in data.exercises}
    found = set(db.scalars(select(Exercise.id).where(Exercise.id.in_(exercise_ids))))
    if missing := exercise_ids - found:
        raise UnknownExerciseError(sorted(missing))
    workout = Workout(**data.model_dump(exclude={"exercises"}), source="app")
    for position, entry in enumerate(data.exercises):
        workout.exercises.append(
            WorkoutExercise(
                position=position,
                exercise_id=entry.exercise_id,
                superset_group=entry.superset_group,
                sets=[WorkoutSet(set_index=i, **s.model_dump()) for i, s in enumerate(entry.sets)],
            )
        )
    try:
        with db.begin_nested():
            db.add(workout)
            db.flush()
    except IntegrityError:
        # A concurrent request with the same client_id won the insert (double-tapped Save).
        winner = db.scalar(select(Workout.id).where(Workout.client_id == data.client_id))
        if winner is None:
            raise
        return get_workout(db, winner), False
    recompute_stats(db, exercise_ids)
    db.commit()
    return get_workout(db, workout.id), True


def delete_workout(db: Session, workout: Workout) -> None:
    """Delete a workout and refresh PR flags of its exercises."""
    exercise_ids = {e.exercise_id for e in workout.exercises}
    db.delete(workout)
    db.flush()
    recompute_stats(db, exercise_ids)
    db.commit()


def to_out(workout: Workout) -> WorkoutOut:
    """Serialize a workout tree."""
    return WorkoutOut(
        **{f: getattr(workout, f) for f in WorkoutOut.model_fields if f != "exercises"},
        exercises=[
            WorkoutExerciseOut(
                exercise_id=e.exercise_id,
                exercise_name=e.exercise.name,
                per_side=e.exercise.per_side,
                superset_group=e.superset_group,
                sets=[SetOut.model_validate(s) for s in e.sets],
            )
            for e in workout.exercises
        ],
    )


def list_summaries(
    db: Session, limit: int, offset: int, between: tuple[datetime, datetime] | None = None
) -> list[WorkoutSummary]:
    """History page, newest first, optionally limited to a time range [start, end)."""
    query = select(Workout)
    if between:
        query = query.where(Workout.started_at >= between[0], Workout.started_at < between[1])
    workouts = db.scalars(
        query.order_by(Workout.started_at.desc())
        .limit(limit)
        .offset(offset)
        .options(
            selectinload(Workout.template),
            selectinload(Workout.exercises).selectinload(WorkoutExercise.sets),
        )
    )
    return [
        WorkoutSummary(
            id=w.id,
            started_at=w.started_at,
            ended_at=w.ended_at,
            title=w.title,
            template_name=w.template.name if w.template else None,
            exercise_count=len(w.exercises),
            set_count=sum(len(e.sets) for e in w.exercises),
            pr_count=sum(s.is_pr for e in w.exercises for s in e.sets),
        )
        for w in workouts
    ]
