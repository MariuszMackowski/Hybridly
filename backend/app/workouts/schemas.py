from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SetIn(BaseModel):
    """One logged set: reps-based or time-based."""

    weight_kg: float | None = Field(default=None, ge=0)
    reps: int | None = Field(default=None, ge=1, le=100)
    seconds: int | None = Field(default=None, ge=1)
    is_warmup: bool = False

    @model_validator(mode="after")
    def _reps_xor_seconds(self) -> "SetIn":
        """Require exactly one of reps / seconds."""
        if (self.reps is None) == (self.seconds is None):
            raise ValueError("set needs exactly one of reps or seconds")
        return self


class WorkoutExerciseIn(BaseModel):
    """An exercise with its sets, in performed order."""

    exercise_id: int
    superset_group: int | None = None
    sets: list[SetIn] = Field(min_length=1)


class WorkoutCreate(BaseModel):
    """Whole workout sent once by the logger's Save button."""

    client_id: UUID
    started_at: datetime
    ended_at: datetime | None = None
    template_id: int | None = None
    title: str | None = None
    note: str | None = None
    exercises: list[WorkoutExerciseIn] = Field(min_length=1)


class SetOut(BaseModel):
    """Stored set with derived stats."""

    model_config = ConfigDict(from_attributes=True)

    set_index: int
    weight_kg: float | None
    reps: int | None
    seconds: int | None
    is_warmup: bool
    e1rm_kg: float | None
    is_pr: bool


class WorkoutExerciseOut(BaseModel):
    """Stored exercise entry of a workout."""

    model_config = ConfigDict(from_attributes=True)

    exercise_id: int
    exercise_name: str
    per_side: bool
    superset_group: int | None
    sets: list[SetOut]


class WorkoutOut(BaseModel):
    """Full workout."""

    id: int
    started_at: datetime
    ended_at: datetime | None
    template_id: int | None
    title: str | None
    note: str | None
    source: str
    exercises: list[WorkoutExerciseOut]


class WorkoutSummary(BaseModel):
    """Row of the history list."""

    id: int
    started_at: datetime
    ended_at: datetime | None
    title: str | None
    template_name: str | None
    exercise_count: int
    set_count: int
    pr_count: int
