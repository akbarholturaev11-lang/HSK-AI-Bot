"""add notification templates and motivation reminder tracking

Revision ID: 0054_add_notification_motivation
Revises: 0053_add_subscription_entry_events
Create Date: 2026-06-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0054_add_notification_motivation"
down_revision: Union[str, None] = "0053_add_subscription_entry_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=40), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("text_uz", sa.Text(), nullable=True),
        sa.Column("text_ru", sa.Text(), nullable=True),
        sa.Column("text_tj", sa.Text(), nullable=True),
        sa.Column("media_type", sa.String(length=16), nullable=False, server_default="none"),
        sa.Column("media_path", sa.String(length=512), nullable=True),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_notification_templates_key"),
        "notification_templates",
        ["key"],
        unique=True,
    )

    op.add_column(
        "course_miniapp_profiles",
        sa.Column("last_known_rank", sa.Integer(), nullable=True),
    )
    op.add_column(
        "course_miniapp_profiles",
        sa.Column("motivation_overtaken_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "course_miniapp_profiles",
        sa.Column("motivation_goal_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "course_miniapp_profiles",
        sa.Column("motivation_streak_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("course_miniapp_profiles", "motivation_streak_date")
    op.drop_column("course_miniapp_profiles", "motivation_goal_date")
    op.drop_column("course_miniapp_profiles", "motivation_overtaken_date")
    op.drop_column("course_miniapp_profiles", "last_known_rank")
    op.drop_index(
        op.f("ix_notification_templates_key"),
        table_name="notification_templates",
    )
    op.drop_table("notification_templates")
