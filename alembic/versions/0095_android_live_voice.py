"""Separate Android live voice sessions from upload based sessions.

Revision ID: 0095_android_live_voice
Revises: 0094_account_notice_deliveries
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0095_android_live_voice"
down_revision: Union[str, None] = "0094_account_notice_deliveries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "voice_practice_sessions",
        sa.Column("mode", sa.String(length=8), server_default="turn", nullable=False),
    )
    op.add_column(
        "voice_practice_sessions",
        sa.Column("live_connection_token", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "voice_practice_sessions",
        sa.Column("live_connection_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "voice_practice_sessions",
        sa.Column("live_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "voice_practice_sessions",
        sa.Column("live_cost_usd", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "voice_practice_sessions",
        sa.Column("live_resumption_handle", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_voice_practice_sessions_live_connection_expires_at",
        "voice_practice_sessions",
        ["live_connection_expires_at"],
    )
    op.alter_column("voice_practice_sessions", "mode", server_default=None)
    op.alter_column("voice_practice_sessions", "live_cost_usd", server_default=None)


def downgrade() -> None:
    op.drop_index(
        "ix_voice_practice_sessions_live_connection_expires_at",
        table_name="voice_practice_sessions",
    )
    op.drop_column("voice_practice_sessions", "live_connection_expires_at")
    op.drop_column("voice_practice_sessions", "live_connection_token")
    op.drop_column("voice_practice_sessions", "live_started_at")
    op.drop_column("voice_practice_sessions", "live_cost_usd")
    op.drop_column("voice_practice_sessions", "live_resumption_handle")
    op.drop_column("voice_practice_sessions", "mode")
