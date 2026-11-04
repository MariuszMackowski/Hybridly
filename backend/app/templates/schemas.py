from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SlotIn(BaseModel):
    """One exercise position of a template."""

    block: Literal["main", "finisher"] = "main"
    exercise_id: int
    alternative_exercise_ids: list[int] = []
    warmup_sets: int = Field(default=0, ge=0, le=10)
    sets: int = Field(ge=1, le=20)
    rep_min: int = Field(ge=1, le=100)
    rep_max: int = Field(ge=1, le=100)
    superset_group: int | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _range_ordered(self) -> "SlotIn":
        """rep_max must not be below rep_min."""
        if self.rep_max < self.rep_min:
            raise ValueError("rep_max must be >= rep_min")
        return self


class TemplateIn(BaseModel):
    """Editable template fields; slots are replaced as a whole."""

    name: str = Field(min_length=1, max_length=120)
    note: str | None = None
    warmup_items: list[str] = []
    cooldown_items: list[str] = []
    slots: list[SlotIn] = []


class ExerciseRef(BaseModel):
    """Exercise id and display name."""

    id: int
    name: str


class SlotOut(SlotIn):
    """Slot with resolved names."""

    position: int
    exercise_name: str
    alternatives: list[ExerciseRef]


class TemplateOut(TemplateIn):
    """Template as returned by the API."""

    id: int
    archived: bool
    slots: list[SlotOut]


class WeekItem(BaseModel):
    """Template suggested for one weekday."""

    weekday: int = Field(ge=0, le=6)
    template_id: int | None
    template_name: str | None = None


class TodayOut(BaseModel):
    """What the plan suggests for today."""

    date: date
    weekday: int
    template: TemplateOut | None
