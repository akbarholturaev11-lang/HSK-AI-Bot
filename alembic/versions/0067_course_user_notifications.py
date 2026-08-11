"""add course user notification feed

Revision ID: 0067_course_user_notifications
Revises: 0066_desktop_foundation
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0067_course_user_notifications"
down_revision: Union[str, None] = "0066_desktop_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_user_notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="course_notification"),
        sa.Column("language", sa.String(length=8), nullable=False, server_default="ru"),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False, server_default="course"),
        sa.Column("level", sa.String(length=32), nullable=True),
        sa.Column("lesson_order", sa.Integer(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "telegram_id",
            "key",
            "dedupe_key",
            name="uq_course_user_notifications_telegram_key_dedupe",
        ),
    )
    op.create_index(
        op.f("ix_course_user_notifications_user_id"),
        "course_user_notifications",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_course_user_notifications_telegram_id"),
        "course_user_notifications",
        ["telegram_id"],
    )
    op.create_index(
        op.f("ix_course_user_notifications_key"),
        "course_user_notifications",
        ["key"],
    )
    op.create_index(
        op.f("ix_course_user_notifications_source"),
        "course_user_notifications",
        ["source"],
    )
    op.create_index(
        op.f("ix_course_user_notifications_created_at"),
        "course_user_notifications",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_course_user_notifications_created_at"), table_name="course_user_notifications")
    op.drop_index(op.f("ix_course_user_notifications_source"), table_name="course_user_notifications")
    op.drop_index(op.f("ix_course_user_notifications_key"), table_name="course_user_notifications")
    op.drop_index(op.f("ix_course_user_notifications_telegram_id"), table_name="course_user_notifications")
    op.drop_index(op.f("ix_course_user_notifications_user_id"), table_name="course_user_notifications")
    op.drop_table("course_user_notifications")
