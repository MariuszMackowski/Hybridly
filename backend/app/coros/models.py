from datetime import date, datetime

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CorosAccount(Base):
    """Single-row COROS connection: OAuth client, tokens and last sync state."""

    __tablename__ = "coros_account"
    __table_args__ = (
        CheckConstraint(
            "status IN ('disconnected', 'connected', 'needs_reconnect')", name="ck_coros_status"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False, default=1)
    server_url: Mapped[str]
    client_id: Mapped[str | None]
    redirect_uri: Mapped[str | None]
    access_token: Mapped[str | None]
    refresh_token: Mapped[str | None]
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pending_state: Mapped[str | None]
    pending_verifier: Mapped[str | None]
    status: Mapped[str] = mapped_column(String(20), default="disconnected")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_status: Mapped[dict | None] = mapped_column(JSONB)


class CorosDaily(Base):
    """Daily COROS snapshot (recovery, training load) kept as raw text plus parsed data."""

    __tablename__ = "coros_daily"

    day: Mapped[date] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), primary_key=True)
    raw_text: Mapped[str]
    data: Mapped[dict | list] = mapped_column(JSONB)
