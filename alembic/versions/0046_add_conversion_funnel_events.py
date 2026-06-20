"""add conversion funnel events

Revision ID: 0046_add_conversion_funnel_events
Revises: 0045_merge_all_alembic_heads
Create Date: 2026-06-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0046_add_conversion_funnel_events"
down_revision: Union[str, None] = "0045_merge_all_alembic_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_EVENT_NAMES = (
    "course_cta_seen",
    "course_started",
    "lesson_started",
    "quiz_completed",
    "ai_explanation_seen",
    "homework_completed",
    "paywall_seen",
    "checkout_opened",
    "payment_screenshot_submitted",
    "payment_approved",
    "payment_rejected",
)


def upgrade() -> None:
    op.create_table(
        "conversion_funnel_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("event_name", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=True),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column("payment_id", sa.Integer(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "event_name IN (%s)" % ", ".join(f"'{name}'" for name in _EVENT_NAMES),
            name="ck_conversion_funnel_events_event_name",
        ),
        sa.ForeignKeyConstraint(["lesson_id"], ["course_lessons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversion_funnel_events_user_id", "conversion_funnel_events", ["user_id"])
    op.create_index("ix_conversion_funnel_events_telegram_id", "conversion_funnel_events", ["telegram_id"])
    op.create_index("ix_conversion_funnel_events_event_name", "conversion_funnel_events", ["event_name"])
    op.create_index("ix_conversion_funnel_events_source", "conversion_funnel_events", ["source"])
    op.create_index("ix_conversion_funnel_events_lesson_id", "conversion_funnel_events", ["lesson_id"])
    op.create_index("ix_conversion_funnel_events_payment_id", "conversion_funnel_events", ["payment_id"])
    op.create_index("ix_conversion_funnel_events_created_at", "conversion_funnel_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_conversion_funnel_events_created_at", table_name="conversion_funnel_events")
    op.drop_index("ix_conversion_funnel_events_payment_id", table_name="conversion_funnel_events")
    op.drop_index("ix_conversion_funnel_events_lesson_id", table_name="conversion_funnel_events")
    op.drop_index("ix_conversion_funnel_events_source", table_name="conversion_funnel_events")
    op.drop_index("ix_conversion_funnel_events_event_name", table_name="conversion_funnel_events")
    op.drop_index("ix_conversion_funnel_events_telegram_id", table_name="conversion_funnel_events")
    op.drop_index("ix_conversion_funnel_events_user_id", table_name="conversion_funnel_events")
    op.drop_table("conversion_funnel_events")
