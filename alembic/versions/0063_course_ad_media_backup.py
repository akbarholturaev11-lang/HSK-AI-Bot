"""add media backup to course ad creatives

Revision ID: 0063_course_ad_media_backup
Revises: 0062_voice_review_words
Create Date: 2026-07-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0063_course_ad_media_backup"
down_revision: Union[str, None] = "0062_voice_review_words"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "course_ad_creatives",
        sa.Column("media_blob", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "course_ad_creatives",
        sa.Column("media_size", sa.Integer(), nullable=True),
    )
    op.add_column(
        "course_ad_creatives",
        sa.Column("media_checksum", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("course_ad_creatives", "media_checksum")
    op.drop_column("course_ad_creatives", "media_size")
    op.drop_column("course_ad_creatives", "media_blob")
