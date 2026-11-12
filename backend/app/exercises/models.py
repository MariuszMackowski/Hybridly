from sqlalchemy import CheckConstraint, Index, String, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Exercise(Base):
    """An exercise from the user's editable exercise database."""

    __tablename__ = "exercise"
    __table_args__ = (
        CheckConstraint("measure IN ('reps', 'time', 'distance')", name="ck_exercise_measure"),
        Index("uq_exercise_name_lower", text("lower(name)"), unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    primary_muscles: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    secondary_muscles: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    measure: Mapped[str] = mapped_column(String(10), default="reps", server_default="reps")
    load_factor: Mapped[float] = mapped_column(default=1.0, server_default="1.0")
    increment_kg: Mapped[float] = mapped_column(default=2.5, server_default="2.5")
    is_bodyweight: Mapped[bool] = mapped_column(default=False, server_default="false")
    per_side: Mapped[bool] = mapped_column(default=False, server_default="false")
    grips: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    note: Mapped[str | None]
    archived: Mapped[bool] = mapped_column(default=False, server_default="false")
