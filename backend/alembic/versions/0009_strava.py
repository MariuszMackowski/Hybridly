"""strava

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-12 18:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0009'
down_revision: str | None = '0008'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Strava connection and the Strava activity each workout was sent to."""
    op.create_table(
        'strava_account',
        sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('client_id', sa.String(20), nullable=True),
        sa.Column('client_secret', sa.String(100), nullable=True),
        sa.Column('access_token', sa.String(), nullable=True),
        sa.Column('refresh_token', sa.String(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('athlete_name', sa.String(), nullable=True),
        sa.Column('pending_state', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.add_column('workout', sa.Column('strava_activity_id', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    """Drop the Strava connection and links."""
    op.drop_column('workout', 'strava_activity_id')
    op.drop_table('strava_account')
