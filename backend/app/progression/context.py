from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.exercises.models import Exercise
from app.exercises.schemas import ExerciseOut
from app.progression.suggest import PrevSet, SuggestionKind, suggest_sets
from app.workouts.models import Workout, WorkoutExercise


class PreviousSet(BaseModel):
    """A set from the most recent session of the exercise."""

    weight_kg: float | None
    reps: int | None
    seconds: int | None
    is_warmup: bool


class PreviousSession(BaseModel):
    """Most recent session of the exercise."""

    workout_id: int
    started_at: datetime
    sets: list[PreviousSet]


class SuggestionOut(BaseModel):
    """Suggested target for one working set."""

    weight_kg: float
    reps: int
    kind: SuggestionKind
    reason: str | None = None  # "fatigued" when progression was held back


FATIGUED_RECOVERY_PCT = 40
FATIGUED_MUSCLE_LEVEL = 0.7


def _hold_if_fatigued(db: Session, exercise: Exercise, suggestions, working) -> list[SuggestionOut]:
    """Turn weight increases into holds while the body or the exercise's muscles are fatigued."""
    from app.load.service import current_state  # local: load depends on workouts

    out = [SuggestionOut(**vars(s)) for s in suggestions]
    if not any(s.kind == SuggestionKind.increase for s in out) or not working:
        return out
    state = current_state(db)
    tired = state.recovery_pct < FATIGUED_RECOVERY_PCT or any(
        state.muscles.get(m, 0) >= FATIGUED_MUSCLE_LEVEL for m in exercise.primary_muscles
    )
    if not tired:
        return out
    held = []
    for i, s in enumerate(out):
        prev = working[min(i, len(working) - 1)]
        if s.kind == SuggestionKind.increase:
            s = SuggestionOut(
                weight_kg=prev.weight_kg,
                reps=prev.reps,
                kind=SuggestionKind.hold,
                reason="fatigued",
            )
        held.append(s)
    return held


class ExerciseContext(BaseModel):
    """Everything the logger needs to render one exercise card."""

    exercise: ExerciseOut
    previous: PreviousSession | None
    suggestions: list[SuggestionOut]


def _recent_entries(db: Session, exercise_id: int, limit: int) -> list[WorkoutExercise]:
    """First occurrence of the exercise in each of its most recent workouts, newest first."""
    entries = db.scalars(
        select(WorkoutExercise)
        .join(Workout)
        .where(WorkoutExercise.exercise_id == exercise_id)
        .order_by(Workout.started_at.desc(), WorkoutExercise.position)
        .options(selectinload(WorkoutExercise.sets), selectinload(WorkoutExercise.workout))
    )
    result: list[WorkoutExercise] = []
    for entry in entries:
        if result and result[-1].workout_id == entry.workout_id:
            continue
        result.append(entry)
        if len(result) == limit:
            break
    return result


def _working_sets(entry: WorkoutExercise | None) -> list[PrevSet]:
    """Working reps-sets of an entry as suggestion input."""
    if entry is None:
        return []
    return [
        PrevSet(float(s.weight_kg or 0), s.reps) for s in entry.sets if s.reps and not s.is_warmup
    ]


def build_context(
    db: Session, exercise: Exercise, sets: int, rep_min: int, rep_max: int
) -> ExerciseContext:
    """Previous session plus double-progression suggestions for an exercise."""
    recent = _recent_entries(db, exercise.id, limit=2)
    last = recent[0] if recent else None
    before = recent[1] if len(recent) > 1 else None
    suggestions = []
    if exercise.measure == "reps":
        suggestions = suggest_sets(
            _working_sets(last),
            _working_sets(before),
            sets,
            rep_min,
            rep_max,
            exercise.increment_kg,
        )
    previous = None
    if last is not None:
        previous = PreviousSession(
            workout_id=last.workout_id,
            started_at=last.workout.started_at,
            sets=[
                PreviousSet(
                    weight_kg=float(s.weight_kg) if s.weight_kg is not None else None,
                    reps=s.reps,
                    seconds=s.seconds,
                    is_warmup=s.is_warmup,
                )
                for s in last.sets
            ],
        )
    return ExerciseContext(
        exercise=ExerciseOut.model_validate(exercise),
        previous=previous,
        suggestions=_hold_if_fatigued(db, exercise, suggestions, _working_sets(last)),
    )
