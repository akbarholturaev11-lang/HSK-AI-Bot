"""add course mistakes

Revision ID: 0049_add_course_mistakes
Revises: 0048_add_course_miniapp_foundation
Create Date: 2026-06-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0049_add_course_mistakes"
down_revision: Union[str, None] = "0048_add_course_miniapp_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_mistakes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column("mistake_key", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=True),
        sa.Column("lesson_order", sa.Integer(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("user_answer", sa.Text(), nullable=True),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("wrong_count", sa.Integer(), nullable=False),
        sa.Column("review_count", sa.Integer(), nullable=False),
        sa.Column("resolved_count", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "category IN ('word', 'grammar', 'character', 'pronunciation')",
            name="ck_course_mistakes_category",
        ),
        sa.ForeignKeyConstraint(["lesson_id"], ["course_lessons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "mistake_key", name="uq_course_mistakes_user_key"),
    )
    for column_name in ("user_id", "lesson_id", "category", "source", "level", "last_seen_at"):
        op.create_index(
            f"ix_course_mistakes_{column_name}",
            "course_mistakes",
            [column_name],
        )


def downgrade() -> None:
    for column_name in reversed(("user_id", "lesson_id", "category", "source", "level", "last_seen_at")):
        op.drop_index(f"ix_course_mistakes_{column_name}", table_name="course_mistakes")
    op.drop_table("course_mistakes")
