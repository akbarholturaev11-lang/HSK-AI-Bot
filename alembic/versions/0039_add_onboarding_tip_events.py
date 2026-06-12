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


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if _has_column(table_name, column_name):
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    _add_column_if_missing(
        "users",
        sa.Column("trial_voice_used_at", sa.DateTime(timezone=True), nullable=True),
    )

    if not _has_table("onboarding_tip_events"):
        op.create_table(
            "onboarding_tip_events",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("tip_key", sa.String(length=64), nullable=False),
            sa.Column("trigger_lesson_id", sa.Integer(), nullable=True),
            sa.Column("trigger_step", sa.String(length=64), nullable=True),
            sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
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
            "ix_onboarding_tip_events_scheduled_at",
            "onboarding_tip_events",
            ["scheduled_at"],
            unique=False,
        )


def downgrade() -> None:
    if _has_table("onboarding_tip_events"):
        op.drop_index("ix_onboarding_tip_events_scheduled_at", table_name="onboarding_tip_events")
        op.drop_index("ix_onboarding_tip_events_user_id", table_name="onboarding_tip_events")
        op.drop_table("onboarding_tip_events")
    _drop_column_if_exists("users", "trial_voice_used_at")
