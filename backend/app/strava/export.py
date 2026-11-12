"""Send a strength workout to Strava: describe the watch-recorded activity, or create one."""

from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.progression.progress import sets_volume, working_sets
from app.strava import client
from app.time import local_tz
from app.workouts.format import exercise_line, set_text
from app.workouts.insights import bodyweight_at
from app.workouts.models import Workout

STRENGTH_TYPES = {"WeightTraining", "Workout", "Crossfit", "HighIntensityIntervalTraining"}
MATCH_MARGIN = timedelta(minutes=90)  # watch start vs. logger start can differ
DEFAULT_DURATION = timedelta(hours=1)
MARKER = "🏋️ Hybridly"  # starts our block, so re-sending replaces it and keeps the user's text


class SendResult(BaseModel):
    """What happened on Strava."""

    activity_id: int
    action: Literal["updated", "created"]
    url: str


def describe(db: Session, workout: Workout) -> str:
    """Description text: totals (same volume as the workout summary), exercises and PRs."""
    entries = workout.exercises
    extra = bodyweight_at(db, workout)(workout)
    working = [s for e in entries for s in working_sets(e)]
    volume = round(
        sum(sets_volume(working_sets(e), extra if e.exercise.is_bodyweight else 0) for e in entries)
    )
    lines = [f"{MARKER} · {len(entries)} exercises · {len(working)} sets · {volume:,} kg"]
    lines += [exercise_line(e) for e in entries]
    prs = [
        f"{e.exercise.name} {set_text(s, mark_pr=False)}"
        for e in entries
        for s in e.sets
        if s.is_pr
    ]
    if prs:
        lines.append("🏆 PR: " + ", ".join(prs))
    return "\n".join(lines)


def _merge(existing: str | None, ours: str) -> str:
    """Keep the user's own text, replace any earlier Hybridly block."""
    base = (existing or "").split(MARKER)[0].rstrip()
    return f"{base}\n\n{ours}" if base else ours


def _parse(stamp: str) -> datetime:
    """Strava's ISO timestamp ("…Z") as an aware datetime."""
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def _watch_activity(db: Session, workout: Workout) -> int | None:
    """Strength activity on Strava closest to the workout's start (within the margin) that
    no other workout was sent to."""
    end = workout.ended_at or workout.started_at + DEFAULT_DURATION
    activities = client.api(
        db,
        "GET",
        "/athlete/activities",
        params={
            "after": int((workout.started_at - MATCH_MARGIN).timestamp()),
            "before": int((end + MATCH_MARGIN).timestamp()),
            "per_page": 50,
        },
    )
    taken = set(
        db.scalars(
            select(Workout.strava_activity_id).where(
                Workout.id != workout.id, Workout.strava_activity_id.is_not(None)
            )
        )
    )
    strength = [
        a for a in activities if a.get("sport_type") in STRENGTH_TYPES and a["id"] not in taken
    ]
    best = min(
        strength,
        key=lambda a: abs(_parse(a["start_date"]) - workout.started_at),
        default=None,
    )
    return best["id"] if best else None


def _update(db: Session, activity_id: int, text: str) -> None:
    """Put our block into the activity's description."""
    current = client.api(db, "GET", f"/activities/{activity_id}")
    client.api(
        db,
        "PUT",
        f"/activities/{activity_id}",
        json={"description": _merge(current.get("description"), text)},
    )


def _create(db: Session, workout: Workout, text: str) -> int:
    """New Weight Training activity covering the workout."""
    duration = (workout.ended_at - workout.started_at) if workout.ended_at else DEFAULT_DURATION
    created = client.api(
        db,
        "POST",
        "/activities",
        data={
            "name": workout.title or "Weight Training",
            "sport_type": "WeightTraining",
            "start_date_local": workout.started_at.astimezone(local_tz())
            .replace(tzinfo=None)
            .isoformat(timespec="seconds"),
            "elapsed_time": max(60, int(duration.total_seconds())),
            "description": text,
        },
    )
    return created["id"]


def send_workout(db: Session, workout: Workout) -> SendResult:
    """Describe the matching (or previously used) Strava activity, else create one."""
    text = describe(db, workout)
    target = workout.strava_activity_id
    if target is not None:
        try:
            _update(db, target, text)
        except client.NotFound:
            target = None  # deleted on Strava: match or create again
    if target is None and (target := _watch_activity(db, workout)) is not None:
        _update(db, target, text)
    action = "updated" if target is not None else "created"
    if target is None:
        target = _create(db, workout, text)
    workout.strava_activity_id = target
    db.commit()
    return SendResult(
        activity_id=target, action=action, url=f"https://www.strava.com/activities/{target}"
    )
