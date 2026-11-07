"""best_efforts

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-07 10:30:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0007'
down_revision: str | None = '0006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Fastest standard-distance segments per activity (filled by reparse-activities)."""
    op.add_column(
        'activity',
        sa.Column('best_efforts', postgresql.JSONB(), server_default='{}', nullable=False),
    )


def downgrade() -> None:
    """Drop best efforts."""
    op.drop_column('activity', 'best_efforts')
