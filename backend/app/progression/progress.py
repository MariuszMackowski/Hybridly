from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.bodyweight.service import bodyweight_lookup
from app.exercises.models import Exercise
from app.progression.e1rm import estimate_1rm, weight_for_reps
from app.time import local_date
from app.workouts.models import Workout, WorkoutExercise, WorkoutSet

RECENT_SESSIONS = 5
MAX_REPS = (1, 3, 5, 8, 10, 12)
TO_BEAT_MAX_REPS = 20


class SetPair(BaseModel):
    """Weight × reps of one working set."""

    weight_kg: float
    reps: int


class ProgressSession(BaseModel):
    """Per-workout summary of an exercise's working reps sets."""

    workout_id: int
    started_at: datetime
    grip: str | None
    best_e1rm_kg: float | None
    top_weight_kg: float
    top_reps: int
    volume_kg: float
    sets: list[SetPair]


class ProgressWeek(BaseModel):
    """Working-set volume in one Monday-based week."""

    week_start: date
    volume_kg: float
    sets: int


class RecordValue(BaseModel):
    """One record with the set (if any) and workout it came from."""

    value_kg: float
    weight_kg: float | None = None
    reps: int | None = None
    workout_id: int
    started_at: datetime


class Records(BaseModel):
    """All-time bests of the exercise (within the grip filter)."""

    best_e1rm: RecordValue | None = None
    heaviest: RecordValue | None = None
    biggest_set: RecordValue | None = None
    best_session: RecordValue | None = None


class RepMax(BaseModel):
    """Estimated weight for a rep count, from the best e1RM."""

    reps: int
    weight_kg: float


class ToBeat(BaseModel):
    """Sets that would beat the best e1RM of the last session."""

    target_e1rm_kg: float
    options: list[SetPair]


class ExerciseProgress(BaseModel):
    """Charts and stats for one exercise, optionally limited to one grip."""

    grips: list[str]
    sessions: list[ProgressSession]
    weeks: list[ProgressWeek]
    recent: list[ProgressSession]
    records: Records
    maxes: list[RepMax]
    to_beat: ToBeat | None


@dataclass
class _Entry:
    """A logged entry with its working sets and the bodyweight added to them."""

    entry: WorkoutExercise
    sets: list[WorkoutSet]
    extra_kg: float


def working_sets(entry: WorkoutExercise) -> list[WorkoutSet]:
    """Working sets that have reps."""
    return [s for s in entry.sets if s.reps and not s.is_warmup]


def sets_volume(sets: list[WorkoutSet], extra_kg: float = 0) -> float:
    """Sum of (weight + bodyweight extra) × reps."""
    return round(sum((float(s.weight_kg or 0) + extra_kg) * s.reps for s in sets), 1)


def _session(e: _Entry) -> ProgressSession:
    """Summarise one entry."""
    top = max(e.sets, key=lambda s: (float(s.weight_kg or 0), s.reps))
    e1rms = [float(s.e1rm_kg) for s in e.sets if s.e1rm_kg is not None]
    return ProgressSession(
        workout_id=e.entry.workout_id,
        started_at=e.entry.workout.started_at,
        grip=e.entry.grip,
        best_e1rm_kg=max(e1rms) if e1rms else None,
        top_weight_kg=float(top.weight_kg or 0),
        top_reps=top.reps,
        volume_kg=sets_volume(e.sets, e.extra_kg),
        sets=[SetPair(weight_kg=float(s.weight_kg or 0), reps=s.reps) for s in e.sets],
    )


def _weeks(sessions: list[ProgressSession]) -> list[ProgressWeek]:
    """Sum session volume and set counts into local Monday-based weeks; gaps become zero weeks."""
    volume: dict[date, float] = defaultdict(float)
    count: dict[date, int] = defaultdict(int)
    for session in sessions:
        day = local_date(session.started_at)
        monday = day - timedelta(days=day.weekday())
        volume[monday] += session.volume_kg
        count[monday] += len(session.sets)
    if not volume:
        return []
    weeks, week, last = [], min(volume), max(volume)
    while week <= last:
        weeks.append(
            ProgressWeek(week_start=week, volume_kg=round(volume[week], 1), sets=count[week])
        )
        week += timedelta(days=7)
    return weeks


def _set_record(e: _Entry, s: WorkoutSet, value: float) -> RecordValue:
    """Record pointing at one set."""
    return RecordValue(
        value_kg=round(value, 1),
        weight_kg=float(s.weight_kg or 0),
        reps=s.reps,
        workout_id=e.entry.workout_id,
        started_at=e.entry.workout.started_at,
    )


def _records(entries: list[_Entry]) -> Records:
    """Best e1RM, heaviest set, biggest set (kg × reps) and best session volume."""
    pairs = [(e, s) for e in entries for s in e.sets]
    if not pairs:
        return Records()
    rated = [(e, s) for e, s in pairs if s.e1rm_kg is not None]
    best = max(rated, key=lambda p: p[1].e1rm_kg, default=None)
    heavy = max(pairs, key=lambda p: (float(p[1].weight_kg or 0), p[1].reps))
    big = max(pairs, key=lambda p: (float(p[1].weight_kg or 0) + p[0].extra_kg) * p[1].reps)
    top_session = max(entries, key=lambda e: sets_volume(e.sets, e.extra_kg))
    return Records(
        best_e1rm=_set_record(*best, float(best[1].e1rm_kg)) if best else None,
        heaviest=_set_record(*heavy, float(heavy[1].weight_kg or 0)),
        biggest_set=_set_record(
            *big, (float(big[1].weight_kg or 0) + big[0].extra_kg) * big[1].reps
        ),
        best_session=RecordValue(
            value_kg=sets_volume(top_session.sets, top_session.extra_kg),
            workout_id=top_session.entry.workout_id,
            started_at=top_session.entry.workout.started_at,
        ),
    )


def _maxes(best_e1rm: float, extra_kg: float) -> list[RepMax]:
    """Weights for common rep counts (added weight for bodyweight exercises), to 0.5 kg."""
    return [
        RepMax(
            reps=r, weight_kg=max(0.0, round((weight_for_reps(best_e1rm, r) - extra_kg) * 2) / 2)
        )
        for r in MAX_REPS
    ]


def _reps_to_beat(weight: float, extra_kg: float, target: float) -> int | None:
    """Fewest reps at `weight` whose e1RM is above `target` (None past 20 reps)."""
    for reps in range(1, TO_BEAT_MAX_REPS + 1):
        if estimate_1rm(weight + extra_kg, reps) > target:
            return reps
    return None


def _to_beat(last: _Entry, increment_kg: float) -> ToBeat | None:
    """Same top weight with more reps, or one increment heavier, to beat the last session."""
    e1rms = [float(s.e1rm_kg) for s in last.sets if s.e1rm_kg is not None]
    if not e1rms:
        return None
    target = max(e1rms)
    top = max(float(s.weight_kg or 0) for s in last.sets)
    weights = [top, top + increment_kg] if increment_kg > 0 else [top]
    options = []
    for weight in weights:
        reps = _reps_to_beat(weight, last.extra_kg, target)
        if reps is not None:
            options.append(SetPair(weight_kg=weight, reps=reps))
    return ToBeat(target_e1rm_kg=target, options=options) if options else None


def _entries(db: Session, exercise: Exercise, grip: str | None) -> tuple[list[_Entry], list[str]]:
    """Entries with working reps sets (oldest first) and every grip ever logged."""
    rows = db.scalars(
        select(WorkoutExercise)
        .join(Workout)
        .where(WorkoutExercise.exercise_id == exercise.id)
        .order_by(Workout.started_at, WorkoutExercise.position)
        .options(selectinload(WorkoutExercise.sets), selectinload(WorkoutExercise.workout))
    ).all()
    grips = sorted({e.grip for e in rows if e.grip})
    bodyweight = bodyweight_lookup(db) if exercise.is_bodyweight else None
    entries = []
    for row in rows:
        sets = working_sets(row)
        if not sets or (grip is not None and row.grip != grip):
            continue
        if entries and entries[-1].entry.workout_id == row.workout_id:
            entries[-1].sets.extend(sets)  # same exercise twice in a workout = one session
            continue
        extra = (bodyweight(local_date(row.workout.started_at)) or 0) if bodyweight else 0
        entries.append(_Entry(row, sets, extra))
    return entries, grips


def exercise_progress(db: Session, exercise: Exercise, grip: str | None) -> ExerciseProgress:
    """Sessions, weekly volume, records, rep maxes and the next target of an exercise."""
    entries, grips = _entries(db, exercise, grip)
    sessions = [_session(e) for e in entries]
    records = _records(entries)
    last = entries[-1] if entries else None
    best = records.best_e1rm
    return ExerciseProgress(
        grips=grips,
        sessions=sessions,
        weeks=_weeks(sessions),
        recent=sessions[::-1][:RECENT_SESSIONS],
        records=records,
        maxes=_maxes(best.value_kg, last.extra_kg) if best and last else [],
        to_beat=_to_beat(last, exercise.increment_kg) if last else None,
    )
