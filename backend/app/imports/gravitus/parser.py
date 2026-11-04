"""Parser for the multi-section Gravitus CSV export (pure, no database access)."""

import csv
import io
import re
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime

SECTIONS = {
    "Profile",
    "Workouts",
    "Workout Sets",
    "Workout Group Notes",
    "Workout Videos",
    "Workout Templates",
    "Workout Template Group",
    "Workout Template Set Goals",
    "Exercise Notes",
    "Exercise Videos",
    "Exercise Tips",
}
_WORKOUT_REF = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\+00:00)")
LB_TO_KG = 0.45359237
WARMUP_RATIO = 0.6


@dataclass(frozen=True)
class GSet:
    """One set from the export, weight already in kg."""

    group_number: int
    set_number: int
    exercise: str
    weight_kg: float | None
    reps: int | None
    seconds: int | None
    distance_m: float | None
    is_warmup: bool = False


@dataclass
class GWorkout:
    """One workout with its sets in export order."""

    external_id: str
    started_at: datetime
    duration_s: int | None
    title: str | None
    sets: list[GSet] = field(default_factory=list)


@dataclass
class GTemplate:
    """Template: groups in order, each a list of exercise names."""

    name: str
    groups: list[list[str]]


def lb_to_kg(lb: float) -> float:
    """Convert pounds to kg rounded to the nearest 0.25 kg."""
    return round(lb * LB_TO_KG / 0.25) * 0.25


def _int(value: str) -> int | None:
    """Parse an optional integer cell."""
    return int(float(value)) if value.strip() else None


def _float(value: str) -> float | None:
    """Parse an optional float cell."""
    return float(value) if value.strip() else None


def _sections(text: str) -> dict[str, list[dict[str, str]]]:
    """Split the export into {section title: rows as dicts keyed by that section's header}."""
    result: dict[str, list[dict[str, str]]] = {}
    current: str | None = None
    header: list[str] | None = None
    for row in csv.reader(io.StringIO(text)):
        if row and row[0] in SECTIONS and not any(c.strip() for c in row[1:]):
            current, header = row[0], None
            result[current] = []
        elif current is not None and header is None:
            header = row
        elif current is not None and any(c.strip() for c in row):
            result[current].append(dict(zip(header, row, strict=False)))
    return result


def mark_warmups(sets: list[GSet]) -> list[GSet]:
    """Mark leading sets at <= 60% of the top weight as warm-ups (same exercise, one workout)."""
    top = max((s.weight_kg or 0) for s in sets) if sets else 0
    if top <= 0:
        return sets
    result, leading = [], True
    for s in sets:
        # Weight 0 is an unweighted bodyweight set (logged kg = added load), never a warm-up.
        leading = leading and 0 < (s.weight_kg or 0) <= WARMUP_RATIO * top
        result.append(replace(s, is_warmup=leading))
    return result


def _parse_set(row: dict[str, str]) -> GSet:
    """Build a GSet from a 'Workout Sets' row."""
    weight = _float(row["weight"])
    return GSet(
        group_number=int(row["group_number"]),
        set_number=int(row["set_number"]),
        exercise=row["exercise"].strip(),
        weight_kg=lb_to_kg(weight) if weight is not None else None,
        reps=_int(row["reps"]),
        seconds=_int(row["seconds"]),
        distance_m=_float(row["distance_m"]),
    )


def _with_warmups(sets: list[GSet]) -> list[GSet]:
    """Apply warm-up marking per exercise entry, keeping export order."""
    buckets: dict[tuple[int, str], list[int]] = defaultdict(list)
    for i, s in enumerate(sets):
        buckets[(s.group_number, s.exercise)].append(i)
    result = list(sets)
    for indices in buckets.values():
        indices.sort(key=lambda i: sets[i].set_number)
        for i, marked in zip(indices, mark_warmups([sets[i] for i in indices]), strict=True):
            result[i] = marked
    return result


def parse_export(text: str) -> tuple[list[GWorkout], list[GTemplate]]:
    """Parse workouts (with sets) and templates; other sections are ignored."""
    sections = _sections(text)
    workouts = {
        row["started_at"]: GWorkout(
            external_id=row["started_at"],
            started_at=datetime.fromisoformat(row["started_at"]),
            duration_s=_int(row["duration_seconds"]),
            title=row["title"].strip() or None,
        )
        for row in sections.get("Workouts", [])
    }
    for row in sections.get("Workout Sets", []):
        match = _WORKOUT_REF.match(row["workout"])
        if match and match.group(1) in workouts:
            workouts[match.group(1)].sets.append(_parse_set(row))
    for workout in workouts.values():
        workout.sets = _with_warmups(workout.sets)

    groups: dict[str, dict[int, list[tuple[int, str]]]] = {}
    for row in sections.get("Workout Template Group", []):
        by_group = groups.setdefault(row["template"], {})
        by_group.setdefault(int(row["group_number"]), []).append(
            (int(row["index"]), row["exercise"].strip())
        )
    templates = [
        GTemplate(
            name=row["name"],
            groups=[
                [name for _, name in sorted(members)]
                for _, members in sorted(groups.get(row["name"], {}).items())
            ],
        )
        for row in sections.get("Workout Templates", [])
    ]
    return list(workouts.values()), templates
