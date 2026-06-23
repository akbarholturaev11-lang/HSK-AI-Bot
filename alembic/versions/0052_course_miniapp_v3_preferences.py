"""course miniapp v3 preferences

Revision ID: 0052_course_miniapp_v3_preferences
Revises: 0051_connect_voice_to_course
Create Date: 2026-06-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0052_course_miniapp_v3_preferences"
down_revision: Union[str, None] = "0051_connect_voice_to_course"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROFILE_TABLE = "course_miniapp_profiles"
DAILY_MINUTES_CONSTRAINT_NAMES = (
    "ck_course_miniapp_profiles_daily_minutes",
    "daily_minutes",
    "course_miniapp_profiles_daily_minutes_check",
)


def _drop_daily_minutes_constraint() -> None:
    for name in DAILY_MINUTES_CONSTRAINT_NAMES:
        op.execute(sa.text(f"ALTER TABLE {PROFILE_TABLE} DROP CONSTRAINT IF EXISTS {name}"))


def upgrade() -> None:
    _drop_daily_minutes_constraint()
    op.create_check_constraint(
        "ck_course_miniapp_profiles_daily_minutes",
        PROFILE_TABLE,
        "daily_minutes IN (5, 10, 15, 20, 30)",
    )


def downgrade() -> None:
    _drop_daily_minutes_constraint()
    op.create_check_constraint(
        "ck_course_miniapp_profiles_daily_minutes",
        PROFILE_TABLE,
        "daily_minutes IN (5, 10, 15, 20)",
    )
