"""add ad_type + button_text to course ad creatives

Revision ID: 0064_course_ad_type_button
Revises: 0064_course_promo_sections
Create Date: 2026-07-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0064_course_ad_type_button"
down_revision: Union[str, None] = "0064_course_promo_sections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "course_ad_creatives",
        sa.Column("ad_type", sa.String(length=16), nullable=False, server_default="odiy"),
    )
    op.add_column(
        "course_ad_creatives",
        sa.Column("button_text", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("course_ad_creatives", "button_text")
    op.drop_column("course_ad_creatives", "ad_type")
