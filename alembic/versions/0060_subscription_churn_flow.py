"""add subscription churn follow-up state

Revision ID: 0060_subscription_churn_flow
Revises: 0059_user_bot_block_tracking
Create Date: 2026-06-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0060_subscription_churn_flow"
down_revision: Union[str, None] = "0059_user_bot_block_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("subscription_expired_offer_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("subscription_churn_followup_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("subscription_churn_responded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("subscription_churn_reason", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "subscription_churn_reason")
    op.drop_column("users", "subscription_churn_responded_at")
    op.drop_column("users", "subscription_churn_followup_sent_at")
    op.drop_column("users", "subscription_expired_offer_sent_at")
