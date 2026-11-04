"""Running plan file format v1 (YAML) — validation only, no database access."""

import re
from datetime import date as Date
from datetime import timedelta
from typing import Literal

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

SessionType = Literal["easy", "long", "tempo", "intervals", "strides", "race", "other"]
Flag = Literal["cutback", "taper", "race"]
_PACE = re.compile(r"^(\d{1,2}):([0-5]\d)$")


class PlanFormatError(ValueError):
    """Invalid plan file; `path` points at the offending field (e.g. weeks.0.sessions.1.type)."""

    def __init__(self, path: str, message: str):
        """Keep the field path separately for API responses."""
        super().__init__(f"{path}: {message}" if path else message)
        self.path, self.message = path, message


def pace_to_s(value: str) -> int:
    """'5:40' (min:sec per km) → 340 seconds."""
    match = _PACE.match(value.strip())
    if not match:
        raise ValueError(f"pace must look like 5:40, got {value!r}")
    return int(match[1]) * 60 + int(match[2])


class PaceRange(BaseModel):
    """Per-km pace range; min is the faster end."""

    min: str
    max: str

    @property
    def min_s(self) -> int:
        """Faster end in seconds."""
        return pace_to_s(self.min)

    @property
    def max_s(self) -> int:
        """Slower end in seconds."""
        return pace_to_s(self.max)

    @model_validator(mode="after")
    def _ordered(self) -> "PaceRange":
        """Both parse and min (faster) ≤ max (slower)."""
        if self.min_s > self.max_s:
            raise ValueError("pace.min must be the faster pace (≤ pace.max)")
        return self


class HrRange(BaseModel):
    """Heart-rate range in bpm."""

    min: int = Field(ge=40, le=230)
    max: int = Field(ge=40, le=230)

    @model_validator(mode="after")
    def _ordered(self) -> "HrRange":
        """min ≤ max."""
        if self.min > self.max:
            raise ValueError("hr.min must be ≤ hr.max")
        return self


class Intervals(BaseModel):
    """Repeated work segments."""

    reps: int = Field(ge=1, le=50)
    distance_m: int | None = Field(default=None, ge=50)
    duration_s: int | None = Field(default=None, ge=10)
    pace: PaceRange | None = None
    recovery: str | None = None


class SessionIn(BaseModel):
    """One planned run."""

    date: Date
    type: SessionType
    title: str
    description: str = ""
    distance_km: float | None = Field(default=None, gt=0, le=100)
    pace: PaceRange | None = None
    hr: HrRange | None = None
    intervals: Intervals | None = None


class DayNote(BaseModel):
    """Coach remark for a day (gym/home adjustments)."""

    date: Date
    text: str


class WeekIn(BaseModel):
    """One plan week starting on Monday."""

    week: int = Field(ge=1)
    start: Date
    phase: str | None = None
    flags: list[Flag] = []
    target_km: float | None = None
    note: str | None = None
    day_notes: list[DayNote] = []
    sessions: list[SessionIn] = []

    @field_validator("start")
    @classmethod
    def _monday(cls, value: Date) -> Date:
        """Weeks start on Monday."""
        if value.weekday() != 0:
            raise ValueError("week start must be a Monday")
        return value


class Goal(BaseModel):
    """Target race."""

    race: str | None = None
    date: Date | None = None
    target_time: str | None = None


class PlanFile(BaseModel):
    """Whole plan file."""

    version: Literal[1]
    name: str
    goal: Goal | None = None
    notes: list[str] = []
    weeks: list[WeekIn] = Field(min_length=1)


def _check_dates(plan: PlanFile) -> None:
    """Sessions and day notes must fall inside their week."""
    for w, week in enumerate(plan.weeks):
        end = week.start + timedelta(days=6)
        for kind, items in (("sessions", week.sessions), ("day_notes", week.day_notes)):
            for i, item in enumerate(items):
                if not week.start <= item.date <= end:
                    raise PlanFormatError(f"weeks.{w}.{kind}.{i}.date", "date outside its week")


def parse_plan_yaml(text: str) -> PlanFile:
    """Parse and validate a plan file."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise PlanFormatError("", f"not valid YAML: {error}") from error
    if not isinstance(data, dict):
        raise PlanFormatError("", "plan must be a YAML mapping")
    try:
        plan = PlanFile.model_validate(data)
    except ValidationError as error:
        first = error.errors()[0]
        path = ".".join(str(p) for p in first["loc"])
        raise PlanFormatError(path, first["msg"]) from error
    _check_dates(plan)
    return plan


COACH_INSTRUCTIONS = """\
Return the running plan as ONE YAML file in exactly this format (version 1).
Rules:
- weeks[].start is the Monday of that week (YYYY-MM-DD); every session date lies in that week.
- session type: easy | long | tempo | intervals | strides | race | other.
- pace is per km as "m:ss"; pace.min is the FASTER end. hr is bpm.
- Only runs go into sessions. Gym or home-workout remarks go into day_notes.
- flags: cutback (recovery week), taper, race (week with a race).
- Keep your original wording of each session in description.

```yaml
version: 1
name: "Example 10k block"
goal: {race: "City 10k", date: 2027-03-21, target_time: "0:44:00"}
notes: ["Easy runs: 5:40-6:20/km, HR 133-146"]
weeks:
  - week: 1
    start: 2027-01-04
    phase: "Base"
    flags: []
    target_km: 30
    day_notes:
      - {date: 2027-01-05, text: "Gym: Lower A as usual"}
    sessions:
      - date: 2027-01-04
        type: easy
        title: "Easy 8 km"
        description: "Easy 8km, 5:40-6:20/km (HR133-146)"
        distance_km: 8
        pace: {min: "5:40", max: "6:20"}
        hr: {min: 133, max: 146}
      - date: 2027-01-08
        type: intervals
        title: "5 x 1 km"
        description: "Intervals 5x1km @4:20/km, 2 min jog"
        intervals: {reps: 5, distance_m: 1000, pace: {min: "4:15", max: "4:25"}, recovery: "2 min jog"}
      - date: 2027-01-10
        type: long
        title: "Long run 16 km"
        description: "Long run 16km easy"
        distance_km: 16
        pace: {min: "5:40", max: "6:20"}
```
"""
