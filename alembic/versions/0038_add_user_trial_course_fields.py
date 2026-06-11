"""add user trial course fields

Revision ID: 0038_add_user_trial_course_fields
Revises: 0037_add_miniapp_payment_local_fields
Create Date: 2026-06-11 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0038_add_user_trial_course_fields"
down_revision: Union[str, None] = "0037_add_miniapp_payment_local_fields"
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
    _add_column_if_missing("users", sa.Column("trial_course_lesson_id", sa.Integer(), nullable=True))
    _add_column_if_missing("users", sa.Column("trial_course_started_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("users", sa.Column("trial_course_completed_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("users", sa.Column("trial_quiz_explanation_used_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("users", sa.Column("force_sub_required_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    _drop_column_if_exists("users", "force_sub_required_at")
    _drop_column_if_exists("users", "trial_quiz_explanation_used_at")
    _drop_column_if_exists("users", "trial_course_completed_at")
    _drop_column_if_exists("users", "trial_course_started_at")
    _drop_column_if_exists("users", "trial_course_lesson_id")
