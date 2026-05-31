"""add referral trial progress message fields

Revision ID: 0031_referral_trial_progress_message
Revises: 0030_add_partner_program
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0031_referral_trial_progress_message"
down_revision = "0030_add_partner_program"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    return column_name in {column["name"] for column in inspect(bind).get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if _has_column(table_name, column_name):
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    _add_column_if_missing("users", sa.Column("referral_trial_progress_chat_id", sa.BigInteger(), nullable=True))
    _add_column_if_missing("users", sa.Column("referral_trial_progress_message_id", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    _drop_column_if_exists("users", "referral_trial_progress_message_id")
    _drop_column_if_exists("users", "referral_trial_progress_chat_id")
