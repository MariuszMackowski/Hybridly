"""Workout summary: volume per muscle and each exercise compared with ~4 weeks earlier."""

from collections import defaultdict
from collections.abc import Callable
from datetime import timedelta
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.bodyweight.service import bodyweight_lookup
from app.progression.progress import SetPair, sets_volume, working_sets
from app.time import local_date
from app.workouts.models import Workout, WorkoutExercise, WorkoutSet

COMPARE_DAYS = 28  # compare with the session closest to 4 weeks earlier…
COMPARE_WINDOW_DAYS = 56  # …but no older than 8 weeks…
COMPARE_MIN_DAYS = 7  # …and at least a week old
SECONDARY_SHARE = 0.5

BodyweightAt = Callable[[Workout], float]


class MuscleVolume(BaseModel):
    """Effective volume a muscle got in the workout."""

    muscle: str
    volume_kg: float


class ExerciseInsight(BaseModel):
    """Volume / best set of one exercise entry and the change against an earlier session."""

    metric: Literal["volume", "reps"]  # reps for bodyweight-only work (pull-ups)
    volume_kg: float
    total_reps: int
    best_set: SetPair | None
    best_e1rm_kg: float | None
    volume_change_pct: int | None  # change of volume (or of total reps for metric=reps)
    best_change_pct: int | None  # change of the best e1RM
    weeks_ago: int | None


class WorkoutInsights(BaseModel):
    """Per-muscle volume and per-exercise insights in workout order."""

    muscles: list[MuscleVolume]
    exercises: list[ExerciseInsight | None]  # None for time/distance-only entries


def _pct(now: float | None, before: float | None) -> int | None:
    """Rounded percentage change, None without a usable baseline."""
    if now is None or not before:
        return None
    return round(100 * (now - before) / before)


def _best(sets: list[WorkoutSet]) -> WorkoutSet | None:
    """Set with the highest e1RM."""
    return max((s for s in sets if s.e1rm_kg is not None), key=lambda s: s.e1rm_kg, default=None)


def _reference(db: Session, workout: Workout, entry: WorkoutExercise) -> WorkoutExercise | None:
    """Earlier entry of the same exercise and grip closest to 4 weeks before the workout."""
    since = workout.started_at - timedelta(days=COMPARE_WINDOW_DAYS)
    earlier = db.scalars(
        select(WorkoutExercise)
        .join(Workout)
        .where(
            WorkoutExercise.exercise_id == entry.exercise_id,
            WorkoutExercise.grip.is_(None)
            if entry.grip is None
            else WorkoutExercise.grip == entry.grip,
            Workout.started_at <= workout.started_at - timedelta(days=COMPARE_MIN_DAYS),
            Workout.started_at >= since,
        )
        .options(selectinload(WorkoutExercise.sets), selectinload(WorkoutExercise.workout))
    ).all()
    target = workout.started_at - timedelta(days=COMPARE_DAYS)
    candidates = [e for e in earlier if working_sets(e)]
    return min(candidates, key=lambda e: abs(e.workout.started_at - target), default=None)


def _insight(db: Session, workout: Workout, entry: WorkoutExercise, bodyweight: BodyweightAt):
    """Insight for one entry, None when it has no working reps sets."""
    sets = working_sets(entry)
    if not sets:
        return None
    extra = bodyweight(workout) if entry.exercise.is_bodyweight else 0
    bodyweight_only = entry.exercise.is_bodyweight and all(not s.weight_kg for s in sets)
    best = _best(sets)
    volume = sets_volume(sets, extra)
    reps = sum(s.reps for s in sets)
    ref = _reference(db, workout, entry)
    ref_sets = working_sets(ref) if ref else []
    ref_best = _best(ref_sets)
    ref_extra = bodyweight(ref.workout) if ref and entry.exercise.is_bodyweight else 0
    ref_amount = (
        sum(s.reps for s in ref_sets) if bodyweight_only else sets_volume(ref_sets, ref_extra)
    )
    days = (workout.started_at - ref.workout.started_at).days if ref else None
    return ExerciseInsight(
        metric="reps" if bodyweight_only else "volume",
        volume_kg=volume,
        total_reps=reps,
        best_set=SetPair(weight_kg=float(best.weight_kg or 0), reps=best.reps) if best else None,
        best_e1rm_kg=float(best.e1rm_kg) if best else None,
        volume_change_pct=_pct(reps if bodyweight_only else volume, ref_amount),
        best_change_pct=_pct(
            float(best.e1rm_kg) if best else None,
            float(ref_best.e1rm_kg) if ref_best else None,
        ),
        weeks_ago=max(1, round(days / 7)) if days is not None else None,
    )


def _muscles(workout: Workout, extra: float) -> list[MuscleVolume]:
    """Volume per muscle: full for primary muscles, half for secondary, biggest first."""
    totals: dict[str, float] = defaultdict(float)
    for entry in workout.exercises:
        volume = sets_volume(working_sets(entry), extra if entry.exercise.is_bodyweight else 0)
        for muscle in entry.exercise.primary_muscles:
            totals[muscle] += volume
        for muscle in entry.exercise.secondary_muscles:
            totals[muscle] += volume * SECONDARY_SHARE
    ranked = sorted(((m, round(v)) for m, v in totals.items()), key=lambda kv: -kv[1])
    return [MuscleVolume(muscle=m, volume_kg=v) for m, v in ranked if v > 0]


def _bodyweight_at(db: Session, workout: Workout) -> BodyweightAt:
    """Bodyweight on a workout's day; skips loading entries when no bodyweight exercise is in it."""
    if not any(e.exercise.is_bodyweight for e in workout.exercises):
        return lambda _: 0
    lookup = bodyweight_lookup(db)
    return lambda w: lookup(local_date(w.started_at)) or 0


def workout_insights(db: Session, workout: Workout) -> WorkoutInsights:
    """Muscle volume and per-exercise comparison for a loaded workout."""
    bodyweight = _bodyweight_at(db, workout)
    return WorkoutInsights(
        muscles=_muscles(workout, bodyweight(workout)),
        exercises=[_insight(db, workout, e, bodyweight) for e in workout.exercises],
    )
