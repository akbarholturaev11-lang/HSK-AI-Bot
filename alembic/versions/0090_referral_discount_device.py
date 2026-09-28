"""Track the device-specific qualification for the 20% referral offer.

Revision ID: 0090_referral_discount_device
Revises: 0089_android_push_tokens
"""

from alembic import op
import sqlalchemy as sa


revision = "0090_referral_discount_device"
down_revision = "0089_android_push_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "referrals",
        sa.Column("discount_platform", sa.String(length=16), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "referrals",
        sa.Column("discount_qualified_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Preserve progress earned before the device-specific offer existed.
    op.execute("UPDATE referrals SET discount_platform = 'legacy'")
    op.execute(
        "UPDATE referrals SET discount_qualified_at = activated_at "
        "WHERE status = 'active' AND activated_at IS NOT NULL"
    )
    op.create_index(
        "ix_referrals_discount_qualified_at", "referrals", ["discount_qualified_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_referrals_discount_qualified_at", table_name="referrals")
    op.drop_column("referrals", "discount_qualified_at")
    op.drop_column("referrals", "discount_platform")
