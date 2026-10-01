"""Store each user's subscription price display currency.

Revision ID: 0095_subscription_currency_preference
Revises: 0094_account_notice_deliveries
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0095_subscription_currency_preference"
down_revision: Union[str, None] = "0094_account_notice_deliveries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("subscription_currency", sa.String(length=3), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "subscription_currency")
