import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.exercises.models import Exercise
from app.templates.models import WorkoutTemplate


class Workout(Base):
    """A completed strength session."""

    __tablename__ = "workout"
    __table_args__ = (
        CheckConstraint("source IN ('app', 'gravitus')", name="ck_workout_source"),
        UniqueConstraint("source", "external_id", name="uq_workout_source_external_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[uuid.UUID | None] = mapped_column(unique=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("workout_template.id", ondelete="SET NULL")
    )
    title: Mapped[str | None]
    note: Mapped[str | None]
    source: Mapped[str] = mapped_column(String(10), default="app", server_default="app")
    external_id: Mapped[str | None]

    template: Mapped[WorkoutTemplate | None] = relationship()
    exercises: Mapped[list["WorkoutExercise"]] = relationship(
        back_populates="workout",
        order_by="WorkoutExercise.position",
        cascade="all, delete-orphan",
    )


class WorkoutExercise(Base):
    """An exercise performed within a workout."""

    __tablename__ = "workout_exercise"

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("workout.id", ondelete="CASCADE"))
    position: Mapped[int]
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercise.id"), index=True)
    superset_group: Mapped[int | None]

    workout: Mapped[Workout] = relationship(back_populates="exercises")
    exercise: Mapped[Exercise] = relationship()
    sets: Mapped[list["WorkoutSet"]] = relationship(
        back_populates="workout_exercise",
        order_by="WorkoutSet.set_index",
        cascade="all, delete-orphan",
    )


class WorkoutSet(Base):
    """A single logged set."""

    __tablename__ = "workout_set"

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_exercise_id: Mapped[int] = mapped_column(
        ForeignKey("workout_exercise.id", ondelete="CASCADE")
    )
    set_index: Mapped[int]
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    reps: Mapped[int | None]
    seconds: Mapped[int | None]
    distance_m: Mapped[float | None]
    is_warmup: Mapped[bool] = mapped_column(default=False, server_default="false")
    e1rm_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    is_pr: Mapped[bool] = mapped_column(default=False, server_default="false")

    workout_exercise: Mapped[WorkoutExercise] = relationship(back_populates="sets")
