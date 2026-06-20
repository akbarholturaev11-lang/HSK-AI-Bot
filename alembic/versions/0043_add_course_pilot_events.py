"""add course pilot events

Revision ID: 0043_add_course_pilot_events
Revises: 0042_add_daily_practice_fields
Create Date: 2026-06-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0043_add_course_pilot_events"
down_revision: Union[str, None] = "0042_add_daily_practice_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_pilot_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("lesson_order", sa.Integer(), nullable=False),
        sa.Column("block_no", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("step_name", sa.String(length=64), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["course_lessons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_course_pilot_events_user_id", "course_pilot_events", ["user_id"])
    op.create_index("ix_course_pilot_events_telegram_id", "course_pilot_events", ["telegram_id"])
    op.create_index("ix_course_pilot_events_lesson_id", "course_pilot_events", ["lesson_id"])
    op.create_index("ix_course_pilot_events_level", "course_pilot_events", ["level"])
    op.create_index("ix_course_pilot_events_lesson_order", "course_pilot_events", ["lesson_order"])
    op.create_index("ix_course_pilot_events_event_type", "course_pilot_events", ["event_type"])
    op.create_index("ix_course_pilot_events_step_name", "course_pilot_events", ["step_name"])
    op.create_index("ix_course_pilot_events_created_at", "course_pilot_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_course_pilot_events_created_at", table_name="course_pilot_events")
    op.drop_index("ix_course_pilot_events_step_name", table_name="course_pilot_events")
    op.drop_index("ix_course_pilot_events_event_type", table_name="course_pilot_events")
    op.drop_index("ix_course_pilot_events_lesson_order", table_name="course_pilot_events")
    op.drop_index("ix_course_pilot_events_level", table_name="course_pilot_events")
    op.drop_index("ix_course_pilot_events_lesson_id", table_name="course_pilot_events")
    op.drop_index("ix_course_pilot_events_telegram_id", table_name="course_pilot_events")
    op.drop_index("ix_course_pilot_events_user_id", table_name="course_pilot_events")
    op.drop_table("course_pilot_events")
