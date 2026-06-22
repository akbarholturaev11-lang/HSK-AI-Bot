"""add voice practice sessions

Revision ID: 0047_add_voice_practice_sessions
Revises: 0046_add_conversion_funnel_events
Create Date: 2026-06-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0047_add_voice_practice_sessions"
down_revision: Union[str, None] = "0046_add_conversion_funnel_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "voice_practice_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.Column("level", sa.String(length=24), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("voice", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("turn_count", sa.Integer(), nullable=False),
        sa.Column("history", sa.JSON(), nullable=False),
        sa.Column("corrections", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_voice_practice_sessions_user_telegram_id", "voice_practice_sessions", ["user_telegram_id"])
    op.create_index("ix_voice_practice_sessions_status", "voice_practice_sessions", ["status"])
    op.create_index("ix_voice_practice_sessions_started_at", "voice_practice_sessions", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_voice_practice_sessions_started_at", table_name="voice_practice_sessions")
    op.drop_index("ix_voice_practice_sessions_status", table_name="voice_practice_sessions")
    op.drop_index("ix_voice_practice_sessions_user_telegram_id", table_name="voice_practice_sessions")
    op.drop_table("voice_practice_sessions")
