"""Android push preferences and reminder delivery state.

Revision ID: 0093_android_push_preferences
Revises: 0092_trial_risk_events
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0093_android_push_preferences"
down_revision: Union[str, None] = "0092_trial_risk_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "android_push_tokens",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "android_push_tokens",
        sa.Column(
            "study_reminders_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "android_push_tokens",
        sa.Column("timezone_name", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "android_push_tokens",
        sa.Column("last_study_push_day", sa.String(length=10), nullable=True),
    )
    op.execute(
        "UPDATE android_push_tokens "
        "SET updated_at = COALESCE(updated_at, registered_at)"
    )
    op.alter_column("android_push_tokens", "updated_at", nullable=False)
    op.alter_column(
        "android_push_tokens",
        "study_reminders_enabled",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("android_push_tokens", "last_study_push_day")
    op.drop_column("android_push_tokens", "timezone_name")
    op.drop_column("android_push_tokens", "study_reminders_enabled")
    op.drop_column("android_push_tokens", "updated_at")
