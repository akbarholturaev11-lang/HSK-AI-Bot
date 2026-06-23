"""course miniapp v3 preferences

Revision ID: 0052_course_miniapp_v3_preferences
Revises: 0051_connect_voice_to_course
Create Date: 2026-06-23
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0052_course_miniapp_v3_preferences"
down_revision: Union[str, None] = "0051_connect_voice_to_course"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("daily_minutes", "course_miniapp_profiles", type_="check")
    op.create_check_constraint(
        "daily_minutes",
        "course_miniapp_profiles",
        "daily_minutes IN (5, 10, 15, 20, 30)",
    )


def downgrade() -> None:
    op.drop_constraint("daily_minutes", "course_miniapp_profiles", type_="check")
    op.create_check_constraint(
        "daily_minutes",
        "course_miniapp_profiles",
        "daily_minutes IN (5, 10, 15, 20)",
    )
