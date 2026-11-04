from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.exercises.models import Exercise


class WorkoutTemplate(Base):
    """A reusable strength session (e.g. Upper A)."""

    __tablename__ = "workout_template"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    note: Mapped[str | None]
    warmup_items: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    cooldown_items: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    archived: Mapped[bool] = mapped_column(default=False, server_default="false")

    slots: Mapped[list["TemplateSlot"]] = relationship(
        back_populates="template",
        order_by="TemplateSlot.position",
        cascade="all, delete-orphan",
    )


class TemplateSlot(Base):
    """One exercise position in a template, with its targets."""

    __tablename__ = "template_slot"
    __table_args__ = (
        CheckConstraint("block IN ('main', 'finisher')", name="ck_template_slot_block"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("workout_template.id", ondelete="CASCADE"))
    position: Mapped[int]
    block: Mapped[str] = mapped_column(String(10), default="main", server_default="main")
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercise.id"))
    alternative_exercise_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), default=list, server_default="{}"
    )
    warmup_sets: Mapped[int] = mapped_column(default=0, server_default="0")
    sets: Mapped[int]
    rep_min: Mapped[int]
    rep_max: Mapped[int]
    superset_group: Mapped[int | None]
    note: Mapped[str | None]

    template: Mapped[WorkoutTemplate] = relationship(back_populates="slots")
    exercise: Mapped[Exercise] = relationship()


class WeeklyTemplate(Base):
    """Template suggested for a weekday (0 = Monday)."""

    __tablename__ = "weekly_template"

    weekday: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("workout_template.id", ondelete="SET NULL")
    )

    template: Mapped[WorkoutTemplate | None] = relationship()
