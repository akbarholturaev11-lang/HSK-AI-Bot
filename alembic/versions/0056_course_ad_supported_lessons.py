"""add course ad creatives and ad view tracking

Revision ID: 0056_course_ad_supported_lessons
Revises: 0055_free_tier_monetization_policy
Create Date: 2026-06-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0056_course_ad_supported_lessons"
down_revision: Union[str, None] = "0055_free_tier_monetization_policy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_ad_creatives",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("media_path", sa.String(length=512), nullable=False),
        sa.Column("media_type", sa.String(length=16), nullable=False, server_default="video"),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_course_ad_creatives_is_active"), "course_ad_creatives", ["is_active"], unique=False)

    op.create_table(
        "course_ad_views",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ad_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("user_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("lesson_order", sa.Integer(), nullable=False),
        sa.Column("placement", sa.String(length=16), nullable=False),
        sa.Column("watched_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ad_id"], ["course_ad_creatives.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_course_ad_views_ad_id"), "course_ad_views", ["ad_id"], unique=False)
    op.create_index(op.f("ix_course_ad_views_completed"), "course_ad_views", ["completed"], unique=False)
    op.create_index(op.f("ix_course_ad_views_created_at"), "course_ad_views", ["created_at"], unique=False)
    op.create_index(op.f("ix_course_ad_views_lesson_order"), "course_ad_views", ["lesson_order"], unique=False)
    op.create_index(op.f("ix_course_ad_views_level"), "course_ad_views", ["level"], unique=False)
    op.create_index(op.f("ix_course_ad_views_placement"), "course_ad_views", ["placement"], unique=False)
    op.create_index(op.f("ix_course_ad_views_user_id"), "course_ad_views", ["user_id"], unique=False)
    op.create_index(op.f("ix_course_ad_views_user_telegram_id"), "course_ad_views", ["user_telegram_id"], unique=False)
    op.create_index(
        "ix_course_ad_views_user_lesson_placement",
        "course_ad_views",
        ["user_telegram_id", "level", "lesson_order", "placement"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_course_ad_views_user_lesson_placement", table_name="course_ad_views")
    op.drop_index(op.f("ix_course_ad_views_user_telegram_id"), table_name="course_ad_views")
    op.drop_index(op.f("ix_course_ad_views_user_id"), table_name="course_ad_views")
    op.drop_index(op.f("ix_course_ad_views_placement"), table_name="course_ad_views")
    op.drop_index(op.f("ix_course_ad_views_level"), table_name="course_ad_views")
    op.drop_index(op.f("ix_course_ad_views_lesson_order"), table_name="course_ad_views")
    op.drop_index(op.f("ix_course_ad_views_created_at"), table_name="course_ad_views")
    op.drop_index(op.f("ix_course_ad_views_completed"), table_name="course_ad_views")
    op.drop_index(op.f("ix_course_ad_views_ad_id"), table_name="course_ad_views")
    op.drop_table("course_ad_views")
    op.drop_index(op.f("ix_course_ad_creatives_is_active"), table_name="course_ad_creatives")
    op.drop_table("course_ad_creatives")
