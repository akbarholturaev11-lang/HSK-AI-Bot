"""connect voice to course

Revision ID: 0051_connect_voice_to_course
Revises: 0050_add_course_gamification
Create Date: 2026-06-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0051_connect_voice_to_course"
down_revision: Union[str, None] = "0050_add_course_gamification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("voice_practice_sessions", sa.Column("lesson_id", sa.Integer(), nullable=True))
    op.add_column(
        "voice_practice_sessions",
        sa.Column("target_words", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
    )
    op.create_foreign_key(
        "fk_voice_practice_sessions_lesson_id_course_lessons",
        "voice_practice_sessions",
        "course_lessons",
        ["lesson_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_voice_practice_sessions_lesson_id", "voice_practice_sessions", ["lesson_id"])


def downgrade() -> None:
    op.drop_index("ix_voice_practice_sessions_lesson_id", table_name="voice_practice_sessions")
    op.drop_constraint(
        "fk_voice_practice_sessions_lesson_id_course_lessons",
        "voice_practice_sessions",
        type_="foreignkey",
    )
    op.drop_column("voice_practice_sessions", "target_words")
    op.drop_column("voice_practice_sessions", "lesson_id")
