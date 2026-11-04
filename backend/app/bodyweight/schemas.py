from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class BodyweightIn(BaseModel):
    """Bodyweight value for a day."""

    kg: float = Field(gt=20, lt=300)


class BodyweightOut(BaseModel):
    """Stored bodyweight entry."""

    model_config = ConfigDict(from_attributes=True)

    day: date
    kg: float
