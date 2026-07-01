"""add review_words to voice practice sessions

Revision ID: 0062_voice_review_words
Revises: 0061_course_ad_language
Create Date: 2026-07-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0062_voice_review_words"
down_revision: Union[str, None] = "0061_course_ad_language"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "voice_practice_sessions",
        sa.Column("review_words", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("voice_practice_sessions", "review_words")
