"""add scheduled discount notifications

Revision ID: 0029_discount_notification_schedule
Revises: 0028_referral_trial_activation
Create Date: 2026-05-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0029_discount_notification_schedule"
down_revision = "0028_referral_trial_activation"
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
    _add_column_if_missing(
        "discount_campaigns",
        sa.Column("notify_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    _add_column_if_missing("discount_campaigns", sa.Column("notify_media_type", sa.String(length=16), nullable=True))
    _add_column_if_missing("discount_campaigns", sa.Column("notify_media_file_id", sa.String(length=512), nullable=True))
    _add_column_if_missing("discount_campaigns", sa.Column("notification_sent_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing(
        "discount_campaigns",
        sa.Column("notification_sent_count", sa.Integer(), nullable=False, server_default="0"),
    )
    _add_column_if_missing(
        "discount_campaigns",
        sa.Column("notification_failed_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    _drop_column_if_exists("discount_campaigns", "notification_failed_count")
    _drop_column_if_exists("discount_campaigns", "notification_sent_count")
    _drop_column_if_exists("discount_campaigns", "notification_sent_at")
    _drop_column_if_exists("discount_campaigns", "notify_media_file_id")
    _drop_column_if_exists("discount_campaigns", "notify_media_type")
    _drop_column_if_exists("discount_campaigns", "notify_enabled")
