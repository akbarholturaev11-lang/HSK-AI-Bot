"""convert visa subscription prices from somoni to usd

Revision ID: 0032_visa_usd_subscription_prices
Revises: 0031_referral_trial_progress_message
Create Date: 2026-06-01
"""

from alembic import op
from decimal import Decimal
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0032_visa_usd_subscription_prices"
down_revision = "0031_referral_trial_progress_message"
branch_labels = None
depends_on = None


VISA_USD_TJS_RATE = Decimal("9.2464")


def _has_table(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    if not _has_table("subscription_prices"):
        return
    op.execute(
        sa.text(
            """
            UPDATE subscription_prices
            SET amount = GREATEST(1, ROUND(amount / :rate)::INTEGER),
                currency = 'USD'
            WHERE payment_method = 'visa'
              AND LOWER(currency) IN ('somoni', 'tjs', 'сомони')
            """
        ).bindparams(rate=VISA_USD_TJS_RATE)
    )


def downgrade() -> None:
    if not _has_table("subscription_prices"):
        return
    op.execute(
        sa.text(
            """
            UPDATE subscription_prices
            SET amount = GREATEST(1, ROUND(amount * :rate)::INTEGER),
                currency = 'somoni'
            WHERE payment_method = 'visa'
              AND LOWER(currency) IN ('usd', '$')
            """
        ).bindparams(rate=VISA_USD_TJS_RATE)
    )
