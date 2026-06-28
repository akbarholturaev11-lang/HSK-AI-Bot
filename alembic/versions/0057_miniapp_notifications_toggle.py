"""add notifications_enabled toggle to course mini app profile

Revision ID: 0057_miniapp_notifications_toggle
Revises: 0056_course_ad_supported_lessons
Create Date: 2026-06-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0057_miniapp_notifications_toggle"
down_revision: Union[str, None] = "0056_course_ad_supported_lessons"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "course_miniapp_profiles",
        sa.Column(
            "notifications_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("course_miniapp_profiles", "notifications_enabled")
