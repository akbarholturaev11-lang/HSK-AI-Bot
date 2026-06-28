"""add link_url to course ad creatives

Revision ID: 0058_course_ad_link_url
Revises: 0057_miniapp_notifications_toggle
Create Date: 2026-06-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0058_course_ad_link_url"
down_revision: Union[str, None] = "0057_miniapp_notifications_toggle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "course_ad_creatives",
        sa.Column("link_url", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("course_ad_creatives", "link_url")
