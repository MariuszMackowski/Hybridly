from datetime import date
from decimal import Decimal

from sqlalchemy import Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class BodyweightEntry(Base):
    """Bodyweight measured on a given day."""

    __tablename__ = "bodyweight_entry"

    day: Mapped[date] = mapped_column(primary_key=True)
    kg: Mapped[Decimal] = mapped_column(Numeric(5, 2))
