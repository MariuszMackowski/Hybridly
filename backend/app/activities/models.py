from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Activity(Base):
    """A cardio activity (run, walk, …) imported from COROS or an uploaded FIT file."""

    __tablename__ = "activity"
    __table_args__ = (
        CheckConstraint("source IN ('coros', 'upload')", name="ck_activity_source"),
        UniqueConstraint("started_at", name="uq_activity_started_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(10))
    external_id: Mapped[str | None] = mapped_column(unique=True)
    sport: Mapped[str] = mapped_column(String(20), index=True)
    sport_type: Mapped[int | None]
    name: Mapped[str | None]
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_s: Mapped[int]
    distance_m: Mapped[float | None]
    avg_hr: Mapped[int | None]
    max_hr: Mapped[int | None]
    avg_speed: Mapped[float | None]
    ascent_m: Mapped[float | None]
    calories: Mapped[int | None]
    avg_cadence_spm: Mapped[int | None]
    training_load: Mapped[int | None]
    aerobic_te: Mapped[float | None]
    anaerobic_te: Mapped[float | None]
    fit_sha256: Mapped[str] = mapped_column(String(64), unique=True)
    fit_path: Mapped[str]
    streams: Mapped[dict] = mapped_column(JSONB, default=dict)

    laps: Mapped[list["ActivityLap"]] = relationship(
        back_populates="activity", order_by="ActivityLap.index", cascade="all, delete-orphan"
    )


class ActivityLap(Base):
    """A lap (auto km split or interval segment) of an activity."""

    __tablename__ = "activity_lap"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activity.id", ondelete="CASCADE"))
    index: Mapped[int]
    start_offset_s: Mapped[int]
    duration_s: Mapped[int]
    distance_m: Mapped[float | None]
    avg_hr: Mapped[int | None]
    max_hr: Mapped[int | None]
    avg_speed: Mapped[float | None]
    avg_cadence_spm: Mapped[int | None]

    activity: Mapped[Activity] = relationship(back_populates="laps")
