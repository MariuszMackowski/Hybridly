from datetime import date

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Video(Base):
    """A YouTube video in the home-workout library."""

    __tablename__ = "video"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str]
    youtube_id: Mapped[str | None]
    title: Mapped[str]
    thumbnail_url: Mapped[str | None]
    note: Mapped[str | None]


class Routine(Base):
    """A home routine slot (e.g. Core) with alternative videos — doing one counts."""

    __tablename__ = "routine"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    note: Mapped[str | None]
    video_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)
    archived: Mapped[bool] = mapped_column(default=False)


class RoutineWeekday(Base):
    """Routine suggested on a weekday (0 = Monday)."""

    __tablename__ = "routine_weekday"

    weekday: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    routine_id: Mapped[int] = mapped_column(
        ForeignKey("routine.id", ondelete="CASCADE"), primary_key=True
    )


class RoutineLog(Base):
    """Routine ticked as done on a day."""

    __tablename__ = "routine_log"

    day: Mapped[date] = mapped_column(primary_key=True)
    routine_id: Mapped[int] = mapped_column(
        ForeignKey("routine.id", ondelete="CASCADE"), primary_key=True
    )
