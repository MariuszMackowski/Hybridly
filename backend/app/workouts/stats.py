from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bodyweight.service import bodyweight_lookup
from app.exercises.models import Exercise
from app.progression.e1rm import estimate_1rm
from app.time import local_date
from app.workouts.models import Workout, WorkoutExercise, WorkoutSet


def _set_e1rm(row: WorkoutSet, exercise: Exercise, bodyweight: float | None) -> Decimal | None:
    """e1RM of a working reps set, None for warm-up, time sets or unknown bodyweight."""
    if row.is_warmup or not row.reps:
        return None
    weight = float(row.weight_kg or 0)
    if exercise.is_bodyweight:
        if bodyweight is None:
            return None
        weight += bodyweight
    return Decimal(str(estimate_1rm(weight, row.reps)))


def recompute_stats(
    db: Session, exercise_ids: set[int] | None = None, bodyweight_only: bool = False
) -> None:
    """Recompute e1RM and PR flags chronologically; PRs are tracked per exercise and grip."""
    query = (
        select(WorkoutSet, WorkoutExercise.exercise_id, WorkoutExercise.grip, Workout.started_at)
        .join(WorkoutExercise, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .order_by(Workout.started_at, WorkoutExercise.position, WorkoutSet.set_index)
    )
    if exercise_ids is not None:
        query = query.where(WorkoutExercise.exercise_id.in_(exercise_ids))
    if bodyweight_only:
        query = query.join(Exercise, WorkoutExercise.exercise_id == Exercise.id).where(
            Exercise.is_bodyweight.is_(True)
        )
    rows = db.execute(query).all()
    exercises = {e.id: e for e in db.scalars(select(Exercise))}
    bodyweight = bodyweight_lookup(db)
    best: dict[tuple[int, str | None], Decimal] = defaultdict(lambda: Decimal("-1"))
    for workout_set, exercise_id, grip, started_at in rows:
        exercise = exercises[exercise_id]
        e1rm = _set_e1rm(workout_set, exercise, bodyweight(local_date(started_at)))
        workout_set.e1rm_kg = e1rm
        previous_best = best[exercise_id, grip]
        workout_set.is_pr = e1rm is not None and previous_best >= 0 and e1rm > previous_best
        if e1rm is not None and e1rm > previous_best:
            best[exercise_id, grip] = e1rm
    db.flush()
