"""Small helpers that build ORM rows directly for tests."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.exercises.models import Exercise
from app.workouts.models import Workout, WorkoutExercise, WorkoutSet


def make_exercise(db: Session, name: str = "Bench Press", **fields) -> Exercise:
    """Insert an exercise with sensible defaults."""
    exercise = Exercise(name=name, primary_muscles=["chest"], **fields)
    db.add(exercise)
    db.flush()
    return exercise


def make_workout(
    db: Session,
    exercise: Exercise,
    sets: list[tuple],
    started_at: datetime | None = None,
    source: str = "app",
    external_id: str | None = None,
) -> Workout:
    """Insert a workout with one exercise; sets are (weight, reps[, seconds[, is_warmup]])."""
    workout = Workout(
        started_at=started_at or datetime(2026, 11, 1, 7, 0, tzinfo=UTC),
        source=source,
        external_id=external_id,
    )
    workout_exercise = WorkoutExercise(position=0, exercise=exercise)
    for index, values in enumerate(sets):
        weight, reps, *rest = values
        seconds = rest[0] if rest else None
        is_warmup = rest[1] if len(rest) > 1 else False
        workout_exercise.sets.append(
            WorkoutSet(
                set_index=index, weight_kg=weight, reps=reps, seconds=seconds, is_warmup=is_warmup
            )
        )
    workout.exercises.append(workout_exercise)
    db.add(workout)
    db.flush()
    return workout


def make_activity(
    db: Session,
    started_at: datetime,
    sport: str = "run",
    distance_m: float = 8000,
    duration_s: int = 2800,
    streams: dict | None = None,
    laps: list[dict] | None = None,
):
    """Insert an activity row directly (no FIT file)."""
    from app.activities.models import Activity, ActivityLap

    activity = Activity(
        source="upload",
        sport=sport,
        started_at=started_at,
        duration_s=duration_s,
        distance_m=distance_m,
        avg_speed=distance_m / duration_s,
        fit_sha256=f"{started_at.isoformat()}-{sport}",
        fit_path="/nonexistent.fit",
        streams=streams or {"t": []},
        laps=[ActivityLap(index=i, start_offset_s=0, **lap) for i, lap in enumerate(laps or [])],
    )
    db.add(activity)
    db.flush()
    return activity
