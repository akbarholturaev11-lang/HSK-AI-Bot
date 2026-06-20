"""add daily practice retention fields

Revision ID: 0044_add_daily_practice_fields
Revises: 0043_restore_release_feedback_trial_30_minutes
Create Date: 2026-06-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0044_add_daily_practice_fields"
down_revision: Union[str, None] = "0043_restore_release_feedback_trial_30_minutes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
    _add_column_if_missing("users", sa.Column("daily_practice_started_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("users", sa.Column("daily_practice_completed_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing(
        "users",
        sa.Column("daily_practice_streak", sa.Integer(), nullable=False, server_default="0"),
    )
    _add_column_if_missing("users", sa.Column("daily_practice_last_day", sa.Date(), nullable=True))
    op.alter_column("users", "daily_practice_streak", server_default=None)


def downgrade() -> None:
    _drop_column_if_exists("users", "daily_practice_last_day")
    _drop_column_if_exists("users", "daily_practice_streak")
    _drop_column_if_exists("users", "daily_practice_completed_at")
    _drop_column_if_exists("users", "daily_practice_started_at")
