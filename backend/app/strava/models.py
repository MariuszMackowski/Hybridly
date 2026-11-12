from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class StravaAccount(Base):
    """Single-row Strava connection: the user's own API app credentials and OAuth tokens."""

    __tablename__ = "strava_account"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False, default=1)
    client_id: Mapped[str | None] = mapped_column(String(20))
    client_secret: Mapped[str | None] = mapped_column(String(100))
    access_token: Mapped[str | None]
    refresh_token: Mapped[str | None]
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    athlete_name: Mapped[str | None]
    pending_state: Mapped[str | None]
