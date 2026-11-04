from datetime import date as Date
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TrainingPlan(Base):
    """An imported running plan; newer plans take over from their effective date."""

    __tablename__ = "training_plan"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    goal: Mapped[dict | None] = mapped_column(JSONB)
    notes: Mapped[list] = mapped_column(JSONB, default=list)
    source_yaml: Mapped[str]
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_from: Mapped[Date] = mapped_column(index=True)

    weeks: Mapped[list["PlanWeek"]] = relationship(
        back_populates="plan", order_by="PlanWeek.start", cascade="all, delete-orphan"
    )


class PlanWeek(Base):
    """Monday-to-Sunday week of a plan."""

    __tablename__ = "plan_week"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("training_plan.id", ondelete="CASCADE"))
    week: Mapped[int]
    start: Mapped[Date] = mapped_column(index=True)
    phase: Mapped[str | None]
    flags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    target_km: Mapped[float | None]
    note: Mapped[str | None]
    day_notes: Mapped[list] = mapped_column(JSONB, default=list)

    plan: Mapped[TrainingPlan] = relationship(back_populates="weeks")
    sessions: Mapped[list["PlanSession"]] = relationship(
        back_populates="week", order_by="PlanSession.date", cascade="all, delete-orphan"
    )


class PlanSession(Base):
    """One planned run, optionally matched to the activity that fulfilled it."""

    __tablename__ = "plan_session"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("training_plan.id", ondelete="CASCADE"))
    week_id: Mapped[int] = mapped_column(ForeignKey("plan_week.id", ondelete="CASCADE"))
    date: Mapped[Date] = mapped_column(index=True)
    type: Mapped[str] = mapped_column(String(20))
    title: Mapped[str]
    description: Mapped[str] = mapped_column(default="")
    distance_km: Mapped[float | None]
    pace_min_s: Mapped[int | None]
    pace_max_s: Mapped[int | None]
    hr_min: Mapped[int | None]
    hr_max: Mapped[int | None]
    intervals: Mapped[dict | None] = mapped_column(JSONB)
    activity_id: Mapped[int | None] = mapped_column(
        ForeignKey("activity.id", ondelete="SET NULL"), unique=True
    )

    week: Mapped[PlanWeek] = relationship(back_populates="sessions")
    plan: Mapped[TrainingPlan] = relationship()
