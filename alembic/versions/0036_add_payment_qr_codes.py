"""add payment qr codes

Revision ID: 0036_add_payment_qr_codes
Revises: 0035_partner_payout_safety
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0036_add_payment_qr_codes"
down_revision = "0035_partner_payout_safety"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    if _has_table("payment_qr_codes"):
        return

    op.create_table(
        "payment_qr_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("payment_method", sa.String(length=16), nullable=False),
        sa.Column("plan_type", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("file_id", sa.String(length=512), nullable=False),
        sa.Column("created_by_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_qr_codes")),
        sa.UniqueConstraint(
            "scope",
            "payment_method",
            "plan_type",
            "amount",
            "currency",
            name="uq_payment_qr_codes_scope_method_plan_amount_currency",
        ),
    )
    op.create_index(op.f("ix_payment_qr_codes_scope"), "payment_qr_codes", ["scope"], unique=False)
    op.create_index(
        op.f("ix_payment_qr_codes_payment_method"),
        "payment_qr_codes",
        ["payment_method"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payment_qr_codes_plan_type"),
        "payment_qr_codes",
        ["plan_type"],
        unique=False,
    )


def downgrade() -> None:
    if _has_table("payment_qr_codes"):
        op.drop_index(op.f("ix_payment_qr_codes_plan_type"), table_name="payment_qr_codes")
        op.drop_index(op.f("ix_payment_qr_codes_payment_method"), table_name="payment_qr_codes")
        op.drop_index(op.f("ix_payment_qr_codes_scope"), table_name="payment_qr_codes")
        op.drop_table("payment_qr_codes")
