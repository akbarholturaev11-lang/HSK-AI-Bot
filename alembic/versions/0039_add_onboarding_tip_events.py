"""add onboarding tip events

Revision ID: 0039_add_onboarding_tip_events
Revises: 0038_add_user_trial_course_fields
Create Date: 2026-06-12 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0039_add_onboarding_tip_events"
down_revision: Union[str, None] = "0038_add_user_trial_course_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("trial_voice_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "onboarding_tip_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tip_key", sa.String(length=64), nullable=False),
        sa.Column("lang", sa.String(length=8), nullable=False, server_default="ru"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("context_json", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "tip_key", name="uq_onboarding_tip_events_user_tip"),
    )
    op.create_index(
        "ix_onboarding_tip_events_user_id",
        "onboarding_tip_events",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_onboarding_tip_events_status_due_at",
        "onboarding_tip_events",
        ["status", "due_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_onboarding_tip_events_status_due_at", table_name="onboarding_tip_events")
    op.drop_index("ix_onboarding_tip_events_user_id", table_name="onboarding_tip_events")
    op.drop_table("onboarding_tip_events")
    op.drop_column("users", "trial_voice_used_at")
