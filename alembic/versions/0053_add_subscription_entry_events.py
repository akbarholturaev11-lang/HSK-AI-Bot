"""add subscription entry events

Revision ID: 0053_add_subscription_entry_events
Revises: 0052_course_miniapp_v3_preferences
Create Date: 2026-06-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0053_add_subscription_entry_events"
down_revision: Union[str, None] = "0052_course_miniapp_v3_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscription_entry_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("mode", sa.String(length=40), nullable=False),
        sa.Column("plan_type", sa.String(length=32), nullable=True),
        sa.Column("payment_method", sa.String(length=16), nullable=True),
        sa.Column("campaign_id", sa.Integer(), nullable=True),
        sa.Column("feedback_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column_name in (
        "user_id",
        "telegram_id",
        "source",
        "mode",
        "plan_type",
        "payment_method",
        "campaign_id",
        "feedback_id",
        "created_at",
    ):
        op.create_index(
            f"ix_subscription_entry_events_{column_name}",
            "subscription_entry_events",
            [column_name],
        )


def downgrade() -> None:
    for column_name in reversed(
        (
            "user_id",
            "telegram_id",
            "source",
            "mode",
            "plan_type",
            "payment_method",
            "campaign_id",
            "feedback_id",
            "created_at",
        )
    ):
        op.drop_index(
            f"ix_subscription_entry_events_{column_name}",
            table_name="subscription_entry_events",
        )
    op.drop_table("subscription_entry_events")
