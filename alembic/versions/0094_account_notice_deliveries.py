"""Android-first account notices with a Telegram fallback.

Revision ID: 0094_account_notice_deliveries
Revises: 0093_android_push_preferences
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0094_account_notice_deliveries"
down_revision: Union[str, None] = "0093_android_push_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "android_push_tokens",
        sa.Column("notifications_allowed", sa.Boolean(), nullable=True),
    )
    op.create_table(
        "account_notice_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("android_targets", sa.Integer(), nullable=False),
        sa.Column("android_blocked", sa.Integer(), nullable=False),
        sa.Column("telegram_payload", sa.JSON(), nullable=True),
        sa.Column("reason", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fallback_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("android_shown_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("telegram_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_account_notice_deliveries_user_id",
        "account_notice_deliveries",
        ["user_id"],
    )
    op.create_index(
        "ix_account_notice_deliveries_telegram_id",
        "account_notice_deliveries",
        ["telegram_id"],
    )
    op.create_index(
        "ix_account_notice_deliveries_status",
        "account_notice_deliveries",
        ["status"],
    )
    op.create_index(
        "ix_account_notice_deliveries_fallback_due_at",
        "account_notice_deliveries",
        ["fallback_due_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_account_notice_deliveries_fallback_due_at",
        table_name="account_notice_deliveries",
    )
    op.drop_index(
        "ix_account_notice_deliveries_status",
        table_name="account_notice_deliveries",
    )
    op.drop_index(
        "ix_account_notice_deliveries_telegram_id",
        table_name="account_notice_deliveries",
    )
    op.drop_index(
        "ix_account_notice_deliveries_user_id",
        table_name="account_notice_deliveries",
    )
    op.drop_table("account_notice_deliveries")
    op.drop_column("android_push_tokens", "notifications_allowed")
