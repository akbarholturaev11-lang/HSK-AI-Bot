"""add partner affiliate program

Revision ID: 0030_add_partner_program
Revises: 0029_discount_notification_schedule
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0030_add_partner_program"
down_revision = "0029_discount_notification_schedule"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    if not _has_table("partners"):
        op.create_table(
            "partners",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_telegram_id", sa.BigInteger(), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("promotion_channel", sa.Text(), nullable=False),
            sa.Column("audience_size", sa.String(length=120), nullable=False),
            sa.Column("contact_username", sa.String(length=128), nullable=False),
            sa.Column("approved_by_telegram_id", sa.BigInteger(), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_telegram_id"),
        )
        op.create_index(op.f("ix_partners_status"), "partners", ["status"], unique=False)
        op.create_index(op.f("ix_partners_user_telegram_id"), "partners", ["user_telegram_id"], unique=True)

    if not _has_table("partner_referrals"):
        op.create_table(
            "partner_referrals",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("partner_id", sa.Integer(), nullable=False),
            sa.Column("invited_user_telegram_id", sa.BigInteger(), nullable=False),
            sa.Column("first_paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("invited_user_telegram_id"),
        )
        op.create_index(op.f("ix_partner_referrals_partner_id"), "partner_referrals", ["partner_id"], unique=False)
        op.create_index(
            op.f("ix_partner_referrals_invited_user_telegram_id"),
            "partner_referrals",
            ["invited_user_telegram_id"],
            unique=True,
        )

    if not _has_table("partner_credits"):
        op.create_table(
            "partner_credits",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("partner_id", sa.Integer(), nullable=False),
            sa.Column("payment_id", sa.Integer(), nullable=True),
            sa.Column("credit_type", sa.String(length=32), nullable=False),
            sa.Column("amount_usd", sa.Numeric(precision=12, scale=2), nullable=False),
            sa.Column("is_locked", sa.Boolean(), nullable=False),
            sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("payment_id"),
        )
        op.create_index(op.f("ix_partner_credits_partner_id"), "partner_credits", ["partner_id"], unique=False)
        op.create_index(op.f("ix_partner_credits_payment_id"), "partner_credits", ["payment_id"], unique=True)
        op.create_index(op.f("ix_partner_credits_credit_type"), "partner_credits", ["credit_type"], unique=False)

    if not _has_table("partner_payouts"):
        op.create_table(
            "partner_payouts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("partner_id", sa.Integer(), nullable=False),
            sa.Column("amount_usd", sa.Numeric(precision=12, scale=2), nullable=False),
            sa.Column("exchange_rate", sa.Numeric(precision=12, scale=4), nullable=False),
            sa.Column("local_amount", sa.Numeric(precision=14, scale=2), nullable=False),
            sa.Column("status", sa.String(length=24), nullable=False),
            sa.Column("payment_method", sa.String(length=24), nullable=False),
            sa.Column("bank_name", sa.String(length=160), nullable=True),
            sa.Column("account_details", sa.Text(), nullable=False),
            sa.Column("holder_name", sa.String(length=180), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("proof_screenshot_file_id", sa.String(length=512), nullable=True),
            sa.Column("reviewed_by_telegram_id", sa.BigInteger(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_partner_payouts_partner_id"), "partner_payouts", ["partner_id"], unique=False)
        op.create_index(op.f("ix_partner_payouts_status"), "partner_payouts", ["status"], unique=False)


def downgrade() -> None:
    for table_name in ("partner_payouts", "partner_credits", "partner_referrals", "partners"):
        if _has_table(table_name):
            op.drop_table(table_name)
