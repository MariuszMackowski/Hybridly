"""grips

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-12 10:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0008'
down_revision: str | None = '0007'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Grip options per exercise and the grip used for each logged exercise entry."""
    op.add_column(
        'exercise',
        sa.Column('grips', postgresql.ARRAY(sa.String()), server_default='{}', nullable=False),
    )
    op.add_column('workout_exercise', sa.Column('grip', sa.String(40), nullable=True))


def downgrade() -> None:
    """Drop grip columns."""
    op.drop_column('workout_exercise', 'grip')
    op.drop_column('exercise', 'grips')
