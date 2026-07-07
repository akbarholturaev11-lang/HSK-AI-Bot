"""add course promo sections (ad-flow cooperation + bot promo)

Revision ID: 0064_course_promo_sections
Revises: 0063_course_ad_media_backup
Create Date: 2026-07-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0064_course_promo_sections"
down_revision: Union[str, None] = "0063_course_ad_media_backup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_promo_sections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="bot_promo"),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("link_url", sa.String(length=512), nullable=True),
        sa.Column("source_language", sa.String(length=8), nullable=False, server_default="uz"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_course_promo_sections_is_active",
        "course_promo_sections",
        ["is_active"],
    )
    op.create_index(
        "ix_course_promo_sections_sort_order",
        "course_promo_sections",
        ["sort_order"],
    )


def downgrade() -> None:
    op.drop_index("ix_course_promo_sections_sort_order", table_name="course_promo_sections")
    op.drop_index("ix_course_promo_sections_is_active", table_name="course_promo_sections")
    op.drop_table("course_promo_sections")
