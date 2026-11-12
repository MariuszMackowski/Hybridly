"""Plain-text training summary to paste to an AI coach."""

from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.activities.models import Activity
from app.bodyweight.models import BodyweightEntry
from app.db import get_db
from app.load.service import current_state, workout_loads
from app.plans.compare import compare
from app.plans.models import PlanSession
from app.plans.service import sessions_on, week_of
from app.time import local_date, local_range, local_today
from app.workouts.format import exercise_line, kg_text
from app.workouts.models import Workout, WorkoutExercise

router = APIRouter(tags=["export"])

DEFAULT_DAYS = 28
MAX_DAYS = 366
FATIGUE_SHOWN = 0.05  # same cut-off as the Recovery card


class CoachExport(BaseModel):
    """Export text and the range it covers."""

    start: date
    end: date
    text: str


def _day(d: date) -> str:
    """'Mon 03.11'."""
    return d.strftime("%a %d.%m")


def _clock(seconds: float) -> str:
    """'52:30' or '1:44:36'."""
    s = round(seconds)
    h, m, sec = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def _workouts(db: Session, between) -> list[Workout]:
    """Strength workouts in the range with exercises and sets, oldest first."""
    return list(
        db.scalars(
            select(Workout)
            .where(Workout.started_at >= between[0], Workout.started_at < between[1])
            .order_by(Workout.started_at)
            .options(
                selectinload(Workout.exercises).selectinload(WorkoutExercise.sets),
                selectinload(Workout.exercises).selectinload(WorkoutExercise.exercise),
            )
        )
    )


def _activities(db: Session, between) -> list[Activity]:
    """Activities in the range with laps, oldest first."""
    return list(
        db.scalars(
            select(Activity)
            .where(Activity.started_at >= between[0], Activity.started_at < between[1])
            .order_by(Activity.started_at)
            .options(selectinload(Activity.laps))
        )
    )


def _planned(db: Session, start: date, end: date) -> list[PlanSession]:
    """Planned run sessions in the range, each day taken from the plan in effect that day."""
    days = (end - start).days + 1
    return [s for i in range(days) for s in sessions_on(db, start + timedelta(days=i))]


def _state_lines(db: Session, today: date) -> list[str]:
    """Recovery, bodyweight and current plan week as of today."""
    state = current_state(db)
    regions = ", ".join(f"{r.region} {r.recovery_pct}%" for r in state.regions)
    lines = [f"- Recovery: {state.recovery_pct}% ({regions})"]
    if state.coros_pct is not None:
        lines.append(f"- COROS recovery: {state.coros_pct}%")
    tired = [
        m.replace("_", " ")
        for m, v in sorted(state.muscles.items(), key=lambda x: -x[1])
        if v >= FATIGUE_SHOWN
    ]
    if tired:
        lines.append(f"- Most fatigued muscles: {', '.join(tired[:4])}")
    weight = db.scalar(select(BodyweightEntry).order_by(BodyweightEntry.day.desc()).limit(1))
    if weight:
        lines.append(f"- Bodyweight: {kg_text(weight.kg)} kg ({weight.day:%d.%m.%Y})")
    week = week_of(db, today)
    if week:
        goal = {k: v for k, v in (week.plan.goal or {}).items() if v is not None}
        target = f", target {week.target_km:g} km" if week.target_km else ""
        phase = week.phase or "-"
        lines.append(f"- Running plan: {week.plan.name}, week {week.week} ({phase}{target})")
        if goal:
            lines.append(f"- Goal: {', '.join(f'{k} {v}' for k, v in goal.items())}")
    return lines


def _workout_block(workout: Workout, load: int | None) -> list[str]:
    """Header line plus one line per exercise."""
    title = workout.title or "Workout"
    head = f"### {_day(local_date(workout.started_at))} · {title}"
    lines = [head + (f" (load {load})" if load else "")]
    lines += [f"- {exercise_line(entry)}" for entry in workout.exercises]
    return lines


def _activity_line(activity: Activity, planned: PlanSession | None) -> str:
    """One activity with pace/HR/load and, if matched, how it compared to the plan."""
    parts = [f"{_day(local_date(activity.started_at))} · {activity.name or activity.sport}"]
    if activity.distance_m:
        parts.append(f"{activity.distance_m / 1000:.1f} km")
    parts.append(_clock(activity.duration_s))
    if activity.distance_m and activity.sport in ("run", "walk"):
        parts.append(f"{_clock(activity.duration_s / (activity.distance_m / 1000))}/km")
    if activity.avg_hr:
        parts.append(f"HR {activity.avg_hr}/{activity.max_hr or '-'}")
    if activity.training_load:
        parts.append(f"TL {activity.training_load}")
    line = "- " + " · ".join(parts)
    if planned:
        line += f"\n  planned: {planned.title}" + _comparison_text(planned, activity)
    return line


def _comparison_text(planned: PlanSession, activity: Activity) -> str:
    """'(distance 102%, pace faster, HR in zone 80%)' or ''."""
    c = compare(planned, activity)
    bits = []
    if c.distance_pct is not None:
        bits.append(f"distance {c.distance_pct}%")
    if c.pace_status:
        bits.append(f"pace {c.pace_status}")
    if c.hr_in_pct is not None:
        bits.append(f"HR in zone {c.hr_in_pct}%")
    return f" ({', '.join(bits)})" if bits else ""


def _week_table(workouts, activities, planned, start: date, end: date) -> list[str]:
    """Per-week counts: gym sessions, working sets, runs, run km vs planned km."""
    monday = start - timedelta(days=start.weekday())
    rows: dict[date, dict[str, float]] = {}
    while monday <= end:
        rows[monday] = defaultdict(float)
        monday += timedelta(days=7)

    def bucket(day: date) -> dict[str, float]:
        """Row of the week containing `day`."""
        return rows[day - timedelta(days=day.weekday())]

    for w in workouts:
        row = bucket(local_date(w.started_at))
        row["gym"] += 1
        row["sets"] += sum(1 for e in w.exercises for s in e.sets if not s.is_warmup)
    for a in activities:
        if a.sport == "run":
            row = bucket(local_date(a.started_at))
            row["runs"] += 1
            row["km"] += (a.distance_m or 0) / 1000
    for p in planned:
        bucket(p.date)["planned_km"] += p.distance_km or 0
    lines = [
        "| Week of | Gym | Working sets | Runs | Run km | Planned km |",
        "|---|---|---|---|---|---|",
    ]
    for week, r in rows.items():
        lines.append(
            f"| {week:%d.%m} | {r['gym']:g} | {r['sets']:g} | {r['runs']:g} "
            f"| {r['km']:.1f} | {r['planned_km']:.1f} |"
        )
    return lines


def _missed(planned: list[PlanSession], today: date) -> list[str]:
    """Past planned sessions with no matched activity."""
    missed = [p for p in planned if p.activity_id is None and p.date < today]
    return [f"- {_day(p.date)} · {p.title}" for p in missed]


def build_export(db: Session, start: date, end: date) -> str:
    """Markdown summary of strength, cardio and plan adherence in [start, end]."""
    today = local_today()
    between = local_range(start, end + timedelta(days=1))
    workouts = _workouts(db, between)
    activities = _activities(db, between)
    planned = _planned(db, start, end)
    by_activity = {p.activity_id: p for p in planned if p.activity_id}
    loads = workout_loads(db, [w.id for w in workouts])
    out = [f"# Training summary {start:%d.%m.%Y} – {end:%d.%m.%Y}", ""]
    out += ["## Current state", *_state_lines(db, today), ""]
    out += ["## Weekly overview", *_week_table(workouts, activities, planned, start, end), ""]
    out += ["## Strength workouts (sets: kg×reps, W = warm-up)"]
    for w in workouts:
        out += _workout_block(w, loads.get(w.id))
    out += ["", "## Runs and other cardio"]
    out += [_activity_line(a, by_activity.get(a.id)) for a in activities] or ["- none"]
    missed = _missed(planned, today)
    if missed:
        out += ["", "## Planned runs not done", *missed]
    return "\n".join(out) + "\n"


@router.get("/export/coach", response_model=CoachExport)
def coach_export(
    start: date | None = Query(None),
    end: date | None = Query(None),
    db: Session = Depends(get_db),
):
    """Training summary for an AI coach; defaults to the last 4 weeks up to today."""
    end = end or local_today()
    start = start or end - timedelta(days=DEFAULT_DAYS - 1)
    if start > end or (end - start).days >= MAX_DAYS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid date range")
    return CoachExport(start=start, end=end, text=build_export(db, start, end))
