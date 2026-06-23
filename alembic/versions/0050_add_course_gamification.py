"""add course gamification

Revision ID: 0050_add_course_gamification
Revises: 0049_add_course_mistakes
Create Date: 2026-06-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0050_add_course_gamification"
down_revision: Union[str, None] = "0049_add_course_mistakes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("course_miniapp_profiles", sa.Column("xp_total", sa.Integer(), server_default="0", nullable=False))
    op.add_column("course_miniapp_profiles", sa.Column("current_streak", sa.Integer(), server_default="0", nullable=False))
    op.add_column("course_miniapp_profiles", sa.Column("longest_streak", sa.Integer(), server_default="0", nullable=False))
    op.add_column("course_miniapp_profiles", sa.Column("last_activity_date", sa.Date(), nullable=True))

    op.create_table(
        "course_xp_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("activity_type", sa.String(length=32), nullable=False),
        sa.Column("activity_ref", sa.String(length=120), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "activity_ref", name="uq_course_xp_events_user_activity_ref"),
    )
    for column_name in ("user_id", "activity_type", "activity_date", "week_start", "created_at"):
        op.create_index(f"ix_course_xp_events_{column_name}", "course_xp_events", [column_name])


def downgrade() -> None:
    for column_name in reversed(("user_id", "activity_type", "activity_date", "week_start", "created_at")):
        op.drop_index(f"ix_course_xp_events_{column_name}", table_name="course_xp_events")
    op.drop_table("course_xp_events")
    op.drop_column("course_miniapp_profiles", "last_activity_date")
    op.drop_column("course_miniapp_profiles", "longest_streak")
    op.drop_column("course_miniapp_profiles", "current_streak")
    op.drop_column("course_miniapp_profiles", "xp_total")
