"""add course miniapp foundation

Revision ID: 0048_add_course_miniapp_foundation
Revises: 0047_add_voice_practice_sessions
Create Date: 2026-06-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0048_add_course_miniapp_foundation"
down_revision: Union[str, None] = "0047_add_voice_practice_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_miniapp_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("goal", sa.String(length=32), nullable=False),
        sa.Column("daily_minutes", sa.Integer(), nullable=False),
        sa.Column("start_mode", sa.String(length=24), nullable=False),
        sa.Column("timezone_offset_minutes", sa.Integer(), nullable=False),
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "goal IN ('hsk_exam', 'study_china', 'work_china', 'daily_communication', 'travel')",
            name="ck_course_miniapp_profiles_goal",
        ),
        sa.CheckConstraint(
            "daily_minutes IN (5, 10, 15, 20)",
            name="ck_course_miniapp_profiles_daily_minutes",
        ),
        sa.CheckConstraint(
            "start_mode IN ('lesson_1', 'continue', 'placement')",
            name="ck_course_miniapp_profiles_start_mode",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(
        "ix_course_miniapp_profiles_user_id",
        "course_miniapp_profiles",
        ["user_id"],
    )

    op.create_table(
        "course_feature_usages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("feature_key", sa.String(length=32), nullable=False),
        sa.Column("usage_ref", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "feature_key IN ('lesson', 'voice', 'placement', 'training_test')",
            name="ck_course_feature_usages_feature_key",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "feature_key",
            "usage_ref",
            name="uq_course_feature_usages_user_feature_ref",
        ),
    )
    op.create_index(
        "ix_course_feature_usages_user_id",
        "course_feature_usages",
        ["user_id"],
    )
    op.create_index(
        "ix_course_feature_usages_feature_key",
        "course_feature_usages",
        ["feature_key"],
    )
    op.create_index(
        "ix_course_feature_usages_created_at",
        "course_feature_usages",
        ["created_at"],
    )

    op.create_table(
        "course_miniapp_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("event_name", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=True),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column("lesson_order", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.String(length=80), nullable=True),
        sa.Column("dedupe_key", sa.String(length=120), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["course_lessons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "telegram_id",
            "event_name",
            "dedupe_key",
            name="uq_course_miniapp_events_telegram_event_dedupe",
        ),
    )
    for column_name in (
        "user_id",
        "telegram_id",
        "event_name",
        "source",
        "level",
        "lesson_id",
        "lesson_order",
        "session_id",
        "created_at",
    ):
        op.create_index(
            f"ix_course_miniapp_events_{column_name}",
            "course_miniapp_events",
            [column_name],
        )


def downgrade() -> None:
    for column_name in reversed(
        (
            "user_id",
            "telegram_id",
            "event_name",
            "source",
            "level",
            "lesson_id",
            "lesson_order",
            "session_id",
            "created_at",
        )
    ):
        op.drop_index(
            f"ix_course_miniapp_events_{column_name}",
            table_name="course_miniapp_events",
        )
    op.drop_table("course_miniapp_events")

    op.drop_index("ix_course_feature_usages_created_at", table_name="course_feature_usages")
    op.drop_index("ix_course_feature_usages_feature_key", table_name="course_feature_usages")
    op.drop_index("ix_course_feature_usages_user_id", table_name="course_feature_usages")
    op.drop_table("course_feature_usages")

    op.drop_index("ix_course_miniapp_profiles_user_id", table_name="course_miniapp_profiles")
    op.drop_table("course_miniapp_profiles")
