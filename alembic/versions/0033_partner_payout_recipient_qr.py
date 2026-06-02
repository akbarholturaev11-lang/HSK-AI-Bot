"""add partner payout recipient qr code

Revision ID: 0033_partner_payout_recipient_qr
Revises: 0032_visa_usd_subscription_prices
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0033_partner_payout_recipient_qr"
down_revision = "0032_visa_usd_subscription_prices"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    return column_name in {column["name"] for column in inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    if not _has_column("partner_payouts", "recipient_qr_code_file_id"):
        op.add_column("partner_payouts", sa.Column("recipient_qr_code_file_id", sa.String(length=512), nullable=True))


def downgrade() -> None:
    if _has_column("partner_payouts", "recipient_qr_code_file_id"):
        op.drop_column("partner_payouts", "recipient_qr_code_file_id")
