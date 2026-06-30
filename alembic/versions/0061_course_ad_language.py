"""add language to course ad creatives

Revision ID: 0061_course_ad_language
Revises: 0060_subscription_churn_flow
Create Date: 2026-06-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0061_course_ad_language"
down_revision: Union[str, None] = "0060_subscription_churn_flow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "course_ad_creatives",
        sa.Column(
            "language",
            sa.String(length=8),
            nullable=False,
            server_default="all",
        ),
    )
    op.create_index(
        "ix_course_ad_creatives_language",
        "course_ad_creatives",
        ["language"],
    )


def downgrade() -> None:
    op.drop_index("ix_course_ad_creatives_language", table_name="course_ad_creatives")
    op.drop_column("course_ad_creatives", "language")
