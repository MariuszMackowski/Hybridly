from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SetIn(BaseModel):
    """One logged set: reps-, time- or distance-based."""

    weight_kg: float | None = Field(default=None, ge=0)
    reps: int | None = Field(default=None, ge=1, le=100)
    seconds: int | None = Field(default=None, ge=1)
    distance_m: float | None = Field(default=None, gt=0)
    is_warmup: bool = False

    @model_validator(mode="after")
    def _one_result(self) -> "SetIn":
        """Require exactly one of reps / seconds / distance."""
        if sum(v is not None for v in (self.reps, self.seconds, self.distance_m)) != 1:
            raise ValueError("set needs exactly one of reps, seconds or distance")
        return self


class WorkoutExerciseIn(BaseModel):
    """An exercise with its sets, in performed order."""

    exercise_id: int
    superset_group: int | None = None
    grip: str | None = Field(default=None, max_length=40)
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
    distance_m: float | None
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
    grip: str | None
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
