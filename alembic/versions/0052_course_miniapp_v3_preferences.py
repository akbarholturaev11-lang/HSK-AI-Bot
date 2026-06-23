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
DAILY_MINUTES_CONSTRAINT = "ck_course_miniapp_profiles_daily_minutes"

DROP_DAILY_MINUTES_CONSTRAINTS_SQL = f"""
DO $$
DECLARE
    item record;
BEGIN
    FOR item IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = '{PROFILE_TABLE}'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) ILIKE '%daily_minutes%'
    LOOP
        EXECUTE format('ALTER TABLE {PROFILE_TABLE} DROP CONSTRAINT IF EXISTS %I', item.conname);
    END LOOP;
END $$;
"""


def _drop_daily_minutes_constraint() -> None:
    op.execute(sa.text(DROP_DAILY_MINUTES_CONSTRAINTS_SQL))


def _create_daily_minutes_constraint(allowed_minutes: str) -> None:
    op.execute(
        sa.text(
            f"ALTER TABLE {PROFILE_TABLE} "
            f"ADD CONSTRAINT {DAILY_MINUTES_CONSTRAINT} "
            f"CHECK (daily_minutes IN ({allowed_minutes}))"
        )
    )


def upgrade() -> None:
    _drop_daily_minutes_constraint()
    _create_daily_minutes_constraint("5, 10, 15, 20, 30")


def downgrade() -> None:
    _drop_daily_minutes_constraint()
    _create_daily_minutes_constraint("5, 10, 15, 20")
