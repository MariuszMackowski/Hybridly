from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.muscles import Muscle


class ExerciseIn(BaseModel):
    """Editable exercise fields."""

    name: str = Field(min_length=1, max_length=120)
    aliases: list[str] = []
    primary_muscles: list[Muscle]
    secondary_muscles: list[Muscle] = []
    measure: Literal["reps", "time", "distance"] = "reps"
    load_factor: float = Field(default=1.0, ge=0)
    increment_kg: float = Field(default=2.5, ge=0)
    is_bodyweight: bool = False
    per_side: bool = False
    grips: list[str] = []
    note: str | None = None


class ExerciseOut(ExerciseIn):
    """Exercise as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    archived: bool
