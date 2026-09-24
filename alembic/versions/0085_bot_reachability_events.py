"""store Telegram bot reachability transitions

Revision ID: 0085_bot_reachability_events
Revises: 0084_bot_feedback_prompt_attempts
Create Date: 2026-09-24
"""

from alembic import op
import sqlalchemy as sa


revision = "0085_bot_reachability_events"
down_revision = "0084_bot_feedback_prompt_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_reachability_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_bot_reachability_events_user_id",
        "bot_reachability_events",
        ["user_id"],
    )
    op.create_index(
        "ix_bot_reachability_events_telegram_id",
        "bot_reachability_events",
        ["telegram_id"],
    )
    op.create_index(
        "ix_bot_reachability_events_event_type",
        "bot_reachability_events",
        ["event_type"],
    )
    op.create_index(
        "ix_bot_reachability_events_created_at",
        "bot_reachability_events",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_bot_reachability_events_created_at", table_name="bot_reachability_events")
    op.drop_index("ix_bot_reachability_events_event_type", table_name="bot_reachability_events")
    op.drop_index("ix_bot_reachability_events_telegram_id", table_name="bot_reachability_events")
    op.drop_index("ix_bot_reachability_events_user_id", table_name="bot_reachability_events")
    op.drop_table("bot_reachability_events")
